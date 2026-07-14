from django.db import models
from django.conf import settings
from products.models import Tool, SubscriptionPlan

ORDER_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('paid', 'Paid'),
    ('failed', 'Failed'),
    ('refunded', 'Refunded'),
    ('cancelled', 'Cancelled'),
]

PAYMENT_GATEWAY_CHOICES = [
    ('paystack', 'Paystack'),
    ('flutterwave', 'Flutterwave'),
    ('manual', 'Manual'),
]


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='orders', on_delete=models.CASCADE)
    total_amount_ngn = models.DecimalField(max_digits=10, decimal_places=2)
    local_currency = models.CharField(max_length=10, default='NGN')
    local_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True,
                                        help_text="Rate used at time of purchase")
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    # Delivery
    delivery_email = models.EmailField(blank=True, help_text="Email where access details are sent")
    delivery_status = models.CharField(max_length=20, default='pending',
                                       choices=[('pending','Pending'),('sent','Sent'),('failed','Failed')],
                                       help_text="Status of access delivery")
    delivery_notes = models.TextField(blank=True, help_text="Internal notes on delivery")
    access_details = models.TextField(blank=True,
        help_text='Credentials/access info delivered to user after payment')
    paystack_reference = models.CharField(max_length=200, blank=True,
        help_text='Paystack payment reference for this order')
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Referral tracking
    referred_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    related_name='referral_orders', on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} – {self.user.email} – {self.status.upper()}"

    @property
    def is_paid(self):
        return self.status == 'paid'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    tool = models.ForeignKey(Tool, on_delete=models.SET_NULL, null=True)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    price_ngn = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.IntegerField(default=30)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        tool_name = self.tool.name if self.tool else "Deleted Tool"
        return f"{tool_name} (Order #{self.order.id})"


class PaymentTransaction(models.Model):
    order = models.OneToOneField(Order, related_name='payment', on_delete=models.CASCADE)
    gateway = models.CharField(max_length=50, choices=PAYMENT_GATEWAY_CHOICES)
    transaction_id = models.CharField(max_length=200, unique=True)
    reference = models.CharField(max_length=200, blank=True, help_text="Gateway-specific reference")
    status = models.CharField(max_length=20, default='pending')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency_paid = models.CharField(max_length=10, default='NGN')
    gateway_response = models.JSONField(null=True, blank=True, help_text="Raw response from gateway")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.gateway.upper()} | {self.transaction_id} | {self.status}"


class RefundRequest(models.Model):
    REFUND_STATUS = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved & Refunded'),
        ('rejected', 'Rejected'),
    ]

    order = models.ForeignKey(Order, related_name='refund_requests', on_delete=models.CASCADE)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=REFUND_STATUS, default='pending')
    admin_note = models.TextField(blank=True, help_text="Note from admin on rejection or approval")
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Refund for Order #{self.order.id} [{self.status.upper()}]"
