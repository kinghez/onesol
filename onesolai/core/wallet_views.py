from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Profile, WalletTransaction
from django.conf import settings
from core.models import SiteSettings
import uuid
import requests

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

        secret_key = cfg.paystack_secret_key
        if not secret_key:
            messages.error(request, "Payment gateway is not configured.")
            return redirect('dashboard:wallet')
            
        reference = f"TOPUP_{uuid.uuid4().hex[:12].upper()}"
        
        # Initialize Paystack
        headers = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json"
        }
        
        # Build the callback URL (using absolute URI if possible, or relative)
        callback_url = request.build_absolute_uri('/dashboard/wallet/topup/callback/')
        
        data = {
            "email": request.user.email,
            "amount": int(amount * 100),  # Paystack uses kobo
            "reference": reference,
            "callback_url": callback_url,
            "metadata": {
                "user_id": request.user.id,
                "type": "wallet_topup"
            }
        }
        
        resp = requests.post("https://api.paystack.co/transaction/initialize", headers=headers, json=data)
        
        if resp.status_code == 200:
            res_data = resp.json()
            auth_url = res_data['data']['authorization_url']
            return redirect(auth_url)
        else:
            messages.error(request, "Failed to initialize payment. Please try again.")
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

    from core.services import get_live_usd_rates
    rates = get_live_usd_rates() or {}
    ngn_rate = float(rates.get('NGN', 1500.0))
    usd_amount = round(float(tx.amount_ngn) / ngn_rate, 2)

    context = {
        'tx': tx,
        'reference': reference,
        'amount_ngn': tx.amount_ngn,
        'usd_amount': usd_amount,
        'usdt_address': cfg.crypto_usdt_address,
        'usdt_network': cfg.crypto_usdt_network,
        'instructions': cfg.crypto_instructions,
    }
    return render(request, 'dashboard/wallet_crypto.html', context)


@login_required(login_url='/auth/login/')
def wallet_crypto_submit_view(request, reference):
    """Process user TxID submission for Crypto Wallet Top-up."""
    if request.method == 'POST':
        tx_hash = request.POST.get('transaction_hash', '').strip()
        if not tx_hash:
            messages.error(request, "Please enter a valid Transaction Hash / TxID.")
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
                    activity_type='user_signup', # general system action
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
    reference = request.GET.get('reference')
    if not reference:
        messages.error(request, "Payment reference missing.")
        return redirect('dashboard:wallet')
        
    cfg = SiteSettings.get()
    secret_key = cfg.paystack_secret_key
    
    headers = {
        "Authorization": f"Bearer {secret_key}",
    }
    
    resp = requests.get(f"https://api.paystack.co/transaction/verify/{reference}", headers=headers)
    
    if resp.status_code == 200:
        res_data = resp.json()
        if res_data['data']['status'] == 'success':
            amount_ngn = res_data['data']['amount'] / 100
            
            # Check if transaction already exists
            if not WalletTransaction.objects.filter(reference=reference).exists():
                # Add to wallet balance
                profile = request.user.profile
                profile.wallet_balance += type(profile.wallet_balance)(str(amount_ngn))
                profile.save(update_fields=['wallet_balance'])
                
                # Record transaction
                WalletTransaction.objects.create(
                    user=request.user,
                    transaction_type='deposit',
                    amount_ngn=amount_ngn,
                    reference=reference,
                    description="Wallet Top-up via Paystack"
                )
                
                # Notify User
                from notifications.models import Notification
                Notification.objects.create(
                    user=request.user,
                    title="Wallet Funded",
                    message=f"Your wallet has been successfully credited with NGN {amount_ngn:,.2f}.",
                    notification_type='system',
                    action_url='/dashboard/wallet/'
                )
                
                messages.success(request, f"Successfully added NGN {amount_ngn:,.2f} to your wallet.")
            else:
                messages.info(request, "This transaction has already been processed.")
        else:
            messages.error(request, "Payment was not successful.")
    else:
        messages.error(request, "Failed to verify payment with Paystack.")
        
    return redirect('dashboard:wallet')
