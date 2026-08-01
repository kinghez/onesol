from django.db import models
from django.conf import settings
from django.contrib.auth.models import Group

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('system', 'System Notification'),
        ('order', 'Order Delivery / Update'),
        ('referral', 'Referral Commission'),
        ('promotion', 'Promotional Offer'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='notifications', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, default='system')
    is_read = models.BooleanField(default=False)
    action_url = models.CharField(max_length=255, blank=True, null=True, help_text="Optional URL to redirect user when clicked")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'In-App Notification'
        verbose_name_plural = 'In-App Notifications'

    def __str__(self):
        return f"{self.user.email} - {self.title}"


class BroadcastEmail(models.Model):
    TARGET_CHOICES = [
        ('all', 'All Users'),
        ('single', 'Single Specific User'),
        ('group', 'User Group (Role)'),
    ]

    target_type = models.CharField(max_length=20, choices=TARGET_CHOICES, default='all', help_text="Who should receive this email?")
    recipient_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_broadcast_emails', help_text="Required if 'Single Specific User' is selected.")
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, help_text="Required if 'User Group (Role)' is selected.")
    subject = models.CharField(max_length=255)
    message = models.TextField(help_text="Body content of the email.")
    recipients_count = models.PositiveIntegerField(default=0, help_text="Total number of users who were sent this email.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Broadcast Email'
        verbose_name_plural = 'Broadcast Emails'

    def __str__(self):
        return f"Email: {self.subject} ({self.get_target_type_display()})"
