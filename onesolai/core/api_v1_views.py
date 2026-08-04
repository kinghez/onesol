import json
import logging
import traceback
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from products.models import Tool, Category, Wishlist
from orders.models import Order, OrderItem, PaymentTransaction
from accounts.models import WalletTransaction
from notifications.models import Notification
from vendors.tasks import _fulfill_order_logic
from orders.delivery import trigger_delivery
from core.api_v1_auth import api_v1_auth

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# 1. CATALOG / TOOLS ENDPOINTS (Public & Secret)
# ─────────────────────────────────────────────
@csrf_exempt
@api_v1_auth(require_secret=False)
def v1_list_tools(request):
    """
    GET /api/v1/tools/?query=chatgpt&category=ai-chatbots
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        query = request.GET.get('query', '').strip()
        category_slug = request.GET.get('category', '').strip()

        tools_qs = Tool.objects.filter(is_active=True).select_related('category', 'vendor_product')

        if query:
            tools_qs = tools_qs.filter(name__icontains=query)
        if category_slug:
            tools_qs = tools_qs.filter(category__slug=category_slug)

        tools_data = []
        for t in tools_qs[:50]:
            is_available = t.is_in_stock
            try:
                if hasattr(t, 'vendor_product') and t.vendor_product and hasattr(t.vendor_product, 'vendor'):
                    if not t.vendor_product.vendor.is_active:
                        is_available = False
            except Exception:
                pass

            tools_data.append({
                'id': t.id,
                'name': t.name,
                'slug': t.slug,
                'category': t.category.name if t.category else 'Uncategorized',
                'category_slug': t.category.slug if t.category else '',
                'price_ngn': float(t.get_ngn_price()),
                'price_usd': float(t.get_usd_price()),
                'is_in_stock': is_available,
                'short_description': t.short_description or t.name,
                'detail_url': f"https://onesolai.com/tools/{t.slug}/"
            })

        return JsonResponse({
            'success': True,
            'count': len(tools_data),
            'tools': tools_data
        })
    except Exception as e:
        logger.error(f"v1_list_tools error: {e}\n{traceback.format_exc()}")
        return JsonResponse({'error': 'Server Error', 'message': str(e)}, status=500)


@csrf_exempt
@api_v1_auth(require_secret=False)
def v1_tool_detail(request, tool_id):
    """
    GET /api/v1/tools/<id>/
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        tool = Tool.objects.filter(id=tool_id, is_active=True).select_related('category').first()
        if not tool:
            return JsonResponse({'error': 'Not Found', 'message': 'Tool not found or inactive'}, status=404)

        is_available = tool.is_in_stock
        try:
            if hasattr(tool, 'vendor_product') and tool.vendor_product and hasattr(tool.vendor_product, 'vendor'):
                if not tool.vendor_product.vendor.is_active:
                    is_available = False
        except Exception:
            pass

        return JsonResponse({
            'success': True,
            'tool': {
                'id': tool.id,
                'name': tool.name,
                'slug': tool.slug,
                'category': tool.category.name if tool.category else 'Uncategorized',
                'price_ngn': float(tool.get_ngn_price()),
                'price_usd': float(tool.get_usd_price()),
                'is_in_stock': is_available,
                'short_description': tool.short_description or tool.name,
                'description': tool.description or tool.short_description or tool.name,
                'features': tool.features_list if hasattr(tool, 'features_list') else [],
                'detail_url': f"https://onesolai.com/tools/{tool.slug}/"
            }
        })
    except Exception as e:
        logger.error(f"v1_tool_detail error: {e}\n{traceback.format_exc()}")
        return JsonResponse({'error': 'Server Error', 'message': str(e)}, status=500)


