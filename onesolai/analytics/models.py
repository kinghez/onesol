from django.db import models
from vendors.models import Vendor
from django.conf import settings

class VendorBalanceSnapshot(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='balance_snapshots')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.vendor.name} - ${self.balance} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class ActivityLog(models.Model):
    ACTION_TYPES = [
        ('user_signup', 'User Registration'),
        ('user_login', 'User Login'),
        ('user_logout', 'User Logout'),
        ('order_created', 'Order Created'),
        ('order_paid', 'Order Paid'),
        ('order_failed', 'Order Failed'),
        ('order_fulfilled', 'Order Fulfilled'),
        ('withdrawal_requested', 'Withdrawal Requested'),
        ('withdrawal_approved', 'Withdrawal Approved'),
        ('withdrawal_rejected', 'Withdrawal Rejected'),
        ('vendor_sync', 'Vendor Product Sync'),
        ('vendor_balance', 'Vendor Balance Check'),
        ('admin_action', 'Admin Action'),
        ('system', 'System Event'),
    ]

    SEVERITY_LEVELS = [
        ('info', 'Info'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_logs')
    action_type = models.CharField(max_length=30, choices=ACTION_TYPES, default='system', db_index=True)
    severity = models.CharField(max_length=15, choices=SEVERITY_LEVELS, default='info', db_index=True)
    title = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.title} ({self.timestamp.strftime('%Y-%m-%d %H:%M')})"

    @classmethod
    def log(cls, action_type, title, details='', user=None, severity='info', ip_address=None):
        """
        Helper method to record an activity log entry anywhere across the application.
        """
        try:
            return cls.objects.create(
                user=user,
                action_type=action_type,
                severity=severity,
                title=title,
                details=str(details) if details else '',
                ip_address=ip_address
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to record ActivityLog: {e}")
            return None

