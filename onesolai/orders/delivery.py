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
    items = order.items.select_related('tool', 'plan').all()
    tool_name = items.first().tool.name if items.exists() else 'Your Tool'

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
        
        # In-App Notification
        from notifications.models import Notification
        Notification.objects.create(
            user=order.user,
            title="Order Delivered",
            message=f"Your order #{order.id} for {tool_name} has been processed successfully.",
            notification_type='order',
            action_url=f"/dashboard/orders/"
        )
    except Exception:
        order.delivery_status = 'failed'

    order.save(update_fields=['delivery_status'])


def credit_referral_commission(order):
    """
    If the buyer was referred, credit the referrer's earnings balance.
    Called only on first successful purchase by the referred user.
    """
    try:
        from accounts.models import Referral
        from core.models import SiteSettings

        # Check if buyer has a referral record
        referral = Referral.objects.select_related('referrer__profile').get(
            referred_user=order.user,
            status='pending',
        )
        cfg = SiteSettings.get()
        commission = cfg.referral_commission_ngn

        # Credit referrer's earnings
        referrer_profile = referral.referrer.profile
        referrer_profile.earnings += commission
        referrer_profile.save(update_fields=['earnings'])

        # Update referral status
        referral.status = 'rewarded'
        referral.reward_amount_ngn = commission
        referral.save(update_fields=['status', 'reward_amount_ngn'])

        # Link order to referrer
        order.referred_by = referral.referrer
        order.save(update_fields=['referred_by'])
        
        # Notify the referrer
        from notifications.models import Notification
        Notification.objects.create(
            user=referral.referrer,
            title="Referral Commission Earned!",
            message=f"You earned NGN {commission:,.2f} from a successful referral.",
            notification_type='referral',
            action_url="/dashboard/referrals/"
        )

    except Referral.DoesNotExist:
        pass  # Not a referred user – no action needed
    except Exception:
        pass  # Never crash the payment confirmation flow
