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


from core.admin_utils import export_as_csv

# ─────────────────────────────────────────────
#  Order Admin
# ─────────────────────────────────────────────
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        if change and 'status' in form.changed_data:
            old_obj = Order.objects.get(pk=obj.pk)
            if old_obj.status != 'paid' and obj.status == 'paid':
                from orders.delivery import trigger_delivery, credit_referral_commission
                trigger_delivery(obj)
                credit_referral_commission(obj)
                try:
                    from vendors.tasks import fulfill_order_via_vendors
                    fulfill_order_via_vendors(obj.id)
                except Exception as ve:
                    print(f"Vendor fulfillment error on order save: {ve}")

                if obj.user:
                    try:
                        from notifications.models import Notification
                        Notification.objects.create(
                            user=obj.user,
                            title="🎉 Order Payment Approved!",
                            message=f"Your payment for Order #{obj.order_number} has been approved and your access details are ready!",
                            notification_type='order',
                            action_url='/dashboard/orders/'
                        )
                    except Exception:
                        pass
        super().save_model(request, obj, form, change)
    list_display = (
        'order_tracking_id', 'user_email', 'status_badge', 'total_amount_ngn',
        'local_currency', 'delivery_status', 'vendor_order_id', 'created_at'
    )
    list_display_links = ('user_email',)
    list_filter = ('status', 'delivery_status', 'local_currency', 'created_at')
    search_fields = ('user__email', 'delivery_email', 'id', 'paystack_reference', 'vendor_order_id')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'user', 'total_amount_ngn',
                       'local_amount', 'exchange_rate', 'local_currency')
    inlines = [OrderItemInline, PaymentTransactionInline]
    actions = ['mark_delivery_sent', 'mark_delivery_failed', 'mark_as_paid', 'mark_as_failed', export_as_csv]

    fieldsets = (
        ('Order Info', {
            'fields': ('user', 'status', 'total_amount_ngn', 'local_currency', 'local_amount', 'exchange_rate', 'vendor_order_id')
        }),
        ('Delivery', {
            'fields': ('delivery_email', 'delivery_status', 'delivery_notes', 'access_details')
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

    @admin.display(description='Order ID', ordering='id')
    def order_tracking_id(self, obj):
        return f"#{obj.order_number}"

    @admin.display(description='User')
    def user_email(self, obj):
        if obj.user:
            return obj.user.email
        return obj.delivery_email or "Unregistered User" 

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

    @admin.action(description='✅ Mark selected orders as PAID')
    def mark_as_paid(self, request, queryset):
        from orders.delivery import trigger_delivery, credit_referral_commission
        count = 0
        for order in queryset:
            if order.status != 'paid':
                order.status = 'paid'
                order.save(update_fields=['status'])
                trigger_delivery(order)
                credit_referral_commission(order)
                try:
                    from vendors.tasks import fulfill_order_via_vendors
                    fulfill_order_via_vendors(order.id)
                except Exception:
                    pass
                count += 1
        self.message_user(request, f"{count} order(s) marked as PAID and fulfillment triggered.")

    @admin.action(description='❌ Mark selected orders as FAILED (Abandoned)')
    def mark_as_failed(self, request, queryset):
        count = queryset.update(status='failed')
        self.message_user(request, f"{count} order(s) marked as FAILED.")

    @admin.action(description='🔄 Re-trigger Vendor API Purchase Fulfillment')
    def retry_vendor_fulfillment(self, request, queryset):
        from vendors.tasks import _fulfill_order_logic
        count = 0
        for order in queryset:
            if order.status == 'paid':
                _fulfill_order_logic(order.id)
                count += 1
        self.message_user(request, f"Re-triggered vendor purchase for {count} paid order(s). Check API Logs / Access Details for updates.")

    @admin.action(description='↩️ Refund Selected Orders to User Wallet')
    def refund_orders_to_wallet(self, request, queryset):
        from accounts.models import WalletTransaction
        from notifications.models import Notification
        from analytics.models import ActivityLog
        refunded_count = 0
        for order in queryset:
            if order.status in ['paid', 'pending', 'failed']:
                user = order.user
                amount = order.total_amount_ngn
                profile = user.profile
                profile.wallet_balance += amount
                profile.save(update_fields=['wallet_balance'])

                order.status = 'refunded'
                order.save(update_fields=['status'])

                WalletTransaction.objects.create(
                    user=user,
                    transaction_type='refund',
                    amount_ngn=amount,
                    status='success',
                    reference=f"REFUND_{order.order_number}",
                    description=f"Wallet Refund for Order #{order.order_number}"
                )

                ActivityLog.log(
                    action_type='order_refunded',
                    title=f"Order #{order.order_number} Refunded to Wallet",
                    details=f"Amount: NGN {amount:,.2f} | User: {user.email} | Admin: {request.user.email}",
                    user=user,
                    performed_by=request.user,
                    severity='info'
                )

                Notification.objects.create(
                    user=user,
                    title="↩️ Order Refunded to Wallet",
                    message=f"Order #{order.order_number} has been refunded. NGN {amount:,.2f} has been added back to your wallet.",
                    notification_type='order',
                    action_url="/dashboard/wallet/"
                )
                refunded_count += 1
        self.message_user(request, f"{refunded_count} order(s) refunded to user wallet balance.")


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
    actions = [export_as_csv]
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
    actions = ['approve_refunds', 'reject_refunds', export_as_csv]

    @admin.display(description='User')
    def user_email(self, obj):
        return obj.order.user.email

    @admin.action(description='✅ Approve selected refunds & credit user wallet')
    def approve_refunds(self, request, queryset):
        from django.utils import timezone
        from accounts.models import WalletTransaction
        from notifications.models import Notification
        from analytics.models import ActivityLog
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


# ─────────────────────────────────────────────
#  OrderAPIRequest Admin (Vendor API Logs)
# ─────────────────────────────────────────────
from .models import OrderAPIRequest

@admin.register(OrderAPIRequest)
class OrderAPIRequestAdmin(admin.ModelAdmin):
    list_display = ('order_link', 'vendor', 'vendor_product', 'status_badge', 'vendor_order_id', 'error_message', 'created_at')
    list_filter = ('vendor', 'status', 'created_at')
    search_fields = ('order__id', 'vendor__name', 'vendor_order_id', 'error_message')
    readonly_fields = ('order', 'vendor', 'vendor_product', 'status', 'vendor_order_id', 'request_data', 'response_data', 'error_message', 'created_at')
    actions = ['retry_vendor_fulfillment_from_log', export_as_csv]
    ordering = ('-created_at',)

    @admin.display(description='Order')
    def order_link(self, obj):
        url = f"/admin/orders/order/{obj.order.id}/change/"
        return format_html('<a href="{}">Order #{}</a>', url, obj.order.id)

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'completed': '#10B981',
            'success': '#10B981',
            'pending_manual': '#F59E0B',
            'pending': '#3B82F6',
            'failed': '#EF4444',
        }
        color = colors.get(obj.status, '#6B7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;">{}</span>',
            color, obj.status.upper()
        )



# ─────────────────────────────────────────────
#  Manual Bank Account & Payment Proof Admin
# ─────────────────────────────────────────────
from .models import ManualBankAccount, ManualPaymentProof

@admin.register(ManualBankAccount)
class ManualBankAccountAdmin(admin.ModelAdmin):
    list_display = ('payment_method_name', 'account_number', 'account_name', 'supported_regions', 'currency_code', 'is_active', 'display_order')
    list_filter = ('payment_method_name', 'currency_code', 'is_active')
    search_fields = ('payment_method_name', 'account_number', 'account_name', 'supported_regions')
    list_editable = ('is_active', 'display_order')
    fields = ('payment_method_name', 'account_number', 'account_name', 'supported_regions', 'currency_code', 'additional_instructions', 'is_active', 'display_order')


@admin.register(ManualPaymentProof)
class ManualPaymentProofAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_email', 'target_reference', 'payment_channel_used', 'sender_name_or_txid', 'amount_display', 'status_badge', 'proof_link', 'created_at')
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('user__email', 'sender_name_or_txid', 'order__id', 'wallet_transaction__reference')
    readonly_fields = ('order', 'wallet_transaction', 'user', 'payment_channel_used', 'sender_name_or_txid', 'proof_file_preview', 'amount_local', 'currency', 'amount_ngn', 'created_at', 'processed_at')
    actions = ['approve_manual_payments', 'reject_manual_payments']

    @admin.display(description='User')
    def user_email(self, obj):
        return obj.user.email if obj.user else "N/A"

    @admin.display(description='Target')
    def target_reference(self, obj):
        if obj.order:
            url = f"/admin/orders/order/{obj.order.id}/change/"
            return format_html('<a href="{}">Order #{}</a>', url, obj.order.order_number)
        elif obj.wallet_transaction:
            return f"Wallet ({obj.wallet_transaction.reference})"
        return "N/A"

    @admin.display(description='Amount')
    def amount_display(self, obj):
        return f"{obj.currency} {obj.amount_local:,.2f} (₦{obj.amount_ngn:,.2f})"

    @admin.display(description='Proof File')
    def proof_link(self, obj):
        if obj.proof_file:
            return format_html('<a href="{}" target="_blank" style="background:#4F46E5;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;">View Proof</a>', obj.proof_file.url)
        return "No File"

    @admin.display(description='Proof Preview')
    def proof_file_preview(self, obj):
        if obj.proof_file:
            url = obj.proof_file.url
            if url.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                return format_html('<a href="{}" target="_blank"><img src="{}" style="max-width:400px;max-height:400px;border-radius:8px;border:1px solid #333;" /></a>', url, url)
            return format_html('<a href="{}" target="_blank" style="font-weight:bold;color:#6366F1;">Download Proof Document ({})</a>', url, url.split('.')[-1].upper())
        return "No File Uploaded"

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {'approved': '#10B981', 'pending': '#F59E0B', 'rejected': '#EF4444'}
        return format_html('<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;">{}</span>', colors.get(obj.status, '#6B7280'), obj.status.upper())

    @admin.action(description='✅ Approve selected manual payments')
    def approve_manual_payments(self, request, queryset):
        from django.utils import timezone
        from orders.delivery import trigger_delivery, credit_referral_commission
        from notifications.models import Notification
        from analytics.models import ActivityLog

        approved_count = 0
        for proof in queryset.filter(status='pending'):
            proof.status = 'approved'
            proof.processed_at = timezone.now()
            proof.save()

            if proof.order:
                order = proof.order
                order.status = 'paid'
                order.save(update_fields=['status'])

                trigger_delivery(order)
                credit_referral_commission(order)

                try:
                    from vendors.tasks import fulfill_order_via_vendors
                    fulfill_order_via_vendors(order.id)
                except Exception as ve:
                    print(f"Vendor fulfillment error on manual approval: {ve}")

                ActivityLog.log(
                    action_type='payment_success',
                    title=f"Manual Payment Approved: Order #{order.order_number}",
                    details=f"Amount: {proof.currency} {proof.amount_local:,.2f} | Sender: {proof.sender_name_or_txid} | Admin: {request.user.email}",
                    user=order.user,
                    performed_by=request.user,
                    severity='success'
                )

                if order.user:
                    Notification.objects.create(
                        user=order.user,
                        title="✅ Payment Approved!",
                        message=f"Your manual payment for Order #{order.order_number} has been verified and approved!",
                        notification_type='order',
                        action_url="/dashboard/orders/"
                    )

            elif proof.wallet_transaction:
                w_tx = proof.wallet_transaction
                w_tx.status = 'success'
                w_tx.save(update_fields=['status'])

                user = proof.user
                profile = user.profile
                profile.wallet_balance += proof.amount_ngn
                profile.save(update_fields=['wallet_balance'])

                ActivityLog.log(
                    action_type='wallet_funded',
                    title=f"Manual Wallet Top-up Approved for {user.email}",
                    details=f"Amount Credited: NGN {proof.amount_ngn:,.2f} ({proof.currency} {proof.amount_local:,.2f}) | Admin: {request.user.email}",
                    user=user,
                    performed_by=request.user,
                    severity='success'
                )

                Notification.objects.create(
                    user=user,
                    title="💰 Wallet Top-Up Approved!",
                    message=f"Your manual top-up of {proof.currency} {proof.amount_local:,.2f} (₦{proof.amount_ngn:,.2f}) has been verified and credited to your wallet balance!",
                    notification_type='wallet',
                    action_url="/dashboard/wallet/"
                )

            approved_count += 1

        self.message_user(request, f"Successfully approved {approved_count} manual payment proof(s).")

    @admin.action(description='❌ Reject selected manual payments')
    def reject_manual_payments(self, request, queryset):
        from django.utils import timezone
        from notifications.models import Notification

        rejected_count = 0
        for proof in queryset.filter(status='pending'):
            proof.status = 'rejected'
            proof.processed_at = timezone.now()
            proof.save()

            if proof.order:
                proof.order.status = 'failed'
                proof.order.save(update_fields=['status'])

            if proof.wallet_transaction:
                proof.wallet_transaction.status = 'failed'
                proof.wallet_transaction.save(update_fields=['status'])

            Notification.objects.create(
                user=proof.user,
                title="❌ Manual Payment Unverified",
                message=f"We could not verify your manual payment proof for {proof.currency} {proof.amount_local:,.2f}. Please contact support or try again.",
                notification_type='order',
                action_url="/dashboard/"
            )
            rejected_count += 1

        self.message_user(request, f"Marked {rejected_count} manual payment proof(s) as REJECTED.")
