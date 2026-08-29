from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils import timezone
from .models import User, Profile, Referral, WithdrawalRequest, WalletTransaction, APIKey, DeveloperWebhook
from core.admin_utils import export_as_csv


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
    actions = [export_as_csv]
    list_display = (
        'email', 'full_name', 'username', 'is_active', 'is_staff',
        'wallet_balance', 'referral_earnings', 'referrals_count', 'date_joined'
    )
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('-date_joined',)

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
    list_display = ('user', 'referral_code', 'earnings', 'wallet_balance_display', 'referrals_count', 'country_preference')

    @admin.display(description='Wallet Balance')
    def wallet_balance_display(self, obj):
        curr = obj.currency_preference or 'NGN'
        from core.templatetags.currency_tags import convert_ngn
        converted = convert_ngn(obj.wallet_balance, curr)
        if curr != 'NGN':
            return format_html('<strong>{}</strong><br><small style="color:#6c757d;">(Base ₦{:,.2f} NGN)</small>', converted, obj.wallet_balance)
        return format_html('<strong>{}</strong>', converted)
    search_fields = ('user__email', 'referral_code')
    list_filter = ('currency_preference', 'country_preference')
    readonly_fields = ('referral_code', 'referral_link_display')
    actions = [export_as_csv]

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
    actions = ['mark_rewarded', export_as_csv]

    @admin.action(description='Mark selected referrals as Rewarded')
    def mark_rewarded(self, request, queryset):
        for referral in queryset.filter(status='successful'):
            referral.status = 'rewarded'
            referral.save()
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
@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount_ngn', 'method_badge', 'payout_details_display', 'status', 'created_at')
    list_filter = ('withdrawal_method', 'status', 'created_at')
    search_fields = ('user__email', 'account_number', 'account_name', 'bank_name', 'crypto_wallet_address')
    readonly_fields = ('created_at', 'processed_at')
    actions = ['approve_withdrawals', 'reject_withdrawals', export_as_csv]

    @admin.display(description='Method')
    def method_badge(self, obj):
        if obj.withdrawal_method == 'crypto':
            return format_html('<span style="background:#5B63F6;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;">🪙 CRYPTO</span>')
        return format_html('<span style="background:#28a745;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;">🏦 BANK</span>')

    @admin.display(description='Payout Destination')
    def payout_details_display(self, obj):
        if obj.withdrawal_method == 'crypto':
            return format_html('<strong>{}</strong><br><small style="color:#6c757d;">{}</small>', obj.crypto_network, obj.crypto_wallet_address)
        return format_html('<strong>{}</strong> ({})<br><small style="color:#6c757d;">{}</small>', obj.bank_name, obj.account_number, obj.account_name)

    @admin.display(description='Amount (NGN)')
    def amount_ngn(self, obj):
        return f'NGN {obj.amount:,.2f}'

    @admin.action(description='✅ Approve selected withdrawals (deduct balance)')
    def approve_withdrawals(self, request, queryset):
        from analytics.models import ActivityLog
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
                    ActivityLog.log(
                        action_type='withdrawal_approved',
                        title=f"Withdrawal Approved for {wr.user.email} (NGN {wr.amount:,.2f})",
                        details=f"Bank: {wr.bank_name} | Acc: {wr.account_number} ({wr.account_name})",
                        user=wr.user,
                        severity='success'
                    )
            except Exception:
                pass
        self.message_user(request, f'{updated} withdrawal(s) approved and balances deducted.')

    @admin.action(description='❌ Reject selected withdrawals')
    def reject_withdrawals(self, request, queryset):
        from analytics.models import ActivityLog
        for wr in queryset.filter(status='pending'):
            wr.status = 'rejected'
            wr.processed_at = timezone.now()
            wr.save()
            ActivityLog.log(
                action_type='withdrawal_rejected',
                title=f"Withdrawal Rejected for {wr.user.email} (NGN {wr.amount:,.2f})",
                details=f"Bank: {wr.bank_name} | Acc: {wr.account_number}",
                user=wr.user,
                severity='warning'
            )
        self.message_user(request, f'Selected withdrawal(s) rejected.')


