import json
import logging
import traceback
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from products.models import Tool, Wishlist
from orders.models import Order, OrderItem, PaymentTransaction
from accounts.models import WalletTransaction, Referral, WithdrawalRequest
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


def extract_request_data(request):
    """
    Utility helper to extract parameters from GET query string, JSON body, or POST form.
    """
    data = {}
    if request.GET:
        for k, v in request.GET.items():
            data[k] = v
    if request.body:
        try:
            body_data = json.loads(request.body)
            if isinstance(body_data, dict):
                data.update(body_data)
        except Exception:
            pass
    if request.POST:
        for k, v in request.POST.items():
            data[k] = v
    return data


@csrf_exempt
def agent_check_tools(request):
    """
    GET/POST /api/agent/tools/?query=chatgpt
    Returns product name, prices, category, availability stock status.
    """
    try:
        data = extract_request_data(request)
        query = data.get('query', '').strip()
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
    if not verify_agent_auth(request):
        return JsonResponse({'error': 'Unauthorized agent request.'}, status=401)

    try:
        data = extract_request_data(request)
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
    if not verify_agent_auth(request):
        return JsonResponse({'error': 'Unauthorized agent request.'}, status=401)

    try:
        data = extract_request_data(request)
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


@csrf_exempt
def agent_user_profile(request):
    """
    GET/POST /api/agent/user-profile/
    Headers: X-Agent-Secret: onesol_agent_secret_2026
    Params: user_email="user@example.com"
    """
    if not verify_agent_auth(request):
        return JsonResponse({'error': 'Unauthorized agent request.'}, status=401)

    try:
        data = extract_request_data(request)
        email = data.get('user_email', '').strip()

        if not email:
            return JsonResponse({'success': False, 'error': 'user_email is required'}, status=400)

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return JsonResponse({'success': False, 'error': f'User with email {email} not found'}, status=404)

        profile = user.profile
        orders_count = Order.objects.filter(user=user).count()
        paid_orders_count = Order.objects.filter(user=user, status='paid').count()
        wishlist_count = Wishlist.objects.filter(user=user).count()

        return JsonResponse({
            'success': True,
            'user_email': user.email,
            'full_name': user.get_full_name() or user.username,
            'username': user.username,
            'wallet_balance_ngn': float(profile.wallet_balance),
            'wallet_balance_formatted': f"NGN {profile.wallet_balance:,.2f}",
            'referral_code': profile.referral_code,
            'referral_earnings_ngn': float(profile.earnings),
            'referral_earnings_formatted': f"NGN {profile.earnings:,.2f}",
            'currency_preference': profile.currency_preference or 'NGN',
            'country_preference': profile.country_preference or 'Nigeria',
            'total_orders': orders_count,
            'paid_orders': paid_orders_count,
            'wishlist_count': wishlist_count,
            'date_joined': user.date_joined.strftime('%Y-%m-%d')
        })
    except Exception as e:
        logger.error(f"Error in agent_user_profile: {e}\n{traceback.format_exc()}")
        return JsonResponse({'success': False, 'error': f"Server error: {str(e)}"}, status=500)


@csrf_exempt
def agent_user_wallet(request):
    """
    GET/POST /api/agent/user-wallet/
    Headers: X-Agent-Secret: onesol_agent_secret_2026
    Params: user_email="user@example.com"
    """
    if not verify_agent_auth(request):
        return JsonResponse({'error': 'Unauthorized agent request.'}, status=401)

    try:
        data = extract_request_data(request)
        email = data.get('user_email', '').strip()

        if not email:
            return JsonResponse({'success': False, 'error': 'user_email is required'}, status=400)

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return JsonResponse({'success': False, 'error': f'User with email {email} not found'}, status=404)

        profile = user.profile
        recent_txs = WalletTransaction.objects.filter(user=user).order_by('-created_at')[:5]

        tx_list = []
        for tx in recent_txs:
            tx_list.append({
                'id': tx.id,
                'type': tx.transaction_type,
                'type_display': tx.get_transaction_type_display() if hasattr(tx, 'get_transaction_type_display') else tx.transaction_type,
                'amount_ngn': float(tx.amount_ngn),
                'amount_formatted': f"NGN {tx.amount_ngn:,.2f}",
                'status': tx.status,
                'reference': tx.reference or '',
                'description': tx.description or '',
                'date': tx.created_at.strftime('%Y-%m-%d %H:%M') if hasattr(tx, 'created_at') and tx.created_at else ''
            })

        return JsonResponse({
            'success': True,
            'user_email': user.email,
            'wallet_balance_ngn': float(profile.wallet_balance),
            'wallet_balance_formatted': f"NGN {profile.wallet_balance:,.2f}",
            'currency': 'NGN',
            'recent_transactions_count': len(tx_list),
            'recent_transactions': tx_list
        })
    except Exception as e:
        logger.error(f"Error in agent_user_wallet: {e}\n{traceback.format_exc()}")
        return JsonResponse({'success': False, 'error': f"Server error: {str(e)}"}, status=500)


