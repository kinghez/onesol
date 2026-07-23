from django.db import models


DEFAULT_PRIVACY_POLICY_HTML = """<h2><i class="fas fa-info-circle"></i> 1. Introduction</h2>
<p>Welcome to <strong>OneSol AI Hub</strong> ("we," "our," or "us"). We operate as an online digital marketplace providing affordable access to premium Artificial Intelligence and Software-as-a-Service (SaaS) tools for individuals, creators, and businesses across Africa and worldwide.</p>
<p>This Privacy Policy explains how we collect, use, disclose, and safeguard your personal information when you visit our website, register an account, or purchase access to tools on our platform.</p>

<div class="legal-highlight-box">
    <strong>Key Summary:</strong> We never sell your personal data to third parties. We only collect the minimal information necessary to deliver access to your ordered software tools, process payments securely, and assist you via customer support.
</div>

<h2><i class="fas fa-database"></i> 2. Information We Collect</h2>
<p>We collect information you provide directly to us when interacting with our platform:</p>
<ul>
    <li><strong>Account & Contact Data:</strong> Full name, email address, country of residence, and account password when you register or make a purchase.</li>
    <li><strong>Transaction & Payment Information:</strong> Order history, billing currency, and payment status. <em>Note: We do not store your credit card numbers or banking PINs. All payment processing is securely handled by PCI-DSS compliant partners (Paystack & Flutterwave).</em></li>
    <li><strong>Technical & Usage Data:</strong> Your IP address, browser type, device information, operating system, and geolocation data used to set your local currency and language preferences.</li>
    <li><strong>Support & Communications:</strong> Records of your customer support inquiries via email or WhatsApp.</li>
</ul>

<h2><i class="fas fa-cogs"></i> 3. How We Use Your Information</h2>
<p>We process your data for the following essential business purposes:</p>
<ul>
    <li>To process orders and deliver tool activation credentials to your registered email address instantly.</li>
    <li>To display products in your local country currency and configure regional payment gateways.</li>
    <li>To manage your OneSol AI Hub user dashboard, order records, and referral commissions.</li>
    <li>To send important transaction receipts, delivery updates, security alerts, and system notices.</li>
    <li>To respond to your support queries and resolve technical issues quickly.</li>
    <li>To detect, prevent, and mitigate fraudulent activities, unauthorized abuse, or security breaches.</li>
</ul>

<h2><i class="fas fa-shield-alt"></i> 4. Data Protection & Security</h2>
<p>We implement robust technical and organizational security measures to protect your personal data against unauthorized access, loss, alteration, or disclosure. These measures include:</p>
<ul>
    <li>HTTPS / TLS 256-bit end-to-end encryption across all web pages and API communications.</li>
    <li>Secure hashed password storage utilizing Django's PBKDF2 encryption standard.</li>
    <li>Restricted admin access control and encrypted database storage for user credential delivery details.</li>
</ul>

<h2><i class="fas fa-share-alt"></i> 5. Sharing & Disclosure of Information</h2>
<p>We do not rent, sell, or trade your personal data. We may share information only under the following limited circumstances:</p>
<ul>
    <li><strong>Service Providers & Payment Processors:</strong> Trusted payment gateways (Paystack, Flutterwave) and automated tool delivery systems required to complete your purchase.</li>
    <li><strong>Legal Obligations:</strong> If required by law, court order, or governmental regulation to comply with legal processes or protect the rights, property, and safety of OneSol AI Hub and its users.</li>
</ul>

<h2><i class="fas fa-cookie-bite"></i> 6. Cookies & Local Storage</h2>
<p>We use essential cookies and browser local storage to maintain your active session, store your detected currency preference, and enable smooth website navigation. You may disable non-essential cookies via your browser settings, though certain interactive features of the platform may be affected.</p>

<h2><i class="fas fa-user-check"></i> 7. Your Rights & Choices</h2>
<p>You have full control over your personal information:</p>
<ul>
    <li><strong>Access & Correction:</strong> You can view and update your profile details at any time from your User Dashboard.</li>
    <li><strong>Email Preferences:</strong> You can unsubscribe from marketing newsletters at any time using the unsubscribe link provided in our emails.</li>
    <li><strong>Account Deletion:</strong> You may request permanent deletion of your account and associated data by contacting our support team.</li>
</ul>

<h2><i class="fas fa-envelope"></i> 8. Contact Us</h2>
<p>If you have any questions, concerns, or requests regarding this Privacy Policy, please reach out to us via support email or WhatsApp.</p>

<div class="updated-date">Last Updated: July 2026 | OneSol AI Hub Legal Team</div>"""


