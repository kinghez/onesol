from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid


#============SUPERUSER DETAILS=================
#Superuser Created:
#Login: admin@onesolai.com
#Password: adminpassword123


class User(AbstractUser):
    """Extended user model."""
    email = models.EmailField(unique=True)

    # Make email the login field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    def get_short_name(self):
        return self.first_name or self.username


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    referral_code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    country_preference = models.CharField(max_length=50, blank=True, null=True)
    currency_preference = models.CharField(max_length=10, default='NGN')
    avatar_url = models.URLField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    
    # Financial & Payout Details
    bank_name = models.CharField(max_length=100, blank=True, default='')
    account_number = models.CharField(max_length=30, blank=True, default='')
    account_name = models.CharField(max_length=150, blank=True, default='')
    crypto_wallet_address = models.CharField(max_length=300, blank=True, default='')
    crypto_network = models.CharField(max_length=50, blank=True, default='USDT (TRC20)')
    preferred_withdrawal_method = models.CharField(
        max_length=20, 
        choices=[('bank', 'Bank Transfer'), ('crypto', 'Crypto (USDT)')], 
        default='bank'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email}'s Profile"

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = str(uuid.uuid4()).replace('-', '').upper()[:12]
        super().save(*args, **kwargs)

    @property
    def referral_link(self):
        return f"/auth/signup/?ref={self.referral_code}"

    @property
    def has_payout_details(self):
        """Returns True if user has configured bank details or crypto wallet."""
        has_bank = bool(self.bank_name and self.account_number and self.account_name)
        has_crypto = bool(self.crypto_wallet_address)
        return has_bank or has_crypto


class Referral(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('rewarded', 'Rewarded'),
    ]
    referrer = models.ForeignKey(User, related_name='referrals_made', on_delete=models.CASCADE)
    referred_user = models.OneToOneField(User, related_name='referred_by', on_delete=models.CASCADE)
    reward_amount_ngn = models.DecimalField(max_digits=10, decimal_places=2, default=2000.00)
    date_referred = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.referrer.email} → {self.referred_user.email} ({self.status})"

WITHDRAWAL_STATUS = [
    ('pending', 'Pending Review'),
    ('approved', 'Approved & Paid'),
    ('rejected', 'Rejected'),
]

class WithdrawalRequest(models.Model):
    METHOD_CHOICES = [
        ('bank', 'Bank Transfer'),
        ('crypto', 'Crypto (USDT)'),
    ]
    user = models.ForeignKey(User, related_name='withdrawal_requests', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    withdrawal_method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='bank')
    bank_name = models.CharField(max_length=100, blank=True, default='')
    account_number = models.CharField(max_length=30, blank=True, default='')
    account_name = models.CharField(max_length=150, blank=True, default='')
    crypto_wallet_address = models.CharField(max_length=300, blank=True, default='')
    crypto_network = models.CharField(max_length=50, blank=True, default='USDT (TRC20)')
    status = models.CharField(max_length=20, choices=WITHDRAWAL_STATUS, default='pending')
    admin_note = models.TextField(blank=True, help_text='Note from admin on rejection or approval')
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        method_str = 'Crypto' if self.withdrawal_method == 'crypto' else 'Bank'
        return f'{self.user.email} – NGN {self.amount:,.0f} [{method_str}] [{self.status.upper()}]'


class WalletTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit / Top-up'),
        ('purchase', 'Tool Purchase'),
        ('withdrawal', 'Withdrawal'),
        ('referral_credit', 'Referral Credit'),
    ]
    user = models.ForeignKey(User, related_name='wallet_transactions', on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount_ngn = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=200, blank=True, null=True, help_text="Payment gateway reference or internal ID")
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.transaction_type} - {self.amount_ngn}"


from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        try:
            from analytics.models import ActivityLog
            ActivityLog.log('user_signup', f"New user registered: {instance.email}", user=instance, severity='success')
        except Exception:
            pass

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    try:
        from analytics.models import ActivityLog
        from accounts.utils import get_client_ip
        ip = get_client_ip(request) if request else None
        ActivityLog.log('user_login', f"User logged in: {user.email}", user=user, severity='info', ip_address=ip)
    except Exception:
        pass

@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    try:
        from analytics.models import ActivityLog
        from accounts.utils import get_client_ip
        ip = get_client_ip(request) if request else None
        email = credentials.get('username') or credentials.get('email') or 'Unknown'
        ActivityLog.log('user_login', f"Failed login attempt for: {email}", severity='warning', ip_address=ip)
    except Exception:
        pass