# ─────────────────────────────────────────────
# 2. USER PROFILE & ACCOUNT (Secret Key Required)
# ─────────────────────────────────────────────
@csrf_exempt
@api_v1_auth(require_secret=True)
def v1_user_profile(request):
    """
    GET /api/v1/me/
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        user = request.api_user
        profile = user.profile
        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'wallet_balance_ngn': float(profile.wallet_balance),
                'referral_code': profile.referral_code,
                'referral_earnings_ngn': float(profile.earnings),
                'currency_preference': profile.currency_preference,
                'country_preference': profile.country_preference,
                'created_at': user.date_joined.isoformat()
            }
        })
    except Exception as e:
        logger.error(f"v1_user_profile error: {e}\n{traceback.format_exc()}")
        return JsonResponse({'error': 'Server Error', 'message': str(e)}, status=500)


@csrf_exempt
@api_v1_auth(require_secret=True)
def v1_user_orders(request):
    """
    GET /api/v1/me/orders/
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        user = request.api_user
        orders_qs = Order.objects.filter(user=user).order_by('-created_at').prefetch_related('items__tool')

        orders_data = []
        for o in orders_qs[:50]:
            items = []
            for item in o.items.all():
                items.append({
                    'tool_id': item.tool.id if item.tool else None,
                    'tool_name': item.tool.name if item.tool else 'Tool',
                    'price_ngn': float(item.price_ngn)
                })

            orders_data.append({
                'id': o.id,
                'order_number': o.order_number,
                'status': o.status,
                'total_amount_ngn': float(o.total_amount_ngn),
                'items': items,
                'access_details': o.access_details if o.status == 'paid' else None,
                'created_at': o.created_at.isoformat()
            })

        return JsonResponse({
            'success': True,
            'count': len(orders_data),
            'orders': orders_data
        })
    except Exception as e:
        logger.error(f"v1_user_orders error: {e}\n{traceback.format_exc()}")
        return JsonResponse({'error': 'Server Error', 'message': str(e)}, status=500)