DEFAULT_TERMS_OF_SERVICE_HTML = """<h2><i class="fas fa-gavel"></i> 1. Acceptance of Terms</h2>
<p>By creating an account, browsing our website, or purchasing products on <strong>OneSol AI Hub</strong> ("the Platform"), you acknowledge that you have read, understood, and agreed to be legally bound by these Terms of Service ("Terms"). If you do not agree with any part of these Terms, you must discontinue use of our platform immediately.</p>

<h2><i class="fas fa-user-cog"></i> 2. Platform Description & Service Delivery</h2>
<p>OneSol AI Hub operates as an online marketplace facilitating affordable access to third-party AI and SaaS software products. Upon successful payment:</p>
<ul>
    <li>Your tool access details or account activation links are automatically processed and delivered to your registered email address and displayed in your User Dashboard.</li>
    <li>Tool subscriptions remain valid for the duration specified at checkout (e.g., 30-day monthly access, annual access, or single-use credits).</li>
    <li>You agree to use delivered credentials strictly for personal or business operations as intended by the software provider.</li>
</ul>

<h2><i class="fas fa-wallet"></i> 3. Pricing, Payments & Local Currency</h2>
<p>All prices displayed on OneSol AI Hub are converted dynamically to your local currency based on current exchange rates.</p>
<ul>
    <li>Payments are processed securely via authorized payment gateways (Paystack, Flutterwave) or your OneSol Wallet balance.</li>
    <li>We reserve the right to adjust product pricing, discount rates, or markup percentages at any time without prior notice.</li>
    <li>You are responsible for ensuring that your payment information is accurate and that sufficient funds are available to complete transactions.</li>
</ul>

<h2><i class="fas fa-user-lock"></i> 4. User Accounts & Responsibilities</h2>
<p>When registering an account with OneSol AI Hub, you agree to:</p>
<ul>
    <li>Provide accurate, current, and complete account details.</li>
    <li>Maintain the confidentiality of your login password and account credentials.</li>
    <li>Refrain from sharing, reselling, or publicly distributing delivered tool access details or sub-licensing access to unauthorized third parties.</li>
    <li>Not engage in automated scraping, malicious attacks, or activities that compromise the integrity or security of the Platform.</li>
</ul>

<div class="legal-highlight-box">
    <strong>Important Notice:</strong> Sharing or reselling OneSol AI Hub tool accounts to third parties without prior authorization will result in immediate termination of your account without refund.
</div>

<h2><i class="fas fa-handshake"></i> 5. Referral & Affiliate Program</h2>
<p>OneSol AI Hub offers a referral program allowing registered users to earn commissions by referring new customers:</p>
<ul>
    <li>Referral commissions are credited to your earnings wallet in accordance with the site's active referral rates.</li>
    <li>Self-referrals, fraudulent account creation, or attempt to manipulate referral links using fake accounts are strictly prohibited.</li>
    <li>Withdrawal requests are processed upon reaching the minimum withdrawal threshold (NGN 5,000 or equivalent) after admin verification.</li>
</ul>

<h2><i class="fas fa-ban"></i> 6. Intellectual Property & Third-Party Trademarks</h2>
<p>All brand names, product logos, software names (e.g., OpenAI, Canva, Claude, Gemini, ChatGPT) belong to their respective trademark owners and software vendors. OneSol AI Hub does not claim ownership of third-party software products sold on the platform.</p>

<h2><i class="fas fa-exclamation-triangle"></i> 7. Limitation of Liability</h2>
<p>To the maximum extent permitted by applicable law, OneSol AI Hub shall not be liable for any indirect, incidental, special, or consequential damages resulting from tool outages, third-party software vendor policy changes, or temporary service interruptions beyond our direct control.</p>

<h2><i class="fas fa-sync-alt"></i> 8. Amendments to Terms</h2>
<p>We reserve the right to revise or update these Terms of Service at any time. Continued use of OneSol AI Hub following any modifications constitutes your acceptance of the updated Terms.</p>

<h2><i class="fas fa-envelope"></i> 9. Contact Information</h2>
<p>For questions or clarifications regarding these Terms of Service, please contact our legal support team.</p>

<div class="updated-date">Last Updated: July 2026 | OneSol AI Hub Legal Team</div>"""


