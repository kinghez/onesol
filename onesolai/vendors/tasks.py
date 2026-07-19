import logging
from celery import shared_task
from django.utils import timezone
from .models import VendorProduct
from orders.models import Order, OrderItem
from .services import get_vendor_service

logger = logging.getLogger(__name__)

@shared_task
def fulfill_order_via_vendors(order_id: int):
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found for fulfillment.")
        return

    if order.delivery_status == 'sent':
        return # Already fulfilled

    items = order.items.all()
    all_codes = []
    has_failed = False
    has_manual = False

    for item in items:
        # Check if tool maps to a vendor product
        if not item.tool or not item.tool.vendor_product:
            continue
            
        vendor_prod = item.tool.vendor_product
        vendor = vendor_prod.vendor
        
        try:
            service = get_vendor_service(vendor)
            
            # Place order
            result = service.purchase(
                vendor_product_id=vendor_prod.vendor_product_id,
                quantity=1, # Assume 1 qty per tool for now
                buyer_info=order.delivery_email
            )
            
            if result['status'] == 'completed':
                if result.get('codes'):
                    all_codes.extend(result['codes'])
            elif result['status'] == 'pending_manual':
                has_manual = True
                order.delivery_notes += f"\n[{timezone.now()}] ShopBot Order ID: {result.get('order_id')}"
            else:
                has_failed = True
                logger.error(f"Failed to fulfill item {item.id} via vendor: {result.get('error')}")
                
        except Exception as e:
            has_failed = True
            logger.exception(f"Exception during vendor purchase for item {item.id}: {str(e)}")

    # Update order based on results
    if all_codes:
        existing_access = order.access_details or ""
        new_access = existing_access + "\n" + "\n".join(all_codes)
        order.access_details = new_access.strip()

    if has_failed:
        order.delivery_status = 'failed'
        order.delivery_notes += f"\n[{timezone.now()}] Some vendor purchases failed."
    elif has_manual:
        order.delivery_status = 'pending'
        order.delivery_notes += f"\n[{timezone.now()}] Pending manual delivery from vendor."
    elif all_codes:
        order.delivery_status = 'sent'
        order.delivery_notes += f"\n[{timezone.now()}] Auto-fulfilled via API."
        
        # NOTE: In a real flow, here is where you would send the delivery email
        # send_delivery_email(order.user.email, all_codes)

    order.save()
    logger.info(f"Fulfillment completed for Order {order_id}. Status: {order.delivery_status}")
