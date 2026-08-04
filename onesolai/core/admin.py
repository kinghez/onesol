from django.contrib import admin

# ─────────────────────────────────────────────
# Admin site branding
# ─────────────────────────────────────────────
admin.site.site_header = "OneSol AI Hub – Admin"
admin.site.site_title = "OneSol Admin"
admin.site.index_title = "Site Management Dashboard"

from django.utils.html import format_html
from .models import SiteSettings, HeroSlide, NewsletterSubscriber, Testimonial, FAQ, ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'category', 'subject', 'status_badge', 'created_at')
    list_filter = ('is_resolved', 'category', 'created_at')
    search_fields = ('full_name', 'email', 'subject', 'message')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    actions = ['mark_resolved', 'mark_unresolved']

    fieldsets = (
        ('Contact Info', {
            'fields': ('full_name', 'email', 'category', 'subject', 'created_at')
        }),
        ('Message Content', {
            'fields': ('message',)
        }),
        ('Status & Admin Resolution', {
            'fields': ('is_resolved', 'admin_note')
        }),
    )

    @admin.display(description='Status')
    def status_badge(self, obj):
        if obj.is_resolved:
            return format_html('<span style="background:#10B981;color:#fff;padding:3px 12px;border-radius:20px;font-size:11px;font-weight:700;">RESOLVED</span>')
        return format_html('<span style="background:#F59E0B;color:#fff;padding:3px 12px;border-radius:20px;font-size:11px;font-weight:700;">PENDING</span>')

    @admin.action(description='Mark selected inquiries as Resolved')
    def mark_resolved(self, request, queryset):
        queryset.update(is_resolved=True)
        self.message_user(request, f"{queryset.count()} contact inquiry(ies) marked as resolved.")

    @admin.action(description='Mark selected inquiries as Pending')
    def mark_unresolved(self, request, queryset):
        queryset.update(is_resolved=False)
        self.message_user(request, f"{queryset.count()} contact inquiry(ies) marked as pending.")


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'rating', 'is_active', 'order')
    list_editable = ('is_active', 'order', 'rating')
    list_filter = ('is_active', 'rating')
    search_fields = ('name', 'location', 'review_text')
    ordering = ('order', '-id')


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    list_filter = ('is_active',)
    search_fields = ('question', 'answer')
    ordering = ('order', 'id')


@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    list_filter = ('is_active',)
    search_fields = ('title_line_1', 'title_line_2_highlight', 'description')
    ordering = ('order',)


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('email',)
    ordering = ('-created_at',)


from django import forms


class SiteSettingsAdminForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = '__all__'
        widgets = {
            'paystack_public_key': forms.PasswordInput(render_value=True, attrs={'autocomplete': 'new-password'}),
            'paystack_secret_key': forms.PasswordInput(render_value=True, attrs={'autocomplete': 'new-password'}),
            'flutterwave_public_key': forms.PasswordInput(render_value=True, attrs={'autocomplete': 'new-password'}),
            'flutterwave_secret_key': forms.PasswordInput(render_value=True, attrs={'autocomplete': 'new-password'}),
            'flutterwave_encryption_key': forms.PasswordInput(render_value=True, attrs={'autocomplete': 'new-password'}),
            'openrouter_api_key': forms.PasswordInput(render_value=True, attrs={'autocomplete': 'new-password'}),
            'google_client_secret': forms.PasswordInput(render_value=True, attrs={'autocomplete': 'new-password'}),
        }


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Singleton admin — edit site settings from admin panel."""
    form = SiteSettingsAdminForm

    fieldsets = [
        ('💳 Payment Gateways Configuration & Priority', {
            'fields': (
                'primary_payment_gateway',
                'is_paystack_enabled',
                'paystack_is_live_mode',
                'is_flutterwave_enabled',
                'flutterwave_is_live_mode',
                'transaction_fee_percent',
                'paystack_public_key',
                'paystack_secret_key',
                'flutterwave_api_version',
                'flutterwave_public_key',
                'flutterwave_secret_key',
                'flutterwave_encryption_key',
            ),
            'description': 'Configure Paystack & Flutterwave API keys, toggle active status, and select primary payment gateway. The platform automatically falls back to secondary gateway if primary gateway is disabled or does not support the user currency.',
        }),
        ('🪙 Crypto Payment Gateway (USDT)', {
            'fields': (
                'is_crypto_enabled',
                'crypto_usdt_address',
                'crypto_usdt_network',
                'crypto_instructions',
            ),
            'description': 'Configure Crypto (USDT) receiving wallet address and checkout payment instructions.',
        }),
        ('🌐 Google Social Sign-In (OAuth 2.0)', {
            'fields': ('google_client_id', 'google_client_secret'),
            'description': 'Configure Google Client ID and Secret to enable "Sign in with Google" on the login and registration pages.',
        }),
        ('🤝 Referral & Withdrawal Settings', {
            'fields': (
                'referral_reward_frequency',
                'referral_commission_type',
                'referral_commission_ngn',
                'referral_commission_percentage',
                'min_withdrawal_ngn'
            ),
        }),
        ('💱 Dynamic Pricing', {
            'fields': ('markup_type', 'global_markup_percent', 'global_markup_fixed_usd', 'usd_to_ngn_rate'),
            'description': 'Select active markup strategy (Percentage vs Fixed USD Amount), configure profit margins, and set currency exchange rates for dynamic vendor products.',
        }),
        ('🌟 Homepage Trust Bar', {
            'fields': ('trust_bar_left_text', 'trust_bar_rating_score', 'trust_bar_right_text'),
            'description': 'Customize the text and rating score displayed in the homepage trust bar.',
        }),
        ('📄 Editable Public Pages Content (Legal & Referral)', {
            'fields': ('privacy_policy_content', 'terms_of_service_content', 'refund_policy_content', 'referral_page_content'),
            'description': 'Customize text or HTML content for Privacy Policy, Terms of Service, Refund Policy, and Refer & Earn pages. Leave blank to use default built-in templates.',
        }),
        ('🤖 AI Settings (OpenRouter)', {
            'fields': ('openrouter_api_key', 'openrouter_model'),
            'description': 'Configure OpenRouter API to automatically clean and refine messy vendor product descriptions.',
        }),
        ('📱 Social Media & Support Contacts', {
            'fields': ('facebook_url', 'twitter_url', 'instagram_url', 'linkedin_url', 'youtube_url', 'whatsapp_number'),
            'description': 'Configure social media links and WhatsApp support number shown on the site and footer.',
        }),
        ('🌐 Site Information & Images', {
            'fields': ('site_name', 'site_url', 'support_email', 'site_logo', 'site_favicon', 'about_us_image', 'contact_hero_image'),
            'description': 'Configure site branding, logos, and custom hero images for the About Us and Contact Us pages.',
        }),
        ('💬 Live Chat Widget', {
            'fields': ('livechat_enabled', 'livechat_show_on_dashboard', 'livechat_script'),
            'description': (
                '🟢 Toggle the widget on/off with "Enable Live Chat Widget". '
                '📋 Paste your full &lt;script&gt; tag in the "Live Chat Widget Script" field. '
                '🗑️ Clear the script field entirely to permanently remove the widget. '
                '📱 Use "Show on Dashboard Pages" to control whether the widget appears inside the user dashboard too.'
            ),
        }),
    ]

    def has_add_permission(self, request):
        # Only allow one row
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Auto-redirect to the edit page of the singleton
        obj, _ = SiteSettings.objects.get_or_create(pk=1)
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        return HttpResponseRedirect(
            reverse('admin:core_sitesettings_change', args=[obj.pk])
        )