# ─────────────────────────────────────────────
#  Wallet Transaction Admin
# ─────────────────────────────────────────────
@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'type_badge', 'amount_ngn_display', 'status_badge', 'reference', 'description', 'created_at')

    def save_model(self, request, obj, form, change):
        if change and 'status' in form.changed_data:
            old_obj = WalletTransaction.objects.get(pk=obj.pk)
            if old_obj.status != 'success' and obj.status == 'success' and obj.transaction_type == 'deposit':
                profile = obj.user.profile
                profile.wallet_balance += obj.amount_ngn
                profile.save(update_fields=['wallet_balance'])

                try:
                    from notifications.models import Notification
                    Notification.objects.create(
                        user=obj.user,
                        title="💰 Wallet Top-Up Approved",
                        message=f"Your deposit of NGN {obj.amount_ngn:,.2f} (Ref: {obj.reference}) has been approved and added to your wallet.",
                        notification_type='wallet',
                        action_url='/dashboard/wallet/'
                    )
                except Exception:
                    pass

                try:
                    from analytics.models import ActivityLog
                    ActivityLog.log(
                        action_type='wallet_funded',
                        title=f"Wallet Top-Up Approved ({obj.reference})",
                        details=f"Admin {request.user.email} marked transaction as success. Credited NGN {obj.amount_ngn:,.2f} to {obj.user.email}",
                        user=obj.user,
                        performed_by=request.user,
                        severity='success'
                    )
                except Exception:
                    pass
        super().save_model(request, obj, form, change)
    list_filter = ('transaction_type', 'status', 'created_at')
    search_fields = ('user__email', 'reference', 'description')
    readonly_fields = ('created_at',)
    actions = [export_as_csv, 'approve_crypto_topup', 'reject_crypto_topup']
    ordering = ('-created_at',)

    @admin.action(description='✅ Approve Selected Crypto Top-ups')
    def approve_crypto_topup(self, request, queryset):
        approved_count = 0
        for tx in queryset.filter(status='pending'):
            profile = tx.user.profile
            profile.wallet_balance += tx.amount_ngn
            profile.save(update_fields=['wallet_balance'])

            tx.status = 'success'
            tx.save(update_fields=['status'])

            try:
                from notifications.models import Notification
                Notification.objects.create(
                    user=tx.user,
                    title="Crypto Top-up Approved",
                    message=f"Your crypto deposit of NGN {tx.amount_ngn:,.2f} has been verified and added to your wallet.",
                    notification_type='system',
                    action_url='/dashboard/wallet/'
                )
            except Exception:
                pass

            try:
                from analytics.models import ActivityLog
                ActivityLog.log(
                    action_type='wallet_topup',
                    title=f"Crypto Top-up Approved ({tx.reference})",
                    details=f"Admin {request.user.email} approved crypto top-up of NGN {tx.amount_ngn} for {tx.user.email}",
                    user=tx.user,
                    performed_by=request.user,
                    severity='success'
                )
            except Exception:
                pass

            approved_count += 1
        self.message_user(request, f"Successfully approved {approved_count} crypto top-up transaction(s) and credited user wallet(s).")

    @admin.action(description='❌ Reject Selected Crypto Top-ups')
    def reject_crypto_topup(self, request, queryset):
        rejected_count = 0
        for tx in queryset.filter(status='pending'):
            tx.status = 'failed'
            tx.save(update_fields=['status'])

            try:
                from notifications.models import Notification
                Notification.objects.create(
                    user=tx.user,
                    title="Crypto Top-up Rejected",
                    message=f"Your crypto deposit of NGN {tx.amount_ngn:,.2f} (Ref: {tx.reference}) could not be verified.",
                    notification_type='system',
                    action_url='/dashboard/wallet/'
                )
            except Exception:
                pass

            try:
                from analytics.models import ActivityLog
                ActivityLog.log(
                    action_type='payment_failed',
                    title=f"Crypto Top-up Rejected ({tx.reference})",
                    details=f"Admin {request.user.email} rejected crypto top-up of NGN {tx.amount_ngn} for {tx.user.email}",
                    user=tx.user,
                    performed_by=request.user,
                    severity='warning'
                )
            except Exception:
                pass

            rejected_count += 1
        self.message_user(request, f"Rejected {rejected_count} crypto top-up transaction(s).")

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'success': '#10B981',
            'pending': '#F59E0B',
            'failed': '#EF4444',
        }
        color = colors.get(obj.status, '#6B7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;">{}</span>',
            color, obj.get_status_display().upper()
        )

    @admin.display(description='Type')
    def type_badge(self, obj):
        colors = {
            'deposit': '#10B981',
            'purchase': '#3B82F6',
            'withdrawal': '#EF4444',
            'referral_credit': '#8B5CF6',
        }
        color = colors.get(obj.transaction_type, '#6B7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;">{}</span>',
            color, obj.get_transaction_type_display().upper()
        )

    @admin.display(description='Amount (NGN)')
    def amount_ngn_display(self, obj):
        return f"NGN {obj.amount_ngn:,.2f}"


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'public_key', 'is_active', 'created_at', 'last_used_at')
    search_fields = ('user__email', 'name', 'public_key', 'secret_key')
    list_filter = ('is_active', 'created_at')


@admin.register(DeveloperWebhook)
class DeveloperWebhookAdmin(admin.ModelAdmin):
    list_display = ('user', 'webhook_url', 'is_active', 'created_at')
    search_fields = ('user__email', 'webhook_url')
    list_filter = ('is_active', 'created_at')