@csrf_exempt
@api_v1_auth(require_secret=True)
def v1_order_detail(request, order_id):
    """
    GET /api/v1/me/orders/<id>/
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        user = request.api_user
        order = Order.objects.filter(id=order_id, user=user).prefetch_related('items__tool').first()
        if not order:
            return JsonResponse({'error': 'Not Found', 'message': 'Order not found'}, status=404)

        items = []
        for item in order.items.all():
            items.append({
                'tool_id': item.tool.id if item.tool else None,
                'tool_name': item.tool.name if item.tool else 'Tool',
                'price_ngn': float(item.price_ngn)
            })

        return JsonResponse({
            'success': True,
            'order': {
                'id': order.id,
                'order_number': order.order_number,
                'status': order.status,
                'total_amount_ngn': float(order.total_amount_ngn),
                'delivery_email': order.delivery_email,
                'access_details': order.access_details,
                'items': items,
                'created_at': order.created_at.isoformat()
            }
        })
    except Exception as e:
        logger.error(f"v1_order_detail error: {e}\n{traceback.format_exc()}")
        return JsonResponse({'error': 'Server Error', 'message': str(e)}, status=500)


# ─────────────────────────────────────────────
# 3. WISHLIST ENDPOINTS (Secret Key Required)
# ─────────────────────────────────────────────
@csrf_exempt
@api_v1_auth(require_secret=True)
def v1_user_wishlist(request):
    """
    GET /api/v1/me/wishlist/ -> List items
    POST /api/v1/me/wishlist/ -> Add item {"tool_id": 12}
    """
    user = request.api_user

    if request.method == 'GET':
        items_qs = Wishlist.objects.filter(user=user).select_related('tool')
        wishlist_data = []
        for item in items_qs:
            t = item.tool
            wishlist_data.append({
                'wishlist_id': item.id,
                'tool_id': t.id,
                'name': t.name,
                'slug': t.slug,
                'price_ngn': float(t.get_ngn_price()),
                'is_in_stock': t.is_in_stock,
                'added_at': item.created_at.isoformat() if hasattr(item, 'created_at') else None
            })
        return JsonResponse({'success': True, 'count': len(wishlist_data), 'wishlist': wishlist_data})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body) if request.body else request.POST
            tool_id = data.get('tool_id')
            if not tool_id:
                return JsonResponse({'error': 'Bad Request', 'message': 'tool_id is required'}, status=400)

            tool = Tool.objects.filter(id=tool_id, is_active=True).first()
            if not tool:
                return JsonResponse({'error': 'Not Found', 'message': 'Tool not found'}, status=404)

            item, created = Wishlist.objects.get_or_create(user=user, tool=tool)
            return JsonResponse({
                'success': True,
                'message': f"Added {tool.name} to wishlist." if created else f"{tool.name} is already in wishlist.",
                'added': created
            })
        except Exception as e:
            return JsonResponse({'error': 'Server Error', 'message': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
@api_v1_auth(require_secret=True)
def v1_remove_wishlist(request, wishlist_id):
    """
    DELETE /api/v1/me/wishlist/<id>/
    """
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        user = request.api_user
        item = Wishlist.objects.filter(id=wishlist_id, user=user).first()
        if not item:
            return JsonResponse({'error': 'Not Found', 'message': 'Wishlist item not found'}, status=404)

        item.delete()
        return JsonResponse({'success': True, 'message': 'Item removed from wishlist.'})
    except Exception as e:
        return JsonResponse({'error': 'Server Error', 'message': str(e)}, status=500)


# ─────────────────────────────────────────────
# 4. PURCHASING & WALLET TOP-UP (Secret Key Required)
# ─────────────────────────────────────────────
@csrf_exempt
@api_v1_auth(require_secret=True)
def v1_buy_tool(request):
    """
    POST /api/v1/orders/buy/
    Body: {"tool_id": 12, "delivery_email": "user@example.com"}
    Deducts wallet balance, creates paid order, fulfills via vendor, and returns access details.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body) if request.body else request.POST
        tool_id = data.get('tool_id')
        delivery_email = data.get('delivery_email', '').strip() or request.api_user.email

        if not tool_id:
            return JsonResponse({'error': 'Bad Request', 'message': 'tool_id is required'}, status=400)

        tool = Tool.objects.filter(id=tool_id, is_active=True).first()
        if not tool:
            return JsonResponse({'error': 'Not Found', 'message': 'Selected tool is invalid or inactive'}, status=404)

        user = request.api_user
        profile = user.profile
        price_ngn = Decimal(str(round(tool.get_ngn_price(), 2)))

        if profile.wallet_balance < price_ngn:
            return JsonResponse({
                'error': 'Insufficient Balance',
                'message': f"Insufficient wallet balance. Current balance: NGN {profile.wallet_balance:,.2f}, Tool price: NGN {price_ngn:,.2f}.",
                'wallet_balance_ngn': float(profile.wallet_balance),
                'required_amount_ngn': float(price_ngn)
            }, status=400)

        # 1. Deduct wallet
        profile.wallet_balance -= price_ngn
        profile.save(update_fields=['wallet_balance'])

        WalletTransaction.objects.create(
            user=user,
            transaction_type='purchase',
            amount_ngn=price_ngn,
            status='success',
            reference=f"API_BUY_{tool.id}",
            description=f"Purchased {tool.name} via API Key ({request.api_key.name})"
        )

        # 2. Create paid order
        order = Order.objects.create(
            user=user,
            total_amount_ngn=price_ngn,
            local_currency='NGN',
            local_amount=price_ngn,
            exchange_rate=Decimal('1500.00'),
            delivery_email=delivery_email,
            status='paid',
        )

        OrderItem.objects.create(
            order=order,
            tool=tool,
            price_ngn=price_ngn,
        )

        PaymentTransaction.objects.create(
            order=order,
            gateway='wallet',
            transaction_id=f"API_PAY_{order.id}",
            reference=f"API_PAY_{order.id}",
            status='success',
            amount_paid=price_ngn,
            currency_paid='NGN',
        )

        # 3. Vendor fulfillment & delivery
        try:
            _fulfill_order_logic(order.id)
            order.refresh_from_db()
        except Exception as ve:
            logger.error(f"API purchase vendor fulfillment error for Order #{order.id}: {ve}")

        trigger_delivery(order)

        return JsonResponse({
            'success': True,
            'message': f"Successfully purchased {tool.name}! Order #{order.order_number} processed.",
            'order': {
                'id': order.id,
                'order_number': order.order_number,
                'tool_name': tool.name,
                'amount_paid_ngn': float(price_ngn),
                'delivery_email': order.delivery_email,
                'access_details': order.access_details or "Activation sent via email and in-app notification."
            }
        })
    except Exception as e:
        logger.error(f"v1_buy_tool error: {e}\n{traceback.format_exc()}")
        return JsonResponse({'error': 'Server Error', 'message': str(e)}, status=500)


