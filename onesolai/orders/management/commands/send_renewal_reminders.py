from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from orders.models import OrderItem
from core.models import SiteSettings
from notifications.models import Notification

class Command(BaseCommand):
    help = 'Sends renewal reminder emails and in-app notifications for subscriptions expiring in 3 and 1 days'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        target_days = [3, 1]
        
        site_settings = SiteSettings.objects.first()
        site_name = site_settings.site_name if site_settings else 'OneSol AI Hub'
        site_url = site_settings.site_url if site_settings else 'http://127.0.0.1:8000'
        support_email = site_settings.support_email if site_settings else settings.DEFAULT_FROM_EMAIL

        total_sent = 0
        
        for days in target_days:
            start_window = now + timedelta(days=days)
            end_window = start_window + timedelta(hours=24)
            
            expiring_items = OrderItem.objects.filter(
                expires_at__gte=start_window,
                expires_at__lt=end_window,
                order__status='paid'
            ).select_related('order__user', 'tool', 'plan')
            
            for item in expiring_items:
                user = item.order.user
                tool_name = item.tool.name if item.tool else "Tool"
                
                # 1. Create In-App Notification
                Notification.objects.create(
                    user=user,
                    title=f"Subscription Expiring Soon",
                    message=f"Your subscription to {tool_name} will expire in {days} day(s). Please renew to maintain access.",
                    notification_type='system',
                    action_url=f"/tools/{item.tool.slug}/" if item.tool else "/tools/"
                )
                
                # 2. Send Email Reminder
                subject = f"Action Required: Your {tool_name} subscription expires in {days} day(s)"
                context = {
                    'user': user,
                    'item': item,
                    'days_remaining': days,
                    'site_name': site_name,
                    'site_url': site_url,
                    'support_email': support_email
                }
                
                html_content = render_to_string('emails/renewal_reminder.html', context)
                
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=f"Your {tool_name} subscription expires in {days} day(s). Renew at {site_url}/tools/",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user.email]
                )
                msg.attach_alternative(html_content, "text/html")
                try:
                    msg.send(fail_silently=True)
                    total_sent += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to send email to {user.email}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f'Successfully sent {total_sent} renewal reminders'))
