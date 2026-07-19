from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Order, OrderItem, PaymentTransaction


# ─────────────────────────────────────────────
#  Inline: OrderItems inside Order
# ─────────────────────────────────────────────
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('tool', 'price_ngn')
    can_delete = False


# ─────────────────────────────────────────────
#  Inline: PaymentTransaction inside Order
# ─────────────────────────────────────────────
class PaymentTransactionInline(admin.StackedInline):
    model = PaymentTransaction
    extra = 0
    readonly_fields = ('gateway', 'transaction_id', 'reference', 'status',
                       'amount_paid', 'currency_paid', 'created_at', 'updated_at')
    can_delete = False


# ─────────────────────────────────────────────
#  Order Admin
# ─────────────────────────────────────────────
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user_email', 'status_badge', 'total_amount_ngn',
        'local_currency', 'delivery_status', 'created_at'
    )
    list_filter = ('status', 'delivery_status', 'local_currency', 'created_at')
    search_fields = ('user__email', 'delivery_email', 'id')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'user', 'total_amount_ngn',
                       'local_amount', 'exchange_rate', 'local_currency')
    inlines = [OrderItemInline, PaymentTransactionInline]
    actions = ['mark_delivery_sent', 'mark_delivery_failed']

    fieldsets = (
        ('Order Info', {
            'fields': ('user', 'status', 'total_amount_ngn', 'local_currency', 'local_amount', 'exchange_rate')
        }),
        ('Delivery', {
            'fields': ('delivery_email', 'delivery_status', 'delivery_notes')
        }),
        ('Referral', {
            'fields': ('referred_by',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='User')
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'paid': '#10B981',
            'pending': '#F59E0B',
            'failed': '#EF4444',
            'refunded': '#6366F1',
            'cancelled': '#9CA3AF',
        }
        color = colors.get(obj.status, '#9CA3AF')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;border-radius:20px;'
            'font-size:11px;font-weight:600;">{}</span>',
            color, obj.status.upper()
        )

    @admin.action(description='Mark delivery as Sent')
    def mark_delivery_sent(self, request, queryset):
        queryset.update(delivery_status='sent')
        self.message_user(request, f"{queryset.count()} orders marked as delivered.")

    @admin.action(description='Mark delivery as Failed')
    def mark_delivery_failed(self, request, queryset):
        queryset.update(delivery_status='failed')
        self.message_user(request, f"{queryset.count()} orders marked delivery failed.")


# ─────────────────────────────────────────────
#  PaymentTransaction Admin
# ─────────────────────────────────────────────
@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'transaction_id', 'order_link', 'gateway', 'status',
        'amount_paid', 'currency_paid', 'created_at'
    )
    list_filter = ('gateway', 'status', 'currency_paid', 'created_at')
    search_fields = ('transaction_id', 'reference', 'order__user__email')
    readonly_fields = ('transaction_id', 'reference', 'gateway', 'order',
                       'amount_paid', 'currency_paid', 'gateway_response',
                       'created_at', 'updated_at')
    ordering = ('-created_at',)

    @admin.display(description='Order')
    def order_link(self, obj):
        url = f"/admin/orders/order/{obj.order.id}/change/"
        return format_html('<a href="{}">Order #{}</a>', url, obj.order.id)


# ─────────────────────────────────────────────
#  RefundRequest Admin
# ─────────────────────────────────────────────
from .models import RefundRequest

@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    list_display = ('order', 'user_email', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order__id', 'order__user__email', 'reason')
    readonly_fields = ('created_at', 'processed_at')
    actions = ['approve_refunds', 'reject_refunds']

    @admin.display(description='User')
    def user_email(self, obj):
        return obj.order.user.email

    @admin.action(description='✅ Approve selected refunds')
    def approve_refunds(self, request, queryset):
        from django.utils import timezone
        updated = 0
        for rr in queryset.filter(status='pending'):
            rr.status = 'approved'
            rr.processed_at = timezone.now()
            rr.save()
            
            # Update order status
            rr.order.status = 'refunded'
            rr.order.save(update_fields=['status'])
            updated += 1
            
        self.message_user(request, f"{updated} refund(s) approved and orders marked as refunded.")

    @admin.action(description='❌ Reject selected refunds')
    def reject_refunds(self, request, queryset):
        from django.utils import timezone
        count = queryset.filter(status='pending').update(
            status='rejected',
            processed_at=timezone.now()
        )
        self.message_user(request, f"{count} refund(s) rejected.")
