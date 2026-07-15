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

from products.models import Tool, SubscriptionPlan
from .models import Order, OrderItem, PaymentTransaction
from . import paystack as ps
from .delivery import trigger_delivery, credit_referral_commission


# ─────────────────────────────────────────────────────────────
#  CHECKOUT – creates order and redirects to Paystack
# ─────────────────────────────────────────────────────────────
@login_required(login_url='/auth/login/')
@require_POST
def checkout_view(request):
    """
    POST: tool_slug, plan_id (optional)
    Creates a pending Order and redirects user to Paystack payment page.
    """
    tool_slug = request.POST.get('tool_slug')
    plan_id = request.POST.get('plan_id')

    tool = get_object_or_404(Tool, slug=tool_slug, is_active=True)

    # Determine plan and price
    if plan_id:
        plan = get_object_or_404(SubscriptionPlan, id=plan_id, tool=tool, is_active=True)
        price_ngn = plan.price_ngn
    else:
        plan = tool.plans.filter(duration_type='monthly', is_active=True).first()
        price_ngn = plan.price_ngn if plan else tool.base_price_ngn

    # Create Order
    order = Order.objects.create(
        user=request.user,
        total_amount_ngn=price_ngn,
        delivery_email=request.user.email,
        status='pending',
    )
    OrderItem.objects.create(
        order=order,
        tool=tool,
        plan=plan,
        price_ngn=price_ngn,
    )

    pay_with_wallet = request.POST.get('pay_with_wallet') == 'true'

    if pay_with_wallet:
        profile = request.user.profile
        if profile.wallet_balance >= price_ngn:
            # Deduct wallet balance
            profile.wallet_balance -= price_ngn
            profile.save(update_fields=['wallet_balance'])
            
            # Update order
            order.status = 'paid'
            order.save(update_fields=['status'])
            
            # Record wallet transaction
            from accounts.models import WalletTransaction
            WalletTransaction.objects.create(
                user=request.user,
                transaction_type='purchase',
                amount_ngn=price_ngn,
                reference=f"ORDER_{order.id}",
                description=f"Purchased {tool.name}"
            )
            
            # Record payment transaction
            PaymentTransaction.objects.create(
                order=order,
                gateway='wallet',
                transaction_id=f"WALLET_{order.id}",
                reference=f"WALLET_{order.id}",
                status='success',
                amount_paid=price_ngn,
                currency_paid='NGN',
            )
            
            # Trigger delivery
            trigger_delivery(order)
            credit_referral_commission(order)
            
            messages.success(request, f"Payment successful! You purchased {tool.name} using your wallet.")
            return redirect(reverse('orders:confirmation', args=[order.id]))
        else:
            messages.error(request, "Insufficient wallet balance. Redirecting to Paystack.")
            # Fallback to paystack below

    # Generate Paystack payment reference
    reference = ps.generate_reference()
    order.paystack_reference = reference
    order.save(update_fields=['paystack_reference'])

    # Build callback URL
    callback_url = request.build_absolute_uri(
        reverse('orders:payment_callback')
    )

    # Initialize Paystack transaction
    try:
        auth_url, confirmed_ref = ps.initialize_transaction(
            email=request.user.email,
            amount_ngn=price_ngn,
            reference=reference,
            callback_url=callback_url,
            metadata={
                'order_id': order.id,
                'tool_name': tool.name,
                'user_id': request.user.id,
            }
        )
        # Record transaction
        PaymentTransaction.objects.create(
            order=order,
            gateway='paystack',
            transaction_id=confirmed_ref,
            reference=confirmed_ref,
            status='pending',
            amount_paid=price_ngn,
            currency_paid='NGN',
        )
        return redirect(auth_url)

    except ValueError as e:
        order.status = 'failed'
        order.save(update_fields=['status'])
        messages.error(request, f'Payment initialization failed: {e}')
        return redirect(reverse('tools:tool_detail', kwargs={'slug': tool_slug}))


# ─────────────────────────────────────────────────────────────
#  PAYMENT CALLBACK – verifies Paystack payment
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

    # Find order by reference
    try:
        order = Order.objects.select_related('user').get(paystack_reference=reference)
    except Order.DoesNotExist:
        messages.error(request, 'Order not found for this payment reference.')
        return redirect('/')

    # Don't re-process already-paid orders
    if order.status == 'paid':
        return redirect(reverse('orders:confirmation', kwargs={'order_id': order.id}))

    # Verify with Paystack API
    try:
        txn_data = ps.verify_transaction(reference)
        ps_status = txn_data.get('status')  # 'success', 'failed', etc.
        amount_paid_kobo = txn_data.get('amount', 0)
        amount_paid_ngn = Decimal(amount_paid_kobo) / 100

        if ps_status == 'success':
            # Mark order as paid
            order.status = 'paid'
            order.total_amount_ngn = amount_paid_ngn
            order.save(update_fields=['status', 'total_amount_ngn'])

            # Update payment transaction record
            PaymentTransaction.objects.filter(order=order).update(
                status='success',
                amount_paid=amount_paid_ngn,
                gateway_response=txn_data,
            )

            # Trigger delivery email
            trigger_delivery(order)

            # Credit referral commission (if applicable)
            credit_referral_commission(order)

            return redirect(reverse('orders:confirmation', kwargs={'order_id': order.id}))

        else:
            order.status = 'failed'
            order.save(update_fields=['status'])
            messages.error(request, 'Payment was not successful. Please try again.')
            return redirect('/')

    except ValueError as e:
        messages.error(request, f'Could not verify payment: {e}')
        return redirect('/')


# ─────────────────────────────────────────────────────────────
#  ORDER CONFIRMATION – success page
# ─────────────────────────────────────────────────────────────
@login_required(login_url='/auth/login/')
def order_confirmation_view(request, order_id):
    """Premium success page shown after successful payment."""
    order = get_object_or_404(
        Order.objects.prefetch_related('items__tool', 'items__plan'),
        id=order_id,
        user=request.user,
    )
    return render(request, 'orders/confirmation.html', {'order': order})
