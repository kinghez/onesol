from django.contrib import admin
from django.utils.html import format_html
from .models import ActivityLog, VendorBalanceSnapshot


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('title', 'action_badge', 'user_link', 'severity_badge', 'ip_address', 'timestamp')
    list_filter = ('severity', 'action_type', 'timestamp')
    search_fields = ('title', 'details', 'user__email', 'user__username', 'ip_address')
    readonly_fields = ('user', 'action_type', 'severity', 'title', 'details', 'ip_address', 'timestamp')
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        # Keep logs immutable for audit safety
        return request.user.is_superuser

    @admin.display(description='User')
    def user_link(self, obj):
        if obj.user:
            return format_html('<a href="/admin/accounts/user/{}/change/" style="font-weight:600; color:#8E6CFF;">{}</a>', obj.user.id, obj.user.email)
        import re
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', f"{obj.title} {obj.details}")
        if emails:
            return format_html('<span style="color:#60A5FA; font-weight:500;">{}</span>', emails[0])
        return format_html('<span style="color:#888;">System / Guest</span>')

    @admin.display(description='Action')
    def action_badge(self, obj):
        colors = {
            'user_signup': '#10B981',
            'user_login': '#3B82F6',
            'user_logout': '#6B7280',
            'user_deleted': '#EF4444',
            'order_created': '#3B82F6',
            'order_paid': '#10B981',
            'order_failed': '#EF4444',
            'order_fulfilled': '#10B981',
            'payment_sent': '#F59E0B',
            'payment_success': '#10B981',
            'payment_failed': '#EF4444',
            'wallet_topup': '#8B5CF6',
            'wallet_purchase': '#3B82F6',
            'withdrawal_requested': '#F59E0B',
            'withdrawal_approved': '#10B981',
            'withdrawal_rejected': '#EF4444',
            'refund_requested': '#F59E0B',
            'refund_approved': '#10B981',
            'refund_rejected': '#EF4444',
            'product_created': '#10B981',
            'product_updated': '#3B82F6',
            'product_deleted': '#EF4444',
        }
        bg = colors.get(obj.action_type, '#4B5563')
        return format_html(
            '<span style="background: {}; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 11px;">{}</span>',
            bg,
            obj.get_action_type_display()
        )

    @admin.display(description='Severity')
    def severity_badge(self, obj):
        colors = {
            'success': '#10B981',
            'error': '#EF4444',
            'warning': '#F59E0B',
            'info': '#3B82F6',
        }
        color = colors.get(obj.severity, '#3B82F6')
        return format_html(
            '<span style="background: {}; color: #fff; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 10px; text-transform: uppercase;">{}</span>',
            color,
            obj.severity
        )


@admin.register(VendorBalanceSnapshot)
class VendorBalanceSnapshotAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'balance', 'timestamp')
    list_filter = ('vendor', 'timestamp')
    readonly_fields = ('vendor', 'balance', 'timestamp')
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

