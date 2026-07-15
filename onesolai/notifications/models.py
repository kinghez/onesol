from django.db import models
from django.conf import settings

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('system', 'System'),
        ('order', 'Order'),
        ('referral', 'Referral'),
        ('promotion', 'Promotion'),
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

    def __str__(self):
        return f"{self.user.email} - {self.title}"

class BroadcastMessage(models.Model):
    subject = models.CharField(max_length=255)
    message = models.TextField()
    send_email = models.BooleanField(default=True, help_text="Send as an email to all users")
    send_in_app = models.BooleanField(default=True, help_text="Create an in-app notification for all users")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Broadcast: {self.subject}"