@csrf_exempt
@api_v1_auth(require_secret=True)
def v1_wallet_topup(request):
    """
    POST /api/v1/wallet/topup/
    Body: {"amount_ngn": 5000}
    Initiates a Paystack checkout transaction for wallet funding.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body) if request.body else request.POST
        amount = Decimal(str(data.get('amount_ngn', 0)))

        if amount < Decimal('500'):
            return JsonResponse({'error': 'Bad Request', 'message': 'Minimum wallet deposit is NGN 500.00'}, status=400)

        import requests, secrets
        paystack_secret = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        if not paystack_secret:
            return JsonResponse({'error': 'Configuration Error', 'message': 'Paystack is not configured on server'}, status=500)

        reference = f"WAPI_{secrets.token_hex(8)}"
        user = request.api_user

        headers = {
            'Authorization': f'Bearer {paystack_secret}',
            'Content-Type': 'application/json'
        }
        payload = {
            'email': user.email,
            'amount': int(amount * 100),
            'reference': reference,
            'callback_url': 'https://onesolai.com/orders/paystack/callback/',
            'metadata': {
                'type': 'wallet_topup',
                'user_id': user.id,
                'amount_ngn': str(amount)
            }
        }

        res = requests.post('https://api.paystack.co/transaction/initialize', json=payload, headers=headers, timeout=10)
        res_data = res.json()

        if res.status_code == 200 and res_data.get('status'):
            return JsonResponse({
                'success': True,
                'reference': reference,
                'amount_ngn': float(amount),
                'authorization_url': res_data['data']['authorization_url']
            })
        else:
            return JsonResponse({'error': 'Payment Gateway Error', 'message': res_data.get('message', 'Failed to initialize Paystack checkout')}, status=400)

    except Exception as e:
        logger.error(f"v1_wallet_topup error: {e}\n{traceback.format_exc()}")
        return JsonResponse({'error': 'Server Error', 'message': str(e)}, status=500)


# ─────────────────────────────────────────────
# 5. NOTIFICATIONS ENDPOINTS (Secret Key Required)
# ─────────────────────────────────────────────
@csrf_exempt
@api_v1_auth(require_secret=True)
def v1_user_notifications(request):
    """
    GET /api/v1/me/notifications/
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        user = request.api_user
        notifs_qs = Notification.objects.filter(user=user).order_by('-created_at')

        notifs_data = []
        for n in notifs_qs[:30]:
            notifs_data.append({
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'is_read': n.is_read,
                'notification_type': n.notification_type if hasattr(n, 'notification_type') else 'system',
                'created_at': n.created_at.isoformat()
            })

        return JsonResponse({'success': True, 'count': len(notifs_data), 'notifications': notifs_data})
    except Exception as e:
        return JsonResponse({'error': 'Server Error', 'message': str(e)}, status=500)


@csrf_exempt
@api_v1_auth(require_secret=True)
def v1_mark_notifications_read(request):
    """
    POST /api/v1/me/notifications/mark-read/
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        user = request.api_user
        Notification.objects.filter(user=user, is_read=False).update(is_read=True)
        return JsonResponse({'success': True, 'message': 'All notifications marked as read.'})
    except Exception as e:
        return JsonResponse({'error': 'Server Error', 'message': str(e)}, status=500)
