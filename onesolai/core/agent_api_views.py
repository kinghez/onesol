import json
import logging
import traceback
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from products.models import Tool, Wishlist
from orders.models import Order, OrderItem, PaymentTransaction
from accounts.models import WalletTransaction
from vendors.tasks import _fulfill_order_logic
from orders.delivery import trigger_delivery
from core.models import SiteSettings

logger = logging.getLogger(__name__)
User = get_user_model()


def verify_agent_auth(request):
    """
    Checks X-Agent-Secret or Authorization header against configured key.
    """
    try:
        settings_obj = SiteSettings.get()
        agent_key = getattr(settings_obj, 'agent_api_key', None) or 'onesol_agent_secret_2026'
        
        auth_header = request.headers.get('X-Agent-Secret') or request.headers.get('Authorization')
        if auth_header and 'Bearer ' in auth_header:
            auth_header = auth_header.replace('Bearer ', '').strip()
        
        if agent_key and auth_header != agent_key:
            return False
        return True
    except Exception as e:
        logger.error(f"Error in verify_agent_auth: {e}")
        return True


@csrf_exempt
def agent_check_tools(request):
    """
    GET /api/agent/tools/?query=chatgpt
    Returns product name, prices, category, availability stock status.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        query = request.GET.get('query', '').strip()
        tools_qs = Tool.objects.filter(is_active=True)

        if query:
            tools_qs = tools_qs.filter(name__icontains=query)

        tools_data = []
        for t in tools_qs[:25]:
            is_available = t.is_in_stock
            try:
                if hasattr(t, 'vendor_product') and t.vendor_product and hasattr(t.vendor_product, 'vendor'):
                    if not t.vendor_product.vendor.is_active:
                        is_available = False
            except Exception:
                pass

            tools_data.append({
                'tool_id': t.id,
                'name': t.name,
                'category': t.category.name if t.category else 'Uncategorized',
                'price_ngn': float(t.get_ngn_price()),
                'price_usd': float(t.get_usd_price()),
                'is_in_stock': is_available,
                'description': t.short_description or t.name,
                'detail_url': f"https://onesolai.com/tools/{t.slug}/"
            })

        return JsonResponse({
            'success': True,
            'count': len(tools_data),
            'tools': tools_data
        })
    except Exception as e:
        logger.error(f"Error in agent_check_tools: {e}\n{traceback.format_exc()}")
        return JsonResponse({'success': False, 'error': f"Server error: {str(e)}"}, status=500)


@csrf_exempt
def agent_add_to_wishlist(request):
    """
    POST /api/agent/add-to-wishlist/
    Headers: X-Agent-Secret: onesol_agent_secret_2026
    Body: {"user_email": "user@example.com", "tool_id": 12}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    if not verify_agent_auth(request):
        return JsonResponse({'error': 'Unauthorized agent request.'}, status=401)

    try:
        try:
            data = json.loads(request.body) if request.body else request.POST
        except Exception:
            data = request.POST

        email = data.get('user_email', '').strip()
        tool_id = data.get('tool_id')
        tool_name = data.get('tool_name', '').strip()

        if not email:
            return JsonResponse({'success': False, 'error': 'user_email is required'}, status=400)

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return JsonResponse({'success': False, 'error': f'User with email {email} not found'}, status=404)

        tool = None
        if tool_id:
            tool = Tool.objects.filter(id=tool_id, is_active=True).first()
        elif tool_name:
            tool = Tool.objects.filter(name__icontains=tool_name, is_active=True).first()

        if not tool:
            return JsonResponse({'success': False, 'error': 'Tool not found'}, status=404)

        item, created = Wishlist.objects.get_or_create(user=user, tool=tool)
        msg = f"Added {tool.name} to {user.email}'s wishlist!" if created else f"{tool.name} is already in {user.email}'s wishlist!"

        return JsonResponse({
            'success': True,
            'message': msg,
            'added': created
        })
    except Exception as e:
        logger.error(f"Error in agent_add_to_wishlist: {e}\n{traceback.format_exc()}")
        return JsonResponse({'success': False, 'error': f"Server error: {str(e)}"}, status=500)


@csrf_exempt
def agent_buy_tool(request):
    """
    POST /api/agent/buy-tool/
    Headers: X-Agent-Secret: onesol_agent_secret_2026
    Body: {"user_email": "user@example.com", "tool_id": 12, "payment_method": "wallet"}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    if not verify_agent_auth(request):
        return JsonResponse({'error': 'Unauthorized agent request.'}, status=401)

    try:
        try:
            data = json.loads(request.body) if request.body else request.POST
        except Exception:
            data = request.POST

        email = data.get('user_email', '').strip()
        tool_id = data.get('tool_id')
        tool_name = data.get('tool_name', '').strip()
        payment_method = data.get('payment_method', 'wallet').strip()

        if not email:
            return JsonResponse({'success': False, 'error': 'user_email is required'}, status=400)

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return JsonResponse({'success': False, 'error': f'User with email {email} not found'}, status=404)

        tool = None
        if tool_id:
            tool = Tool.objects.filter(id=tool_id, is_active=True).first()
        elif tool_name:
            tool = Tool.objects.filter(name__icontains=tool_name, is_active=True).first()

        if not tool:
            return JsonResponse({'success': False, 'error': 'Selected tool is invalid or inactive'}, status=404)

        price_ngn = Decimal(str(round(tool.get_ngn_price(), 2)))
        profile = user.profile

        if payment_method == 'wallet':
            if profile.wallet_balance < price_ngn:
                return JsonResponse({
                    'success': False,
                    'error': f"Insufficient wallet balance. User balance: NGN {profile.wallet_balance:,.2f}, Tool price: NGN {price_ngn:,.2f}."
                }, status=400)

            profile.wallet_balance -= price_ngn
            profile.save(update_fields=['wallet_balance'])

            WalletTransaction.objects.create(
                user=user,
                transaction_type='purchase',
                amount_ngn=price_ngn,
                status='success',
                reference=f"AGENT_BUY_{tool.id}",
                description=f"Purchased {tool.name} via AI Chatbot Agent"
            )

        order = Order.objects.create(
            user=user,
            total_amount_ngn=price_ngn,
            local_currency='NGN',
            local_amount=price_ngn,
            exchange_rate=Decimal('1500.00'),
            delivery_email=user.email,
            status='paid',
        )

        OrderItem.objects.create(
            order=order,
            tool=tool,
            price_ngn=price_ngn,
        )

        PaymentTransaction.objects.create(
            order=order,
            gateway='wallet' if payment_method == 'wallet' else 'manual',
            transaction_id=f"AGENT_PAY_{order.id}",
            reference=f"AGENT_PAY_{order.id}",
            status='success',
            amount_paid=price_ngn,
            currency_paid='NGN',
        )

        try:
            _fulfill_order_logic(order.id)
            order.refresh_from_db()
        except Exception as ve:
            logger.error(f"Agent purchase vendor error for Order #{order.id}: {ve}")

        trigger_delivery(order)

        return JsonResponse({
            'success': True,
            'order_number': order.order_number,
            'tool_name': tool.name,
            'access_details': order.access_details or "Activation sent via email and in-app notification.",
            'message': f"Successfully purchased {tool.name} for {user.email}! Order #{order.order_number} processed."
        })
    except Exception as e:
        logger.error(f"Error in agent_buy_tool: {e}\n{traceback.format_exc()}")
        return JsonResponse({'success': False, 'error': f"Server error: {str(e)}"}, status=500)
