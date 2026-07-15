from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from orders.models import OrderItem
from core.email_utils import send_alert

class Command(BaseCommand):
    help = 'Checks for expiring and expired subscriptions and sends email/in-app reminders.'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        
        # 1. Renewal Reminders (Expiring in exactly 3 days)
        # We look for items expiring between 3 days from now, and 3 days + 24 hours from now
        # to ensure we catch them once per daily run.
        three_days_from_now = now + timedelta(days=3)
        three_days_plus_one = three_days_from_now + timedelta(days=1)
        
        expiring_items = OrderItem.objects.filter(
            order__status='paid',
            expires_at__gte=three_days_from_now,
            expires_at__lt=three_days_plus_one
        )
        
        for item in expiring_items:
            user = item.order.user
            tool_name = item.tool.name if item.tool else "your tool"
            send_alert(
                user=user,
                title="Subscription Expiring Soon",
                message=f"Your subscription for {tool_name} will expire in 3 days. Please renew to avoid service interruption.",
                notification_type='order'
            )
            self.stdout.write(self.style.SUCCESS(f"Sent expiry reminder to {user.email} for {tool_name}"))

        # 2. Expiration Notices (Expired in the last 24 hours)
        yesterday = now - timedelta(days=1)
        
        expired_items = OrderItem.objects.filter(
            order__status='paid',
            expires_at__gte=yesterday,
            expires_at__lt=now
        )
        
        for item in expired_items:
            user = item.order.user
            tool_name = item.tool.name if item.tool else "your tool"
            send_alert(
                user=user,
                title="Subscription Expired",
                message=f"Your subscription for {tool_name} has expired. Please renew to regain access.",
                notification_type='order'
            )
            self.stdout.write(self.style.SUCCESS(f"Sent expiration notice to {user.email} for {tool_name}"))
            
        self.stdout.write(self.style.SUCCESS('Successfully checked all subscriptions!'))
