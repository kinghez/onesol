from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Profile, Referral


# ─────────────────────────────────────────────
#  Profile Inline inside User
# ─────────────────────────────────────────────
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = (
        'referral_code', 'earnings', 'wallet_balance',
        'country_preference', 'currency_preference', 'avatar_url'
    )
    readonly_fields = ('referral_code',)


# ─────────────────────────────────────────────
#  User Admin
# ─────────────────────────────────────────────
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = (
        'email', 'full_name', 'username', 'is_active', 'is_staff',
        'wallet_balance', 'referral_earnings', 'referrals_count', 'date_joined'
    )
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('-date_joined',)

    # Override fieldsets to show email prominently
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',),
        }),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )

    @admin.display(description='Name')
    def full_name(self, obj):
        return obj.get_full_name() or '—'

    @admin.display(description='Wallet')
    def wallet_balance(self, obj):
        try:
            return f"NGN {obj.profile.wallet_balance:,.2f}"
        except Profile.DoesNotExist:
            return '—'

    @admin.display(description='Referral Earnings')
    def referral_earnings(self, obj):
        try:
            return f"NGN {obj.profile.earnings:,.2f}"
        except Profile.DoesNotExist:
            return '—'

    @admin.display(description='Referrals')
    def referrals_count(self, obj):
        return obj.referrals_made.count()


# ─────────────────────────────────────────────
#  Profile Admin
# ─────────────────────────────────────────────
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'referral_code', 'earnings', 'wallet_balance', 'referrals_count', 'country_preference')
    search_fields = ('user__email', 'referral_code')
    list_filter = ('currency_preference', 'country_preference')
    readonly_fields = ('referral_code', 'referral_link_display')

    @admin.display(description='Referrals Made')
    def referrals_count(self, obj):
        return obj.user.referrals_made.count()

    @admin.display(description='Referral Link')
    def referral_link_display(self, obj):
        link = obj.referral_link
        return format_html('<a href="{}" target="_blank">{}</a>', link, link)


# ─────────────────────────────────────────────
#  Referral Admin
# ─────────────────────────────────────────────
@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('referrer', 'referred_user', 'status', 'reward_amount_ngn', 'date_referred')
    list_filter = ('status',)
    search_fields = ('referrer__email', 'referred_user__email')
    list_editable = ('status',)
    ordering = ('-date_referred',)
    actions = ['mark_rewarded']

    @admin.action(description='Mark selected referrals as Rewarded')
    def mark_rewarded(self, request, queryset):
        for referral in queryset.filter(status='successful'):
            referral.status = 'rewarded'
            referral.save()
            # Credit the referrer's earnings
            try:
                profile = referral.referrer.profile
                profile.earnings += referral.reward_amount_ngn
                profile.save()
            except Exception:
                pass
        self.message_user(request, "Selected referrals marked as rewarded and earnings credited.")


# ─────────────────────────────────────────────
#  Withdrawal Request Admin
# ─────────────────────────────────────────────
from .models import WithdrawalRequest
from django.utils import timezone


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount_ngn', 'bank_name', 'account_number', 'account_name', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'account_number', 'account_name', 'bank_name')
    readonly_fields = ('created_at', 'processed_at')
    actions = ['approve_withdrawals', 'reject_withdrawals']

    @admin.display(description='Amount (NGN)')
    def amount_ngn(self, obj):
        return f'NGN {obj.amount:,.2f}'

    @admin.action(description='✅ Approve selected withdrawals (deduct balance)')
    def approve_withdrawals(self, request, queryset):
        from accounts.models import Profile
        updated = 0
        for wr in queryset.filter(status='pending'):
            try:
                profile = wr.user.profile
                if profile.earnings >= wr.amount:
                    profile.earnings -= wr.amount
                    profile.save(update_fields=['earnings'])
                    wr.status = 'approved'
                    wr.processed_at = timezone.now()
                    wr.save()
                    updated += 1
            except Exception:
                pass
        self.message_user(request, f'{updated} withdrawal(s) approved and balances deducted.')

    @admin.action(description='❌ Reject selected withdrawals')
    def reject_withdrawals(self, request, queryset):
        count = queryset.filter(status='pending').update(
            status='rejected',
            processed_at=timezone.now()
        )
        self.message_user(request, f'{count} withdrawal(s) rejected.')

