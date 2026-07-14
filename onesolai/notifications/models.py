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
