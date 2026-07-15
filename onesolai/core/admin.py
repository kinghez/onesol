from django.contrib import admin

# ─────────────────────────────────────────────
# Admin site branding
# ─────────────────────────────────────────────
admin.site.site_header = "OneSol AI Hub – Admin"
admin.site.site_title = "OneSol Admin"
admin.site.index_title = "Site Management Dashboard"

from .models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Singleton admin — edit site settings from admin panel."""

    fieldsets = [
        ('💳 Paystack Payment Gateway', {
            'fields': ('paystack_public_key', 'paystack_secret_key', 'is_live_mode', 'transaction_fee_percent'),
            'description': 'Configure your Paystack API keys. Toggle Live Mode ON only when ready for real payments.',
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
        ('🌐 Site Information', {
            'fields': ('site_name', 'site_url', 'support_email'),
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