@csrf_exempt
def agent_user_referrals(request):
    """
    GET/POST /api/agent/user-referrals/
    Headers: X-Agent-Secret: onesol_agent_secret_2026
    Params: user_email="user@example.com"
    """
    if not verify_agent_auth(request):
        return JsonResponse({'error': 'Unauthorized agent request.'}, status=401)

    try:
        data = extract_request_data(request)
        email = data.get('user_email', '').strip()

        if not email:
            return JsonResponse({'success': False, 'error': 'user_email is required'}, status=400)

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return JsonResponse({'success': False, 'error': f'User with email {email} not found'}, status=404)

        profile = user.profile
        ref_link = f"https://onesolai.com/auth/signup/?ref={profile.referral_code}" if profile.referral_code else ""
        
        all_referrals = Referral.objects.filter(referrer=user).select_related('referred_user').order_by('-date_referred')
        total_count = all_referrals.count()
        rewarded_count = all_referrals.filter(status='rewarded').count()
        pending_count = all_referrals.filter(status='pending').count()

        recent_list = []
        for r in all_referrals[:5]:
            recent_list.append({
                'referred_user': r.referred_user.email,
                'status': r.status,
                'status_display': r.get_status_display() if hasattr(r, 'get_status_display') else r.status,
                'reward_amount_ngn': float(r.reward_amount_ngn),
                'date_referred': r.date_referred.strftime('%Y-%m-%d')
            })

        return JsonResponse({
            'success': True,
            'user_email': user.email,
            'referral_code': profile.referral_code or '',
            'referral_link': ref_link,
            'referral_earnings_ngn': float(profile.earnings),
            'referral_earnings_formatted': f"NGN {profile.earnings:,.2f}",
            'reward_per_referral': "NGN 2,000.00",
            'total_referrals': total_count,
            'successful_referrals': rewarded_count,
            'pending_referrals': pending_count,
            'recent_referrals': recent_list
        })
    except Exception as e:
        logger.error(f"Error in agent_user_referrals: {e}\n{traceback.format_exc()}")
        return JsonResponse({'success': False, 'error': f"Server error: {str(e)}"}, status=500)


