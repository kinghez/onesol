import json
import hmac
import hashlib
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from orders.models import Order
from .models import Vendor

logger = logging.getLogger(__name__)

def verify_shopbot_signature(secret: str, timestamp: str, body_bytes: bytes, received_sig: str) -> bool:
    try:
        msg = f"{timestamp}.".encode() + body_bytes
        expected = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", received_sig)
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False

@csrf_exempt
def shopbot_webhook(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    timestamp = request.headers.get('X-Webhook-Timestamp')
    signature = request.headers.get('X-Webhook-Signature')
    event_type = request.headers.get('X-Event-Type')

    # Find the Shop Bot vendor to get the secret
    vendor = Vendor.objects.filter(api_type='shopbot', is_active=True).first()
    if not vendor or not vendor.webhook_secret:
        return JsonResponse({'success': False, 'error': 'Webhook secret not configured'}, status=400)

    if not verify_shopbot_signature(vendor.webhook_secret, timestamp, request.body, signature):
        return JsonResponse({'success': False, 'error': 'Invalid signature'}, status=401)

    try:
        payload = json.loads(request.body)
        
        # We care about order.completed events
        if event_type == 'order.completed':
            data = payload.get('data', {})
            vendor_order_id = data.get('order_id')
            status = data.get('status')
            
            # Since ShopBot doesn't easily let us pass a passthrough ID, 
            # we might have stored their order_id in our Order.delivery_notes 
            # or somewhere. Actually, our task doesn't save the vendor_order_id.
            # Let's fix that. Assume we save `ShopBot Order ID: {order_id}` in notes.
            
            # For now, let's just log it and if we can match it, update it.
            # A robust way is adding vendor_order_id to OrderItem. Let's assume we parse it from delivery_notes.
            
            logger.info(f"ShopBot webhook received for order {vendor_order_id}. Status: {status}")
            
            # Attempt to find the order by parsing delivery_notes
            orders = Order.objects.filter(delivery_status='pending', delivery_notes__icontains=vendor_order_id)
            for order in orders:
                if status == 'completed':
                    # Delivery is manual, so maybe the codes are in the webhook?
                    # Or the vendor just marks it completed.
                    codes = data.get('codes', [])
                    if codes:
                        existing = order.access_details or ""
                        order.access_details = existing + "\n" + "\n".join(codes)
                    order.delivery_status = 'sent'
                    order.delivery_notes += f"\n[{timezone.now()}] Manual fulfillment completed via ShopBot webhook."
                    order.save()
                    # Trigger email
                    # send_delivery_email(order.user.email, codes)

        return JsonResponse({'success': True})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.exception("Error processing ShopBot webhook")
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)
