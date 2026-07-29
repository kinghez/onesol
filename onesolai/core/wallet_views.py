from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Profile, WalletTransaction
from django.conf import settings
from core.models import SiteSettings
from decimal import Decimal
import uuid
import requests
import logging

logger = logging.getLogger(__name__)

@login_required(login_url='/auth/login/')
def wallet_dashboard_view(request):
    user = request.user
    profile = user.profile
    transactions = user.wallet_transactions.all()
    
    context = {
        'profile': profile,
        'transactions': transactions,
    }
    return render(request, 'dashboard/wallet.html', context)


@login_required(login_url='/auth/login/')
def wallet_topup_initialize(request):
    if request.method == 'POST':
        amount_str = request.POST.get('amount')
        payment_method = request.POST.get('payment_method', 'card').strip().lower()
        try:
            amount = float(amount_str)
            if amount < 100:
                messages.error(request, "Minimum top-up amount is NGN 100.")
                return redirect('dashboard:wallet')
        except (ValueError, TypeError):
            messages.error(request, "Invalid amount.")
            return redirect('dashboard:wallet')
            
        cfg = SiteSettings.get()

        if payment_method == 'crypto':
            if not cfg.is_crypto_enabled:
                messages.error(request, "Crypto payments are currently disabled.")
                return redirect('dashboard:wallet')

            reference = f"TOPUP_CRYPTO_{uuid.uuid4().hex[:12].upper()}"
            WalletTransaction.objects.create(
                user=request.user,
                transaction_type='deposit',
                amount_ngn=amount,
                reference=reference,
                description="Wallet Top-up via Crypto USDT (Pending TxID Submission)"
            )
            return redirect('dashboard:wallet_crypto_topup', reference=reference)

        # Dynamic Primary Gateway Selection (Flutterwave vs Paystack)
        primary = cfg.primary_payment_gateway or 'paystack'
        is_fw_active = cfg.is_flutterwave_enabled and bool(cfg.flutterwave_secret_key.strip())
        is_ps_active = cfg.is_paystack_enabled and bool(cfg.paystack_secret_key.strip())

        callback_url = request.build_absolute_uri('/dashboard/wallet/topup/callback/')

        def try_flutterwave():
            from orders import flutterwave as flw
            ref = flw.generate_reference()
            link, _ = flw.initialize_transaction(
                email=request.user.email,
                amount=Decimal(str(amount)),
                currency='NGN',
                reference=ref,
                callback_url=callback_url,
                metadata={'user_id': request.user.id, 'type': 'wallet_topup', 'amount_ngn': amount},
                customer_name=f"{request.user.first_name} {request.user.last_name}".strip() or request.user.email
            )
            return link

        def try_paystack():
            from orders import paystack as ps
            ref = ps.generate_reference()
            auth_url, _ = ps.initialize_transaction(
                email=request.user.email,
                amount_ngn=Decimal(str(amount)),
                reference=ref,
                callback_url=callback_url,
                metadata={'user_id': request.user.id, 'type': 'wallet_topup', 'amount_ngn': amount}
            )
            return auth_url

        sequence = []
        if primary == 'flutterwave':
            if is_fw_active: sequence.append(('Flutterwave', try_flutterwave))
            if is_ps_active: sequence.append(('Paystack', try_paystack))
        else:
            if is_ps_active: sequence.append(('Paystack', try_paystack))
            if is_fw_active: sequence.append(('Flutterwave', try_flutterwave))

        if not sequence:
            messages.error(request, "No active payment gateway is currently configured. Please contact support.")
            return redirect('dashboard:wallet')

        for g_name, g_func in sequence:
            try:
                auth_url = g_func()
                return redirect(auth_url)
            except Exception as e:
                logger.error(f"Wallet Topup Gateway {g_name} failed: {e}")

        messages.error(request, "Failed to initialize payment gateway. Please try again.")
        return redirect('dashboard:wallet')

    return redirect('dashboard:wallet')


@login_required(login_url='/auth/login/')
def wallet_crypto_topup_view(request, reference):
    """Render Crypto Wallet Top-up payment page."""
    cfg = SiteSettings.get()
    tx = WalletTransaction.objects.filter(user=request.user, reference=reference).first()
    if not tx:
        messages.error(request, "Transaction not found.")
        return redirect('dashboard:wallet')

    context = {
        'tx': tx,
        'cfg': cfg,
    }
    return render(request, 'dashboard/wallet_crypto_topup.html', context)


