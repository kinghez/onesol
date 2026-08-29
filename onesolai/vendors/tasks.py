import threading
import logging

logger = logging.getLogger(__name__)

def _fulfill_order_logic(order_id):
    """
    Core vendor order fulfillment logic.
    Sends purchase request to third-party vendor API (Akunding, ShopBot, Canboso),
    saves vendor credentials/codes to order.access_details, updates delivery status,
    and logs activity log.
    """
    try:
        from orders.models import Order, OrderAPIRequest
        from vendors.services import get_vendor_service
        from analytics.models import ActivityLog
        from orders.delivery import trigger_delivery

        order = Order.objects.prefetch_related('items__tool__vendor_product__vendor').filter(id=order_id).first()
        if not order:
            logger.error(f"Order #{order_id} not found for vendor fulfillment.")
            return

        if order.status != 'paid':
            logger.warning(f"Order #{order.id} is not paid (status: {order.status}). Skipping vendor fulfillment.")
            return

        delivered_codes = []
        is_manual_delivery_needed = False

        for item in order.items.all():
            tool = item.tool
            if not tool or not tool.vendor_product:
                continue

            vp = tool.vendor_product
            vendor = vp.vendor
            if not vendor or not vendor.is_active:
                logger.warning(f"Vendor {vendor} for Tool '{tool.name}' is inactive. Skipping auto-purchase.")
                continue

            # Check if this item was already sent to the vendor for this order
            if OrderAPIRequest.objects.filter(order=order, vendor=vendor, vendor_product=vp, status='completed').exists():
                logger.info(f"Order #{order.id} already fulfilled via vendor {vendor.name}.")
                continue

            try:
                svc = get_vendor_service(vendor)
                buyer_info = order.delivery_email or order.user.email
                res = svc.purchase(vendor_product_id=vp.vendor_product_id, quantity=1, buyer_info=buyer_info)

                # Record API Log
                api_log = OrderAPIRequest.objects.create(
                    order=order,
                    vendor=vendor,
                    vendor_product=vp,
                    status=res.get('status', 'unknown'),
                    vendor_order_id=res.get('order_id', ''),
                    request_data={'product_id': vp.vendor_product_id, 'qty': 1, 'buyer': buyer_info},
                    response_data=res,
                    error_message=res.get('error', '') or ''
                )

                v_order_id = str(res.get('order_id', '')).strip()
                if v_order_id:
                    order.vendor_order_id = v_order_id
                    order.save(update_fields=['vendor_order_id'])

                if res.get('status') in ['completed', 'success'] and res.get('codes'):
                    codes = res['codes']
                    delivered_codes.extend(codes)
                    ActivityLog.log(
                        action_type='order_fulfilled',
                        title=f"Vendor Order Fulfilled: Order #{order.id}",
                        details=f"Tool: {tool.name} | Vendor: {vendor.name} | Vendor Order ID: {v_order_id} | Codes: {', '.join(codes)}",
                        user=order.user,
                        severity='success'
                    )
                elif res.get('status') == 'pending_manual':
                    is_manual_delivery_needed = True
                    ActivityLog.log(
                        action_type='order_fulfilled',
                        title=f"Vendor Order Pending Manual Delivery: Order #{order.id}",
                        details=f"Tool: {tool.name} | Vendor: {vendor.name} (Requires manual vendor action)",
                        user=order.user,
                        severity='info'
                    )
                else:
                    err_msg = res.get('error') or 'Unknown vendor API error'
                    ActivityLog.log(
                        action_type='order_failed',
                        title=f"Vendor Purchase Failed for Order #{order.id}",
                        details=f"Tool: {tool.name} | Vendor: {vendor.name} | Error: {err_msg}",
                        user=order.user,
                        severity='error'
                    )
                    send_support_vendor_error_alert(order, tool.name, vendor.name, err_msg)

            except Exception as ve:
                logger.error(f"Error processing vendor purchase for Order #{order.id}: {ve}")
                OrderAPIRequest.objects.create(
                    order=order,
                    vendor=vendor,
                    vendor_product=vp,
                    status='failed',
                    error_message=str(ve)
                )
                ActivityLog.log(
                    action_type='order_failed',
                    title=f"Vendor Integration Exception for Order #{order.id}",
                    details=f"Tool: {tool.name} | Error: {ve}",
                    user=order.user,
                    severity='error'
                )
                send_support_vendor_error_alert(order, tool.name, vendor.name, str(ve))

        # Update order access details if codes were received
        if delivered_codes:
            new_codes_text = "\n".join(f"Code: {c}" for c in delivered_codes)
            if order.access_details:
                order.access_details = f"{order.access_details}\n\n[Auto-Fulfilled Credentials]\n{new_codes_text}"
            else:
                order.access_details = f"[Auto-Fulfilled Credentials]\n{new_codes_text}"

            order.delivery_status = 'sent'
            order.save(update_fields=['access_details', 'delivery_status'])

            # Re-trigger email delivery so user receives credentials immediately!
            trigger_delivery(order)

        elif is_manual_delivery_needed:
            order.delivery_notes = f"{order.delivery_notes}\n[Vendor Auto-Order] Purchase requested from vendor API. Pending vendor manual delivery."
            order.save(update_fields=['delivery_notes'])

    except Exception as e:
        logger.error(f"Failed to fulfill order #{order_id} via vendors: {e}")


def fulfill_order_via_vendors(order_id):
    """
    Public function to fulfill vendor order synchronously so that vendor API responses,
    credentials, and errors are immediately captured and saved to the order before response.
    """
    _fulfill_order_logic(order_id)


def send_support_vendor_error_alert(order, tool_name, vendor_name, error_details):
    """
    Sends an email notification to support@onesolai.com when vendor API fails or doesn't return credentials.
    """
    try:
        from django.core.mail import send_mail
        from core.models import SiteSettings
        cfg = SiteSettings.get()
        support_email = cfg.support_email or 'support@onesolai.com'
    except Exception:
        support_email = 'support@onesolai.com'

    subject = f"⚠️ [VENDOR API ISSUE] Manual Fulfillment Needed for Order #{order.order_number} ({tool_name})"
    cust_email = order.delivery_email or (order.user.email if order.user else 'Unregistered User')

    body = f"""Hello Support Team,

A customer paid for Order #{order.order_number} ({tool_name}), but the Vendor API ({vendor_name}) did NOT return immediate access credentials.

--- ORDER & VENDOR FAILURE DETAILS ---
Order Number: #{order.order_number}
Tool Purchased: {tool_name}
Vendor Name: {vendor_name}
Customer Email: {cust_email}
Amount Paid: ₦{order.total_amount_ngn:,.2f} NGN ({order.local_currency} {order.local_amount:,.2f})
Vendor Response / Error: {error_details}

ACTION REQUIRED:
Please check vendor dashboard or manually deliver credentials to the customer, and update the order in Django Admin.

OneSol AI System Notification
"""
    try:
        from django.core.mail import send_mail
        send_mail(
            subject=subject,
            message=body,
            from_email=f"OneSol System <{support_email}>",
            recipient_list=['support@onesolai.com', support_email],
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"Error sending vendor error alert: {e}")