DEFAULT_REFUND_POLICY_HTML = """<h2><i class="fas fa-shield-heart"></i> 1. Our Customer Commitment</h2>
<p>At <strong>OneSol AI Hub</strong>, customer satisfaction is at the core of everything we do. Because we sell digital tool subscriptions and access credentials, we maintain a transparent, fair, and user-friendly refund and replacement policy to protect your purchase.</p>

<div class="legal-highlight-box">
    <strong>100% Replacement & Working Guarantee:</strong> If a tool access code or account fails to work upon delivery, or stops working within the warranty period due to technical issues, we guarantee a free replacement or instant wallet refund.
</div>

<h2><i class="fas fa-check-circle"></i> 2. Refund & Replacement Eligibility</h2>
<p>You are eligible for a replacement or full refund under the following conditions:</p>
<ul>
    <li><strong>Non-Delivery of Access Details:</strong> Payment was successfully debited from your account, but you did not receive activation details within 24 hours due to a delivery glitch.</li>
    <li><strong>Defective or Non-Working Access Code:</strong> The provided activation link, promo code, or account credentials fail to grant access upon first use.</li>
    <li><strong>Tool Outage During Warranty Period:</strong> If a tool subscription stops functioning prior to the expiration of its advertised coverage period and our team is unable to restore or replace access within 48 hours.</li>
    <li><strong>Duplicate Billing:</strong> You were inadvertently charged twice for a single order transaction.</li>
</ul>

<h2><i class="fas fa-times-circle"></i> 3. Non-Refundable Scenarios</h2>
<p>Refunds or replacements will NOT be issued under the following circumstances:</p>
<ul>
    <li>Change of mind after tool activation details have been accessed or utilized.</li>
    <li>Incompatibility of third-party tools with your personal computer or local network settings when product system requirements were clearly stated.</li>
    <li>Violation of OneSol AI Hub Terms of Service, such as account sharing, reselling access, or attempting to compromise tool security.</li>
    <li>Requests submitted after the tool's specified warranty period has expired.</li>
</ul>

<h2><i class="fas fa-headset"></i> 4. How to Submit a Refund or Support Claim</h2>
<p>Submitting a claim is simple and fast. Follow these steps:</p>
<ul>
    <li>Contact our dedicated support team via Email or WhatsApp.</li>
    <li>Provide your <strong>Order ID</strong> (found in your User Dashboard or email receipt) and a brief description/screenshot of the issue encountered.</li>
    <li>Our support technical team will review and verify your request within 2–12 hours.</li>
</ul>

<h2><i class="fas fa-exchange-alt"></i> 5. Processing & Refund Methods</h2>
<p>Once approved by our support team, refunds are processed via one of the following methods according to your preference:</p>
<ul>
    <li><strong>OneSol Wallet Balance (Recommended & Instant):</strong> Refunded directly to your OneSol AI Hub wallet for immediate use on any other tool.</li>
    <li><strong>Original Payment Source:</strong> Refunded back to your Paystack / Flutterwave card or bank account within 3–5 business days depending on your bank.</li>
</ul>

<h2><i class="fas fa-comments"></i> 6. Contact & Support</h2>
<p>For any questions or assistance with an existing order, please get in touch with our team.</p>

<div class="updated-date">Last Updated: July 2026 | OneSol AI Hub Legal Team</div>"""


class CurrencyRate(models.Model):
    currency_code = models.CharField(max_length=10, unique=True)
    rate_to_ngn = models.DecimalField(max_digits=10, decimal_places=4)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.currency_code} - {self.rate_to_ngn}"