@login_required(login_url='/auth/login/')
def wallet_crypto_submit_view(request, reference):
    """Process user TxID submission for Crypto Wallet Top-up."""
    if request.method == 'POST':
        tx_hash = request.POST.get('transaction_hash', '').strip()
        if not tx_hash:
            messages.error(request, "Transaction Hash (TxID) is required.")
            return redirect('dashboard:wallet_crypto_topup', reference=reference)

        tx = WalletTransaction.objects.filter(user=request.user, reference=reference).first()
        if tx:
            tx.description = f"Wallet Top-up via Crypto USDT (TxID: {tx_hash})"
            tx.save(update_fields=['description'])

            # Log Activity
            try:
                from analytics.models import ActivityLog
                ActivityLog.objects.create(
                    user=request.user,
                    activity_type='user_signup',
                    description=f'Submitted Crypto Top-up TxID ({tx_hash[:12]}...) for NGN {tx.amount_ngn:,.0f} (Ref: {reference})',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            except Exception:
                pass

            messages.success(request, f"Your TxID for NGN {tx.amount_ngn:,.0f} wallet top-up has been submitted for admin verification!")
        else:
            messages.error(request, "Transaction reference not found.")

    return redirect('dashboard:wallet')


@login_required(login_url='/auth/login/')
def wallet_topup_callback(request):
    """
    Handles payment callback for wallet top-ups (supporting both Flutterwave and Paystack).
    """
    # Flutterwave sends tx_ref or transaction_id; Paystack sends reference or trxref
    reference = request.GET.get('reference') or request.GET.get('tx_ref') or request.GET.get('trxref')
    transaction_id = request.GET.get('transaction_id')
    status_param = request.GET.get('status')

    if not reference and not transaction_id:
        messages.error(request, "Payment reference missing.")
        return redirect('dashboard:wallet')

    amount_ngn = None
    is_successful = False
    gateway_used = ''

    # Check if reference belongs to Flutterwave
    if (reference and 'FLW' in reference) or transaction_id or status_param == 'successful':
        from orders import flutterwave as flw
        try:
            flw_data = flw.verify_transaction(transaction_id=transaction_id, reference=reference)
            if flw_data.get('status') == 'successful':
                amount_ngn = Decimal(str(flw_data.get('amount', 0)))
                is_successful = True
                gateway_used = 'Flutterwave'
        except Exception as e:
            logger.error(f"Wallet top-up Flutterwave verification failed: {e}")

    # Fallback to Paystack verification
    if not is_successful and reference:
        from orders import paystack as ps
        try:
            ps_data = ps.verify_transaction(reference)
            if ps_data.get('status') == 'success':
                amount_ngn = Decimal(str(ps_data.get('amount', 0))) / Decimal('100')
                is_successful = True
                gateway_used = 'Paystack'
        except Exception as e:
            logger.error(f"Wallet top-up Paystack verification failed: {e}")

    if is_successful and amount_ngn:
        lookup_ref = reference or f"FLW_TX_{transaction_id}"
        if not WalletTransaction.objects.filter(reference=lookup_ref).exists():
            profile = request.user.profile
            profile.wallet_balance += amount_ngn
            profile.save(update_fields=['wallet_balance'])

            WalletTransaction.objects.create(
                user=request.user,
                transaction_type='deposit',
                amount_ngn=amount_ngn,
                reference=lookup_ref,
                description=f"Wallet Top-up via {gateway_used}"
            )

            from notifications.models import Notification
            Notification.objects.create(
                user=request.user,
                title="Wallet Funded",
                message=f"Your wallet has been successfully credited with NGN {amount_ngn:,.2f}.",
                notification_type='system',
                action_url='/dashboard/wallet/'
            )

            messages.success(request, f"Successfully added NGN {amount_ngn:,.2f} to your wallet via {gateway_used}.")
        else:
            messages.info(request, "This transaction has already been processed.")
    else:
        messages.error(request, "Payment verification failed or payment was not successful.")

    return redirect('dashboard:wallet')
