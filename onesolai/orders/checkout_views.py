"""
Order checkout and payment views for OneSol AI Hub.
Flow: Buy Now -> checkout -> Paystack -> callback -> confirmation
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import reverse
from decimal import Decimal

from products.models import Tool
from .models import Order, OrderItem, PaymentTransaction
from . import paystack as ps
from . import flutterwave as flw
from .delivery import trigger_delivery, credit_referral_commission

PAYSTACK_CURRENCIES = {'NGN', 'GHS', 'KES', 'ZAR', 'USD'}
FLUTTERWAVE_CURRENCIES = {'NGN', 'GHS', 'KES', 'ZAR', 'UGX', 'TZS', 'RWF', 'XOF', 'XAF', 'ZMW', 'MWK', 'MUR', 'EGP', 'USD', 'GBP', 'EUR', 'CAD', 'AUD'}


def initiate_gateway_payment(order, tool, price_ngn, local_amount, user_currency, request):
    """
    Handles payment gateway initialization based on admin configuration, primary gateway setting,
    supported currency check, and automatic fallback between Paystack and Flutterwave.
    """
    from core.models import SiteSettings
    from django.conf import settings
    cfg = SiteSettings.get()

    primary = cfg.primary_payment_gateway or 'paystack'
    is_paystack_active = cfg.is_paystack_enabled and bool(cfg.paystack_secret_key.strip() or getattr(settings, 'PAYSTACK_SECRET_KEY', ''))
    is_flutterwave_active = cfg.is_flutterwave_enabled and bool(cfg.flutterwave_secret_key.strip() or getattr(settings, 'FLUTTERWAVE_SECRET_KEY', ''))

    user_curr = user_currency.upper()

    paystack_callback = request.build_absolute_uri(reverse('orders:payment_callback'))
    flutterwave_callback = request.build_absolute_uri(reverse('orders:flutterwave_callback'))

    def try_paystack():
        ref = ps.generate_reference()
        order.paystack_reference = ref
        order.save(update_fields=['paystack_reference'])

        auth_url, confirmed_ref = ps.initialize_transaction(
            email=request.user.email,
            amount_ngn=price_ngn,
            reference=ref,
            callback_url=paystack_callback,
            metadata={
                'order_id': order.id,
                'tool_name': tool.name,
                'user_id': request.user.id,
            }
        )
        PaymentTransaction.objects.create(
            order=order,
            gateway='paystack',
            transaction_id=confirmed_ref,
            reference=confirmed_ref,
            status='pending',
            amount_paid=price_ngn,
            currency_paid='NGN',
        )
        return auth_url

    def try_flutterwave():
        ref = flw.generate_reference()
        order.paystack_reference = ref
        order.save(update_fields=['paystack_reference'])

        flw_curr = user_curr if user_curr in FLUTTERWAVE_CURRENCIES else 'NGN'
        flw_amount = local_amount if flw_curr == user_curr else price_ngn

        auth_url, confirmed_ref = flw.initialize_transaction(
            email=request.user.email,
            amount=flw_amount,
            currency=flw_curr,
            reference=ref,
            callback_url=flutterwave_callback,
            metadata={
                'order_id': order.id,
                'tool_name': tool.name,
                'user_id': request.user.id,
            },
            customer_name=f"{request.user.first_name} {request.user.last_name}".strip() or request.user.email
        )
        PaymentTransaction.objects.create(
            order=order,
            gateway='flutterwave',
            transaction_id=confirmed_ref,
            reference=confirmed_ref,
            status='pending',
            amount_paid=flw_amount,
            currency_paid=flw_curr,
        )
        return auth_url

    gateway_sequence = []

    if primary == 'paystack':
        if is_paystack_active and (user_curr in PAYSTACK_CURRENCIES or user_curr == 'NGN'):
            gateway_sequence.append(('Paystack', try_paystack))
        if is_flutterwave_active:
            gateway_sequence.append(('Flutterwave', try_flutterwave))
        if is_paystack_active and ('Paystack', try_paystack) not in gateway_sequence:
            gateway_sequence.append(('Paystack', try_paystack))
    else:
        if is_flutterwave_active and user_curr in FLUTTERWAVE_CURRENCIES:
            gateway_sequence.append(('Flutterwave', try_flutterwave))
        if is_paystack_active:
            gateway_sequence.append(('Paystack', try_paystack))
        if is_flutterwave_active and ('Flutterwave', try_flutterwave) not in gateway_sequence:
            gateway_sequence.append(('Flutterwave', try_flutterwave))

    if not gateway_sequence:
        raise ValueError("No active payment gateway is currently configured for this currency. Please contact support.")

    import logging
    logger = logging.getLogger(__name__)
    
    errors = []
    for g_name, g_func in gateway_sequence:
        try:
            return g_func()
        except Exception as e:
            import traceback
            print(f"\\n[GATEWAY ERROR] {g_name} failed: {e}\\n{traceback.format_exc()}")
            logger.error(f"Payment gateway {g_name} failed: {e}\\n{traceback.format_exc()}")
            errors.append(f"{g_name}: {e}")

    raise ValueError(f"Payment gateway initialization failed: {'; '.join(errors)}")


# ─────────────────────────────────────────────────────────────
#  CHECKOUT – creates order and redirects to Payment Gateway
# ─────────────────────────────────────────────────────────────
@login_required(login_url='/auth/login/')
@require_POST
def checkout_view(request):
    """
    POST: tool_slug
    Creates a pending Order and redirects user to primary/fallback payment gateway.
    """
    tool_slug = request.POST.get('tool_slug')
    tool = get_object_or_404(Tool, slug=tool_slug, is_active=True)

    # Determine price
    price_ngn = tool.get_ngn_price()
    usd_price = tool.get_usd_price()

    user_currency = request.session.get('detected_currency')
    if not user_currency and hasattr(request.user, 'profile') and request.user.profile.currency_preference:
        user_currency = request.user.profile.currency_preference
    if not user_currency:
        user_currency = 'NGN'

    from core.services import get_live_usd_rates
    rates = get_live_usd_rates() or {}
    rate = rates.get(user_currency)
    if not rate or float(rate) <= 0:
        rate = 1500.0 if user_currency == 'NGN' else 1.0

    local_amount = Decimal(str(round(float(usd_price) * float(rate), 2)))

    # Create Order
    order = Order.objects.create(
        user=request.user,
        total_amount_ngn=price_ngn,
        local_currency=user_currency,
        local_amount=local_amount,
        exchange_rate=Decimal(str(rate)),
        delivery_email=request.user.email,
        status='pending',
    )
    OrderItem.objects.create(
        order=order,
        tool=tool,
        price_ngn=price_ngn,
    )

    payment_method = request.POST.get('payment_method', '').strip().lower()
    pay_with_wallet = (request.POST.get('pay_with_wallet') == 'true') or (payment_method == 'wallet')

    if payment_method == 'crypto':
        from core.models import SiteSettings
        cfg = SiteSettings.get()
        if not cfg.is_crypto_enabled:
            messages.error(request, "Crypto payment gateway is currently disabled.")
            return redirect(reverse('tools:tool_detail', kwargs={'slug': tool_slug}))

        PaymentTransaction.objects.create(
            order=order,
            gateway='crypto',
            transaction_id=f"CRYPTO_PENDING_{order.id}",
            reference=f"CRYPTO_REF_{order.id}",
            status='pending',
            amount_paid=usd_price,
            currency_paid='USDT',
        )
        return redirect('orders:crypto_checkout', order_id=order.id)

    if pay_with_wallet:
        profile = request.user.profile
        if profile.wallet_balance >= price_ngn:
            from django.db import transaction
            with transaction.atomic():
                profile.wallet_balance -= price_ngn
                profile.save(update_fields=['wallet_balance'])
                
                order.status = 'paid'
                order.save(update_fields=['status'])
                
                from accounts.models import WalletTransaction
                WalletTransaction.objects.create(
                    user=request.user,
                    transaction_type='purchase',
                    amount_ngn=price_ngn,
                    reference=f"ORDER_{order.id}",
                    status='success',
                    description=f"Purchased {tool.name}"
                )
                
                PaymentTransaction.objects.create(
                    order=order,
                    gateway='wallet',
                    transaction_id=f"WALLET_{order.id}",
                    reference=f"WALLET_{order.id}",
                    status='success',
                    amount_paid=price_ngn,
                    currency_paid='NGN',
                )

                from analytics.models import ActivityLog
                ActivityLog.log(
                    action_type='wallet_purchase',
                    title=f"Purchased {tool.name} via Wallet",
                    details=f"Order #{order.id} | Amount: NGN {price_ngn:,.2f}",
                    user=request.user,
                    severity='success'
                )
                
            trigger_delivery(order)
            credit_referral_commission(order)
            try:
                from vendors.tasks import fulfill_order_via_vendors
                fulfill_order_via_vendors(order.id)
            except Exception as e:
                logger.error(f"Vendor fulfillment error for Order #{order.id}: {e}")
            
            messages.success(request, f"Payment successful! You purchased {tool.name} using your wallet balance.")
            return redirect(reverse('orders:confirmation', args=[order.id]))
        else:
            messages.error(request, "Insufficient wallet balance for this purchase. Please top up your wallet.")
            return redirect(reverse('tools:tool_detail', kwargs={'slug': tool_slug}))

    # Initiate payment with primary / fallback gateway
    try:
        redirect_url = initiate_gateway_payment(order, tool, price_ngn, local_amount, user_currency, request)
        return redirect(redirect_url)
    except Exception as e:
        order.status = 'failed'
        order.save(update_fields=['status'])
        logger.error(f"Order #{order.id} payment initialization failed: {e}")
        messages.error(request, f"Payment gateway initialization failed: {e}")
        return redirect(reverse('tools:tool_detail', kwargs={'slug': tool_slug}))


# ─────────────────────────────────────────────────────────────
#  PAYMENT CALLBACKS – verifies Paystack & Flutterwave payments
# ─────────────────────────────────────────────────────────────
def payment_callback_view(request):
    """
    GET: Paystack redirects here after payment attempt.
    Verifies the transaction and updates the order.
    """
    reference = request.GET.get('reference') or request.GET.get('trxref')

    if not reference:
        messages.error(request, 'Invalid payment reference.')
        return redirect('/')

    try:
        order = Order.objects.select_related('user').get(paystack_reference=reference)
    except Order.DoesNotExist:
        messages.error(request, 'Order not found for this payment reference.')
        return redirect('/')

    if order.status == 'paid':
        return redirect(reverse('orders:confirmation', kwargs={'order_id': order.id}))

    try:
        txn_data = ps.verify_transaction(reference)
        ps_status = txn_data.get('status')
        amount_paid_kobo = txn_data.get('amount', 0)
        amount_paid_ngn = Decimal(amount_paid_kobo) / 100

        if ps_status == 'success':
            order.status = 'paid'
            order.total_amount_ngn = amount_paid_ngn
            order.save(update_fields=['status', 'total_amount_ngn'])

            PaymentTransaction.objects.filter(order=order).update(
                status='success',
                amount_paid=amount_paid_ngn,
                gateway_response=txn_data,
            )

            from analytics.models import ActivityLog
            ActivityLog.log(
                action_type='payment_success',
                title=f"Paystack Payment Verified: Order #{order.id}",
                details=f"Amount: NGN {amount_paid_ngn:,.2f} | Reference: {reference}",
                user=order.user,
                severity='success'
            )

            trigger_delivery(order)
            credit_referral_commission(order)
            
            try:
                from vendors.tasks import fulfill_order_via_vendors
                fulfill_order_via_vendors(order.id)
            except Exception:
                pass

            return redirect(reverse('orders:confirmation', kwargs={'order_id': order.id}))

        else:
            order.status = 'failed'
            order.save(update_fields=['status'])
            messages.error(request, 'Payment was not successful. Please try again.')
            return redirect('/')

    except ValueError as e:
        messages.error(request, f'Could not verify payment: {e}')
        return redirect('/')


def flutterwave_callback_view(request):
    """
    GET: Flutterwave redirects here after payment attempt.
    Query parameters: status, tx_ref, transaction_id.
    """
    tx_ref = request.GET.get('tx_ref') or request.GET.get('reference')
    transaction_id = request.GET.get('transaction_id')

    if not tx_ref and not transaction_id:
        messages.error(request, 'Invalid payment response from Flutterwave.')
        return redirect('/')

    try:
        if tx_ref:
            order = Order.objects.select_related('user').get(paystack_reference=tx_ref)
        else:
            order = Order.objects.select_related('user').filter(paystack_reference__icontains='FLW').first()
    except Order.DoesNotExist:
        messages.error(request, 'Order not found for this Flutterwave reference.')
        return redirect('/')

    if order.status == 'paid':
        return redirect(reverse('orders:confirmation', kwargs={'order_id': order.id}))

    try:
        txn_data = flw.verify_transaction(transaction_id=transaction_id, reference=tx_ref)
        flw_status = (txn_data.get('status') or '').lower()
        amount_paid = Decimal(str(txn_data.get('amount', 0)))
        currency_paid = (txn_data.get('currency') or 'NGN').upper()

        if flw_status in ['successful', 'completed']:
            order.status = 'paid'
            order.save(update_fields=['status'])

            pt, _ = PaymentTransaction.objects.get_or_create(
                order=order,
                defaults={
                    'gateway': 'flutterwave',
                    'transaction_id': str(transaction_id or tx_ref),
                    'reference': tx_ref or str(transaction_id),
                    'status': 'success',
                    'amount_paid': amount_paid,
                    'currency_paid': currency_paid,
                }
            )
            pt.status = 'success'
            pt.amount_paid = amount_paid
            pt.currency_paid = currency_paid
            pt.save()

            from analytics.models import ActivityLog
            ActivityLog.log(
                action_type='payment_success',
                title=f"Flutterwave Payment Verified: Order #{order.id}",
                details=f"Amount: {currency_paid} {amount_paid:,.2f} | Reference: {tx_ref or transaction_id}",
                user=order.user,
                severity='success'
            )

            trigger_delivery(order)
            credit_referral_commission(order)

            try:
                from vendors.tasks import fulfill_order_via_vendors
                fulfill_order_via_vendors(order.id)
            except Exception:
                pass

            messages.success(request, 'Flutterwave payment verified successfully!')
            return redirect(reverse('orders:confirmation', kwargs={'order_id': order.id}))

        else:
            order.status = 'failed'
            order.save(update_fields=['status'])
            messages.error(request, f'Flutterwave payment failed with status: {flw_status}')
            return redirect('/')

    except ValueError as e:
        messages.error(request, f'Flutterwave verification failed: {e}')
        return redirect('/')


# ─────────────────────────────────────────────────────────────
#  ORDER CONFIRMATION – success page
# ─────────────────────────────────────────────────────────────
@login_required(login_url='/auth/login/')
def order_confirmation_view(request, order_id):
    """Premium success page shown after successful payment."""
    order = get_object_or_404(
        Order.objects.prefetch_related('items__tool'),
        id=order_id,
        user=request.user,
    )
    return render(request, 'orders/confirmation.html', {'order': order})


# ─────────────────────────────────────────────────────────────
#  CRYPTO CHECKOUT – USDT manual & gateway checkout
# ─────────────────────────────────────────────────────────────
@login_required(login_url='/auth/login/')
def crypto_checkout_view(request, order_id):
    """Render Crypto payment page with USDT wallet address and instructions."""
    from core.models import SiteSettings
    cfg = SiteSettings.get()
    order = get_object_or_404(Order, id=order_id, user=request.user)

    first_item = order.items.first()
    tool = first_item.tool if first_item else None
    usd_amount = tool.get_usd_price() if tool else order.local_amount

    context = {
        'order': order,
        'tool': tool,
        'usdt_address': cfg.crypto_usdt_address,
        'usdt_network': cfg.crypto_usdt_network,
        'instructions': cfg.crypto_instructions,
        'usd_amount': usd_amount,
    }
    return render(request, 'orders/crypto_payment.html', context)


@login_required(login_url='/auth/login/')
@require_POST
def submit_crypto_payment_view(request, order_id):
    """Process user TxID submission for Crypto payment."""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    tx_hash = request.POST.get('transaction_hash', '').strip()

    if not tx_hash:
        messages.error(request, "Please enter a valid Transaction Hash / TxID.")
        return redirect('orders:crypto_checkout', order_id=order.id)

    tx = PaymentTransaction.objects.filter(order=order, gateway='crypto').first()
    if not tx:
        tx = PaymentTransaction.objects.create(
            order=order,
            gateway='crypto',
            transaction_id=tx_hash,
            reference=tx_hash,
            status='pending',
            amount_paid=order.total_amount_ngn,
            currency_paid='USDT'
        )
    else:
        tx.transaction_id = tx_hash
        tx.reference = tx_hash
        tx.status = 'pending'
        tx.save()

    # Log Activity
    try:
        from analytics.models import ActivityLog
        ActivityLog.objects.create(
            user=request.user,
            activity_type='order_created',
            description=f'Submitted Crypto TxID ({tx_hash[:12]}...) for Order #{order.id}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
    except Exception:
        pass

    messages.success(request, f"Your Crypto transaction hash (TxID) for Order #{order.id} has been submitted for verification!")
    return redirect('orders:confirmation', order_id=order.id)
