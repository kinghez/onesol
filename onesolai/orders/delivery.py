"""
Delivery logic for OneSol AI Hub.
Called after a successful Paystack payment is verified.
"""
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def trigger_delivery(order):
    """
    Trigger access delivery for a paid order:
    1. Send confirmation email to user
    2. Mark delivery_status = 'sent' on order
    """
    try:
        from core.models import SiteSettings
        cfg = SiteSettings.get()
        support_email = cfg.support_email
        site_name = cfg.site_name
    except Exception:
        support_email = 'support@onesolai.com'
        site_name = 'OneSol AI Hub'

    # Build context for email
    items = order.items.select_related('tool').all()
    tool_name = items.first().tool.name if (items.exists() and items.first().tool) else 'Your Tool'

    context = {
        'order': order,
        'items': items,
        'tool_name': tool_name,
        'user': order.user,
        'site_name': site_name,
        'support_email': support_email,
    }

    # Send HTML email
    try:
        html_message = render_to_string('emails/order_confirmation.html', context)
        plain_message = strip_tags(html_message)
        recipient = order.delivery_email or order.user.email

        send_mail(
            subject=f'\u2705 Your {tool_name} access is ready \u2013 {site_name}',
            message=plain_message,
            from_email=f'{site_name} <{support_email}>',
            recipient_list=[recipient],
            html_message=html_message,
            fail_silently=True,
        )
        order.delivery_status = 'sent'
        
        # In-App Notification with Full Activation Details
        from notifications.models import Notification
        notif_msg = f"Your order #{order.order_number} for {tool_name} is ready!"
        if order.access_details:
            notif_msg += f"\n\nActivation Details:\n{order.access_details}"

        if order.user:
            Notification.objects.create(
                user=order.user,
                title=f"🎉 {tool_name} Access Delivered!",
                message=notif_msg,
                notification_type='order',
                action_url=f"/dashboard/orders/"
            )
    except Exception as e:
        import traceback
        print(f"Error in trigger_delivery for Order #{order.id}: {e}\n{traceback.format_exc()}")
        order.delivery_status = 'failed'

    order.save(update_fields=['delivery_status'])

    # Check if this order contains a manual tool (no vendor product attached)
    has_manual_tool = any(not item.tool or not item.tool.vendor_product for item in items)
    if has_manual_tool:
        send_support_manual_order_alert(order, tool_name)

    # Dispatch Developer Webhook if user configured one
    dispatch_developer_webhook(order)


def dispatch_developer_webhook(order):
    """
    Sends an HTTP POST webhook to user's registered developer webhook URL when order is fulfilled.
    """
    try:
        import hmac, hashlib, json, time, requests
        from accounts.models import DeveloperWebhook
        dev_webhook = DeveloperWebhook.objects.filter(user=order.user, is_active=True).first()
        if not dev_webhook or not dev_webhook.webhook_url:
            return

        items = order.items.select_related('tool').all()
        tool_name = items.first().tool.name if (items.exists() and items.first().tool) else 'Tool'

        payload = {
            'event': 'order.fulfilled',
            'order_id': order.id,
            'order_number': order.order_number,
            'tool_name': tool_name,
            'delivery_email': order.delivery_email,
            'access_details': order.access_details or '',
            'total_amount_ngn': float(order.total_amount_ngn),
            'fulfilled_at': order.updated_at.isoformat() if hasattr(order, 'updated_at') else order.created_at.isoformat()
        }

        payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        timestamp = str(int(time.time()))
        signature_payload = f"t={timestamp}.".encode('utf-8') + payload_bytes
        signature = hmac.new(dev_webhook.secret.encode('utf-8'), signature_payload, hashlib.sha256).hexdigest()

        headers = {
            'Content-Type': 'application/json',
            'X-OneSol-Signature': f"t={timestamp},v1={signature}"
        }

        requests.post(dev_webhook.webhook_url, data=payload_bytes, headers=headers, timeout=5)
    except Exception as e:
        print(f"Webhook dispatch error for Order #{order.id}: {e}")



def credit_referral_commission(order):
    """
    If the buyer was referred, credit the referrer's earnings balance.
    Respects the admin settings for frequency (first vs every) and type (fixed vs %).
    """
    try:
        from accounts.models import Referral, WalletTransaction
        from core.models import SiteSettings
        from decimal import Decimal

        # Check if buyer has a referral record
        referral = Referral.objects.select_related('referrer__profile').filter(
            referred_user=order.user
        ).first()

        if not referral:
            return

        cfg = SiteSettings.get()
        
        # Frequency Check
        if cfg.referral_reward_frequency == 'first_purchase' and referral.status == 'rewarded':
            return  # They already got paid for the first purchase

        # Calculation Check
        if cfg.referral_commission_type == 'percentage':
            commission = (cfg.referral_commission_percentage / Decimal('100.00')) * order.total_amount_ngn
        else:
            commission = cfg.referral_commission_ngn

        # Credit referrer's earnings
        referrer_profile = referral.referrer.profile
        referrer_profile.earnings += commission
        referrer_profile.save(update_fields=['earnings'])

        # Update referral status and cumulative amount
        referral.status = 'rewarded'
        if not referral.reward_amount_ngn:
            referral.reward_amount_ngn = commission
        else:
            referral.reward_amount_ngn += commission
        referral.save(update_fields=['status', 'reward_amount_ngn'])

        # Record wallet transaction for the referrer
        WalletTransaction.objects.create(
            user=referral.referrer,
            transaction_type='referral_credit',
            amount_ngn=commission,
            reference=f"REF_ORDER_{order.id}",
            description=f"Referral commission from {order.user.email}"
        )

        # Link order to referrer
        order.referred_by = referral.referrer
        order.save(update_fields=['referred_by'])
        
        # Notify the referrer
        from notifications.models import Notification
        Notification.objects.create(
            user=referral.referrer,
            title="Referral Commission Earned!",
            message=f"You earned NGN {commission:,.2f} from a successful referral purchase.",
            notification_type='referral',
            action_url="/dashboard/referrals/"
        )

    except Exception as e:
        print(f"Error in credit_referral_commission: {e}")
        pass  # Never crash the payment confirmation flow


def send_support_manual_order_alert(order, tool_name):
    """
    Sends an email notification to support@onesolai.com when a customer purchases a manual tool.
    """
    try:
        from core.models import SiteSettings
        cfg = SiteSettings.get()
        support_email = cfg.support_email or 'support@onesolai.com'
    except Exception:
        support_email = 'support@onesolai.com'

    subject = f"🔔 [MANUAL TOOL ORDER] Action Required for Order #{order.order_number} ({tool_name})"
    cust_email = order.delivery_email or (order.user.email if order.user else 'Unregistered User')
    
    body = f"""Hello Support Team,

A customer has just purchased a MANUAL TOOL on OneSol AI Hub. Please prepare and deliver the credentials to the customer as soon as possible.

--- ORDER DETAILS ---
Order Number: #{order.order_number}
Tool Purchased: {tool_name}
Customer Email: {cust_email}
Amount Charged: ₦{order.total_amount_ngn:,.2f} NGN ({order.local_currency} {order.local_amount:,.2f})
Payment Status: PAID
Delivery Status: Manual Action Required

Please process this delivery and update the order details in Django Admin.

OneSol AI System Notification
"""
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=f"OneSol System <{support_email}>",
            recipient_list=['support@onesolai.com', support_email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"Error sending support manual order alert: {e}")

