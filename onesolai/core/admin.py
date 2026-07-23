from django.contrib import admin

# ─────────────────────────────────────────────
# Admin site branding
# ─────────────────────────────────────────────
admin.site.site_header = "OneSol AI Hub – Admin"
admin.site.site_title = "OneSol Admin"
admin.site.index_title = "Site Management Dashboard"

from .models import SiteSettings, HeroSlide, NewsletterSubscriber


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


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Singleton admin — edit site settings from admin panel."""

    fieldsets = [
        ('💳 Payment Gateways Configuration & Priority', {
            'fields': (
                'primary_payment_gateway',
                'is_paystack_enabled',
                'is_flutterwave_enabled',
                'is_live_mode',
                'transaction_fee_percent',
                'paystack_public_key',
                'paystack_secret_key',
                'flutterwave_public_key',
                'flutterwave_secret_key',
                'flutterwave_encryption_key',
            ),
            'description': 'Configure Paystack & Flutterwave API keys, toggle active status, and select primary payment gateway. The platform automatically falls back to secondary gateway if primary gateway is disabled or does not support the user currency.',
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
            'fields': ('global_markup_percent', 'global_markup_fixed_usd', 'usd_to_ngn_rate'),
            'description': 'Configure profit margins and currency conversion for dynamic Vendor products.',
        }),
        ('📄 Editable Legal Pages Content', {
            'fields': ('privacy_policy_content', 'terms_of_service_content', 'refund_policy_content'),
            'description': 'Customize text or HTML content for Privacy Policy, Terms of Service, and Refund Policy pages. Leave blank to use default built-in legal templates.',
        }),
        ('🤖 AI Settings (OpenRouter)', {
            'fields': ('openrouter_api_key', 'openrouter_model'),
            'description': 'Configure OpenRouter API to automatically clean and refine messy vendor product descriptions.',
        }),
        ('📱 Social Media & Support Contacts', {
            'fields': ('facebook_url', 'twitter_url', 'instagram_url', 'linkedin_url', 'youtube_url', 'whatsapp_number'),
            'description': 'Configure social media links and WhatsApp support number shown on the site and footer.',
        }),
        ('🌐 Site Information', {
            'fields': ('site_name', 'site_url', 'support_email', 'site_logo', 'site_favicon'),
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
