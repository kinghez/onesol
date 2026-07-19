from django.db import models


class CurrencyRate(models.Model):
    currency_code = models.CharField(max_length=10, unique=True)
    rate_to_ngn = models.DecimalField(max_digits=10, decimal_places=4)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.currency_code} - {self.rate_to_ngn}"


class SiteSettings(models.Model):
    """Singleton model for site-wide configuration managed from admin panel."""
    # Paystack
    paystack_public_key = models.CharField(max_length=200, blank=True, default='',
        help_text='Paystack public key (pk_test_... or pk_live_...)')
    paystack_secret_key = models.CharField(max_length=200, blank=True, default='',
        help_text='Paystack secret key (sk_test_... or sk_live_...)')
    is_live_mode = models.BooleanField(default=False,
        help_text='When enabled, live Paystack keys are used. Keep OFF during testing.')
    transaction_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=1.50,
        help_text='% fee added to each transaction (e.g. 1.50 = 1.5%)')
    # Referral
    referral_commission_type = models.CharField(max_length=20, default='fixed', choices=[
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Sale'),
    ], help_text="Type of commission paid out to the referrer.")
    referral_commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=10.00,
        help_text='% commission if "Percentage" is selected above (e.g. 10.00 = 10%)')
    referral_commission_ngn = models.DecimalField(max_digits=10, decimal_places=2, default=2000.00,
        help_text='Fixed NGN commission if "Fixed Amount" is selected above.')
    referral_reward_frequency = models.CharField(max_length=30, default='every_purchase', choices=[
        ('first_purchase', 'Only on First Purchase'),
        ('every_purchase', 'On Every Subscription Purchase'),
    ], help_text="How often should the referrer get paid for a referred user's purchases?")
    min_withdrawal_ngn = models.DecimalField(max_digits=10, decimal_places=2, default=5000.00,
        help_text='Minimum NGN balance required to submit a withdrawal request')
    # Support email
    support_email = models.EmailField(default='support@onesolai.com')
    # Site name / branding
    site_name = models.CharField(max_length=100, default='OneSol AI Hub')
    site_url = models.URLField(default='https://onesolai.com',
        help_text='Full site URL including https (used in emails and referral links)')
    site_logo = models.ImageField(upload_to='site_logos/', blank=True, null=True,
        help_text='Upload the site logo to replace the default one')
    site_favicon = models.ImageField(upload_to='site_logos/', blank=True, null=True,
        help_text='Upload the site favicon (ideally 32x32 or 64x64). If not provided, site logo is used.')

    # Global Pricing Settings
    global_markup_percent = models.DecimalField(max_digits=5, decimal_places=2, default=20.00,
        help_text='% to add to vendor USD price for profit (e.g. 20.00 = 20%)')
    global_markup_fixed_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,
        help_text='Fixed USD profit to add instead of percentage. If greater than 0, overrides percentage.')
    usd_to_ngn_rate = models.DecimalField(max_digits=10, decimal_places=2, default=1500.00,
        help_text='Exchange rate to convert USD to local currency (NGN) on the frontend')

    # AI Configuration (OpenRouter)
    openrouter_api_key = models.CharField(max_length=200, blank=True, default='',
        help_text='OpenRouter API Key for refining product descriptions')
    openrouter_model = models.CharField(max_length=100, default='openrouter/free',
        help_text='OpenRouter Model ID (e.g., openrouter/free, openrouter/auto, google/gemini-2.5-flash)')

    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'

    def __str__(self):
        mode = 'LIVE' if self.is_live_mode else 'TEST'
        return f'Site Settings [{mode} MODE]'

    @classmethod
    def get(cls):
        """Always returns the singleton instance, creating it if it doesn't exist."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class HeroSlide(models.Model):
    title_line_1 = models.CharField(max_length=100, blank=True)
    title_line_2_start = models.CharField(max_length=100, blank=True)
    title_line_2_highlight = models.CharField(max_length=100, blank=True)
    title_line_2_end = models.CharField(max_length=100, blank=True)
    title_line_3 = models.CharField(max_length=100, blank=True)
    
    description = models.TextField(blank=True, help_text="HTML allowed (e.g. <br>)")
    
    image = models.ImageField(upload_to='hero_images/', blank=True, null=True)
    
    primary_button_text = models.CharField(max_length=50, blank=True)
    primary_button_url = models.CharField(max_length=255, blank=True)
    primary_button_icon = models.CharField(max_length=50, blank=True, help_text="e.g. fas fa-compass")
    
    secondary_button_text = models.CharField(max_length=50, blank=True)
    secondary_button_url = models.CharField(max_length=255, blank=True)
    
    show_features_block = models.BooleanField(default=False, help_text="Show the features block (Local currency, Instant delivery, etc) below description.")
    
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = 'Hero Slide'
        verbose_name_plural = 'Hero Slides'

    def __str__(self):
        return self.title_line_1 or f"Hero Slide {self.id}"
