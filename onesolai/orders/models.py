from django.db import models
from django.conf import settings
from products.models import Tool

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
    ('wallet', 'Wallet Balance'),
    ('crypto', 'Crypto USDT'),
    ('manual', 'Manual'),
]


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name='orders', on_delete=models.SET_NULL)
    claim_token = models.CharField(max_length=100, blank=True, null=True, db_index=True, help_text="Token for unregistered user to claim order upon signup")
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
    vendor_order_id = models.CharField(max_length=255, blank=True, null=True,
        verbose_name="Vendor Order ID",
        help_text="Third-party vendor API order reference for admin reconciliation")
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Referral tracking
    referred_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    related_name='referral_orders', on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        email_str = self.user.email if self.user else (self.delivery_email or 'Guest')
        return f"Order #{self.order_number} ({self.id}) – {email_str} – {self.status.upper()}"

    @property
    def order_number(self):
        """Returns a standardized trackable order identifier like OS-00025."""
        return f"OS-{self.id:05d}"

    @property
    def is_paid(self):
        return self.status == 'paid'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    tool = models.ForeignKey(Tool, on_delete=models.SET_NULL, null=True)
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


class OrderAPIRequest(models.Model):
    """Logs third-party vendor API purchase requests and responses."""
    order = models.ForeignKey(Order, related_name='api_requests', on_delete=models.CASCADE)
    vendor = models.ForeignKey('vendors.Vendor', on_delete=models.SET_NULL, null=True, blank=True)
    vendor_product = models.ForeignKey('vendors.VendorProduct', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=50, default='pending')  # pending, completed, pending_manual, failed
    vendor_order_id = models.CharField(max_length=200, blank=True, default='')
    request_data = models.JSONField(null=True, blank=True)
    response_data = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Vendor API Request'
        verbose_name_plural = 'Vendor API Requests'

    def __str__(self):
        v_name = self.vendor.name if self.vendor else "Unknown Vendor"
        return f"Order #{self.order.id} API Request → {v_name} [{self.status}]"



class ManualBankAccount(models.Model):
    payment_method_name = models.CharField(max_length=100, verbose_name="Bank / Payment Provider Name", help_text="e.g. UBA Bank, MTN MoMo, Telecel, Mpesa, Providus Bank")
    account_number = models.CharField(max_length=100, help_text="Bank account number or MoMo phone number")
    account_name = models.CharField(max_length=150, help_text="Account holder name")
    supported_regions = models.CharField(max_length=150, blank=True, default="All Regions / Africa", help_text="e.g. Nigeria & Africa, Cameroon (XAF), Ghana (GHS), Kenya (KES)")
    currency_code = models.CharField(max_length=10, blank=True, default="ALL", help_text="e.g. XAF, GHS, KES, NGN, UGX, TZS or ALL")
    additional_instructions = models.TextField(blank=True, help_text="Specific transfer notes (e.g. Include TxID & sender name)")
    country_code = models.CharField(max_length=10, blank=True, null=True, default='')
    country_name = models.CharField(max_length=100, blank=True, null=True, default='')
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'payment_method_name']
        verbose_name = 'Manual Bank Account'
        verbose_name_plural = 'Manual Bank Accounts'

    def __str__(self):
        return f"{self.payment_method_name}: {self.account_number} ({self.account_name}) – {self.supported_regions}" 


class ManualPaymentProof(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Verification'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    order = models.ForeignKey(Order, related_name='manual_proofs', on_delete=models.CASCADE, null=True, blank=True)
    wallet_transaction = models.ForeignKey('accounts.WalletTransaction', related_name='manual_proofs', on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='manual_proofs', on_delete=models.CASCADE)
    payment_channel_used = models.CharField(max_length=100, help_text="e.g. MTN MoMo, Telecel, Providus Bank, Mpesa")
    sender_name_or_txid = models.CharField(max_length=200, help_text="Sender name or Transaction ID")
    proof_file = models.FileField(upload_to='manual_proofs/', help_text="Uploaded payment screenshot or PDF receipt")
    amount_local = models.DecimalField(max_digits=12, decimal_places=2, help_text="Amount in user local currency")
    currency = models.CharField(max_length=10, default='NGN')
    amount_ngn = models.DecimalField(max_digits=12, decimal_places=2, help_text="Converted base NGN amount")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, help_text="Reason for rejection or admin notes")
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Manual Payment Proof'
        verbose_name_plural = 'Manual Payment Proofs'

    def __str__(self):
        type_str = f"Order #{self.order.order_number}" if self.order else f"Wallet Ref {self.wallet_transaction.reference if self.wallet_transaction else 'N/A'}"
        return f"Proof for {type_str} | {self.currency} {self.amount_local} [{self.status.upper()}]"