@csrf_exempt
def agent_user_withdrawals(request):
    """
    GET/POST /api/agent/user-withdrawals/
    Headers: X-Agent-Secret: onesol_agent_secret_2026
    Params: user_email="user@example.com"
    """
    if not verify_agent_auth(request):
        return JsonResponse({'error': 'Unauthorized agent request.'}, status=401)

    try:
        data = extract_request_data(request)
        email = data.get('user_email', '').strip()

        if not email:
            return JsonResponse({'success': False, 'error': 'user_email is required'}, status=400)

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return JsonResponse({'success': False, 'error': f'User with email {email} not found'}, status=404)

        profile = user.profile
        withdrawals_qs = WithdrawalRequest.objects.filter(user=user).order_by('-created_at')

        withdrawals_list = []
        for w in withdrawals_qs[:5]:
            withdrawals_list.append({
                'id': w.id,
                'amount_ngn': float(w.amount),
                'amount_formatted': f"NGN {w.amount:,.2f}",
                'method': w.get_withdrawal_method_display() if hasattr(w, 'get_withdrawal_method_display') else w.withdrawal_method,
                'status': w.status,
                'status_display': w.get_status_display() if hasattr(w, 'get_status_display') else w.status,
                'admin_note': w.admin_note or '',
                'date_requested': w.created_at.strftime('%Y-%m-%d %H:%M')
            })

        site_cfg = SiteSettings.get()
        min_withdrawal = float(site_cfg.min_withdrawal_ngn) if hasattr(site_cfg, 'min_withdrawal_ngn') else 5000.0

        return JsonResponse({
            'success': True,
            'user_email': user.email,
            'referral_earnings_ngn': float(profile.earnings),
            'min_withdrawal_ngn': min_withdrawal,
            'has_payout_details': profile.has_payout_details,
            'preferred_withdrawal_method': profile.preferred_withdrawal_method or 'bank',
            'payout_details': {
                'bank_name': profile.bank_name or '',
                'account_number': profile.account_number or '',
                'account_name': profile.account_name or '',
                'crypto_wallet_address': profile.crypto_wallet_address or '',
                'crypto_network': profile.crypto_network or 'USDT (TRC20)'
            },
            'total_withdrawals_requested': withdrawals_qs.count(),
            'recent_withdrawals': withdrawals_list
        })
    except Exception as e:
        logger.error(f"Error in agent_user_withdrawals: {e}\n{traceback.format_exc()}")
        return JsonResponse({'success': False, 'error': f"Server error: {str(e)}"}, status=500)


@csrf_exempt
def agent_order_status(request):
    """
    GET/POST /api/agent/order-status/
    Headers: X-Agent-Secret: onesol_agent_secret_2026
    Params: order_number="OS-00025" OR user_email="user@example.com"
    """
    if not verify_agent_auth(request):
        return JsonResponse({'error': 'Unauthorized agent request.'}, status=401)

    try:
        data = extract_request_data(request)
        order_num_raw = data.get('order_number') or data.get('order_id') or ''
        email = data.get('user_email', '').strip()

        orders_qs = Order.objects.none()

        if order_num_raw:
            clean_str = str(order_num_raw).strip().upper().replace('#', '').replace('OS-', '').lstrip('0')
            try:
                order_id = int(clean_str)
                orders_qs = Order.objects.filter(id=order_id)
            except ValueError:
                return JsonResponse({'success': False, 'error': f"Invalid order number format '{order_num_raw}'"}, status=400)
        elif email:
            user = User.objects.filter(email__iexact=email).first()
            if not user:
                return JsonResponse({'success': False, 'error': f"User with email '{email}' not found"}, status=404)
            orders_qs = Order.objects.filter(user=user).order_by('-created_at')[:5]
        else:
            return JsonResponse({'success': False, 'error': 'Either order_number or user_email is required'}, status=400)

        orders_data = []
        for o in orders_qs:
            items_list = []
            for item in o.items.all():
                items_list.append({
                    'tool_id': item.tool.id if item.tool else None,
                    'tool_name': item.tool.name if item.tool else 'Tool',
                    'price_ngn': float(item.price_ngn)
                })

            orders_data.append({
                'order_id': o.id,
                'order_number': o.order_number,
                'user_email': o.user.email,
                'status': o.status,
                'status_display': o.get_status_display() if hasattr(o, 'get_status_display') else o.status,
                'delivery_status': o.delivery_status,
                'total_amount_ngn': float(o.total_amount_ngn),
                'total_amount_formatted': f"NGN {o.total_amount_ngn:,.2f}",
                'items': items_list,
                'access_details': o.access_details if o.status == 'paid' else "Access details are generated once order status is Paid.",
                'created_at': o.created_at.strftime('%Y-%m-%d %H:%M')
            })

        if not orders_data:
            return JsonResponse({'success': False, 'error': 'No matching orders found'}, status=404)

        return JsonResponse({
            'success': True,
            'count': len(orders_data),
            'orders': orders_data
        })
    except Exception as e:
        logger.error(f"Error in agent_order_status: {e}\n{traceback.format_exc()}")
        return JsonResponse({'success': False, 'error': f"Server error: {str(e)}"}, status=500)