class SiteSettings(models.Model):
    """Singleton model for site-wide configuration managed from admin panel."""
    # Payment Gateways Configuration
    is_paystack_enabled = models.BooleanField(default=True, help_text='Enable Paystack payment gateway on checkout.')
    is_flutterwave_enabled = models.BooleanField(default=True, help_text='Enable Flutterwave payment gateway on checkout.')
    primary_payment_gateway = models.CharField(max_length=20, default='paystack', choices=[
        ('paystack', 'Paystack (Primary)'),
        ('flutterwave', 'Flutterwave (Primary)'),
    ], help_text='Primary gateway used for payments. Platform will fallback to secondary gateway if primary fails, is disabled, or does not support user currency.')

    # Paystack Keys
    paystack_public_key = models.CharField(max_length=200, blank=True, default='',
        help_text='Paystack public key (pk_test_... or pk_live_...)')
    paystack_secret_key = models.CharField(max_length=200, blank=True, default='',
        help_text='Paystack secret key (sk_test_... or sk_live_...)')
    
    # Flutterwave Keys
    flutterwave_public_key = models.CharField(max_length=200, blank=True, default='',
        help_text='Flutterwave public key (FLWPUBK_TEST-... or FLWPUBK_LIVE-...)')
    flutterwave_secret_key = models.CharField(max_length=200, blank=True, default='',
        help_text='Flutterwave secret key (FLWSECK_TEST-... or FLWSECK_LIVE-...)')
    flutterwave_encryption_key = models.CharField(max_length=200, blank=True, default='',
        help_text='Flutterwave encryption key (optional)')

    is_live_mode = models.BooleanField(default=False,
        help_text='When enabled, live payment gateway keys are used. Keep OFF during testing.')
    transaction_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=1.50,
        help_text='% fee added to each transaction (e.g. 1.50 = 1.5%)')

    # Legal Pages Content (Admin Editable)
    privacy_policy_content = models.TextField(blank=True, default=DEFAULT_PRIVACY_POLICY_HTML,
        help_text='Custom HTML or text for Privacy Policy page. Edit or replace this text anytime.')
    terms_of_service_content = models.TextField(blank=True, default=DEFAULT_TERMS_OF_SERVICE_HTML,
        help_text='Custom HTML or text for Terms of Service page. Edit or replace this text anytime.')
    refund_policy_content = models.TextField(blank=True, default=DEFAULT_REFUND_POLICY_HTML,
        help_text='Custom HTML or text for Refund Policy page. Edit or replace this text anytime.')

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

    # Social Media Links
    facebook_url = models.URLField(max_length=500, blank=True, default='https://www.facebook.com/share/189F1zob2d/?mibextid=wwXIfr',
        help_text='Facebook page URL')
    twitter_url = models.URLField(max_length=500, blank=True, default='',
        help_text='Twitter / X profile URL')
    instagram_url = models.URLField(max_length=500, blank=True, default='',
        help_text='Instagram profile URL')
    linkedin_url = models.URLField(max_length=500, blank=True, default='',
        help_text='LinkedIn page URL')
    youtube_url = models.URLField(max_length=500, blank=True, default='',
        help_text='YouTube channel URL')
    whatsapp_number = models.CharField(max_length=50, blank=True, default='+2349110585508',
        help_text='WhatsApp support phone number e.g. +2349110585508')

    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'

    def __str__(self):
        mode = 'LIVE' if self.is_live_mode else 'TEST'
        return f'Site Settings [{mode} MODE]'

    @classmethod
    def get(cls):
        """Always returns the singleton instance, populating legal contents if missing."""
        obj, created = cls.objects.get_or_create(pk=1)
        needs_save = False
        if not obj.privacy_policy_content:
            obj.privacy_policy_content = DEFAULT_PRIVACY_POLICY_HTML
            needs_save = True
        if not obj.terms_of_service_content:
            obj.terms_of_service_content = DEFAULT_TERMS_OF_SERVICE_HTML
            needs_save = True
        if not obj.refund_policy_content:
            obj.refund_policy_content = DEFAULT_REFUND_POLICY_HTML
            needs_save = True

        if needs_save:
            obj.save()
        return obj


class NewsletterSubscriber(models.Model):
    """Stores email subscriptions from the website footer/newsletter form."""
    email = models.EmailField(unique=True, help_text="Subscriber's email address")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Newsletter Subscriber'
        verbose_name_plural = 'Newsletter Subscribers'
        ordering = ['-created_at']

    def __str__(self):
        return self.email


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
