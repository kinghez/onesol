from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate

from django.contrib.auth import get_user_model
from accounts.models import User, Profile, Referral
from orders.models import Order
from products.models import Tool
from vendors.models import Vendor
from vendors.services import get_vendor_service
from .models import VendorBalanceSnapshot

@staff_member_required
def admin_analytics_dashboard(request):
    """
    Custom Business Intelligence Dashboard for Staff/Admins with advanced filters.
    """
    now = timezone.now()
    
    # Defaults
    date_range = request.GET.get('date_range', '30')
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    country = request.GET.get('country', 'All')
    product_filter = request.GET.get('product', 'All')

    # Base Queries
    users_qs = get_user_model().objects.all()
    orders_qs = Order.objects.all()
    
    # Store for dynamic filtering logic
    start_date = now - timedelta(days=30)
    
    if date_range != 'all':
        if date_range == 'custom' and start_date_str and end_date_str:
            try:
                start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                orders_qs = orders_qs.filter(created_at__range=[start_dt, end_dt])
                users_qs = users_qs.filter(date_joined__range=[start_dt, end_dt])
                start_date = start_dt
            except ValueError:
                pass
        else:
            try:
                days = int(date_range)
                start_date = now - timedelta(days=days)
                orders_qs = orders_qs.filter(created_at__gte=start_date)
                users_qs = users_qs.filter(date_joined__gte=start_date)
            except ValueError:
                pass

    # Apply Filters
    if country != 'All':
        users_qs = users_qs.filter(profile__country_preference__icontains=country)
        orders_qs = orders_qs.filter(user__profile__country_preference__icontains=country)
        
    if product_filter != 'All' and product_filter.isdigit():
        orders_qs = orders_qs.filter(items__tool_id=product_filter)

    # 1. User Metrics
    total_users = users_qs.count()
    active_users = users_qs.filter(is_active=True).count()
    users_past_7_days = users_qs.filter(date_joined__gte=now - timedelta(days=7)).count()
    
    # Conversion Rate
    users_with_purchases = orders_qs.filter(status='paid').values('user').distinct().count()
    conversion_rate = (users_with_purchases / total_users * 100) if total_users > 0 else 0

    # 2. Payment Metrics
    total_processed = orders_qs.filter(status='paid').aggregate(total=Sum('total_amount_ngn'))['total'] or 0.0
    successful_orders = orders_qs.filter(status='paid').count()
    failed_orders = orders_qs.filter(status='failed').count()
    total_payment_attempts = successful_orders + failed_orders
    success_rate = (successful_orders / total_payment_attempts * 100) if total_payment_attempts > 0 else 0
    fail_rate = 100 - success_rate if total_payment_attempts > 0 else 0

    # 3. Product Metrics
    all_active_tools = Tool.objects.filter(is_active=True)
    total_tools = all_active_tools.count()
    out_of_stock_tools = sum(1 for t in all_active_tools if not t.is_in_stock)

    # 4. Top Selling Tools (Leaderboard)
    top_tools = Tool.objects.annotate(
        sales_count=Count('orderitem', filter=Q(orderitem__order__in=orders_qs, orderitem__order__status='paid')),
        revenue=Sum('orderitem__price_ngn', filter=Q(orderitem__order__in=orders_qs, orderitem__order__status='paid'))
    ).filter(sales_count__gt=0).order_by('-revenue')[:5]
    
    # 5. Top Referrers
    top_referrers = Referral.objects.filter(status='rewarded').values(
        'referrer__email', 'referrer__first_name'
    ).annotate(
        total_referrals=Count('id'),
        total_earned=Sum('reward_amount_ngn')
    ).order_by('-total_earned')[:5]

    # 6. Chart Data: Revenue Trend
    revenue_trend = orders_qs.filter(status='paid').annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(daily_total=Sum('total_amount_ngn')).order_by('date')
    
    rev_labels = [r['date'].strftime('%b %d') for r in revenue_trend]
    rev_data = [float(r['daily_total']) for r in revenue_trend]

    # 7. Chart Data: User Growth Trend
    user_growth = users_qs.filter(date_joined__gte=start_date).annotate(
        date=TruncDate('date_joined')
    ).values('date').annotate(daily_count=Count('id')).order_by('date')
    
    growth_labels = [g['date'].strftime('%b %d') for g in user_growth]
    growth_data = [g['daily_count'] for g in user_growth]

    # 8. User Distribution Map Data (Country counts)
    country_distribution = Profile.objects.exclude(country_preference__isnull=True).exclude(country_preference='').values('country_preference').annotate(count=Count('id'))
    map_data = {item['country_preference']: item['count'] for item in country_distribution}

    # Filter Options for the UI
    all_countries = Profile.objects.exclude(country_preference__isnull=True).exclude(country_preference='').values_list('country_preference', flat=True).distinct()
    all_tools = Tool.objects.filter(is_active=True).values('id', 'name')

    # 9. Recent Activity Logs
    from .models import ActivityLog
    recent_activity_logs = ActivityLog.objects.all().select_related('user')[:10]

    context = {
        'total_users': total_users,
        'active_users': active_users,
        'users_past_7_days': users_past_7_days,
        'conversion_rate': round(conversion_rate, 1),
        
        'total_processed': total_processed,
        'success_rate': round(success_rate, 1),
        'fail_rate': round(fail_rate, 1),
        'successful_orders': successful_orders,
        'failed_orders': failed_orders,
        
        'total_tools': total_tools,
        'out_of_stock_tools': out_of_stock_tools,
        
        'top_tools': top_tools,
        'top_referrers': top_referrers,
        'recent_activity_logs': recent_activity_logs,
        
        # Chart Data
        'rev_labels': rev_labels,
        'rev_data': rev_data,
        'growth_labels': growth_labels,
        'growth_data': growth_data,
        'map_data': map_data,
        
        # Filter State
        'current_date_range': date_range,
        'current_country': country,
        'current_product': product_filter,
        'current_start_date': start_date_str,
        'current_end_date': end_date_str,
        
        # Filter Options
        'all_countries': all_countries,
        'all_tools': all_tools,
    }
    
    return render(request, 'analytics/dashboard.html', context)


@staff_member_required
def vendor_wallets_view(request):
    """
    Dedicated view for vendor wallets monitoring and API feedback logs.
    """
    from orders.models import OrderAPIRequest
    active_vendors = Vendor.objects.filter(is_active=True)
    vendor_data = []
    for v in active_vendors:
        latest_snapshot = v.balance_snapshots.first()
        tool_count = Tool.objects.filter(vendor_product__vendor=v).count()
        vendor_product_count = v.products.count()
        vendor_data.append({
            'id': v.id,
            'name': v.name,
            'balance': latest_snapshot.balance if latest_snapshot else 0.00,
            'last_updated': latest_snapshot.timestamp if latest_snapshot else None,
            'tool_count': tool_count,
            'vendor_product_count': vendor_product_count,
        })
        
    # Vendor API Requests Feedback Logs
    api_logs = OrderAPIRequest.objects.all().select_related('order__user', 'vendor', 'vendor_product').order_by('-created_at')[:50]
    failed_api_requests = OrderAPIRequest.objects.filter(status='failed').select_related('order__user', 'vendor', 'vendor_product').order_by('-created_at')[:50]
    failed_orders = Order.objects.filter(status='failed').select_related('user').order_by('-created_at')[:50]
        
    return render(request, 'analytics/vendor_wallets.html', {
        'vendor_data': vendor_data,
        'api_logs': api_logs,
        'failed_api_requests': failed_api_requests,
        'failed_orders': failed_orders
    })


@staff_member_required
def reload_vendor_balances(request):
    """
    AJAX endpoint to force fetch live vendor balances.
    """
    if request.method == 'POST':
        active_vendors = Vendor.objects.filter(is_active=True)
        results = []
        for vendor in active_vendors:
            try:
                service = get_vendor_service(vendor)
                balance = service.get_balance()
                VendorBalanceSnapshot.objects.create(vendor=vendor, balance=balance)
                results.append({
                    'id': vendor.id,
                    'name': vendor.name,
                    'balance': balance,
                    'status': 'success'
                })
            except Exception as e:
                results.append({
                    'id': vendor.id,
                    'name': vendor.name,
                    'error': str(e),
                    'status': 'error'
                })
        return JsonResponse({'success': True, 'data': results})
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)


@staff_member_required
def pull_vendor_products(request):
    """
    Manual trigger endpoint: Pull all products from all active vendor APIs.
    Updates VendorProduct table and syncs price/stock to any linked Tools.
    Called by the "Pull Products from Vendors" button on the Admin Analytics Dashboard.
    """
    if request.method == 'POST':
        from vendors.sync import sync_all_vendor_products
        try:
            result = sync_all_vendor_products(triggered_by=f"Admin Dashboard ({request.user})")
            return JsonResponse({
                'success': True,
                'total_created': result['total_created'],
                'total_updated': result['total_updated'],
                'total_tools_synced': result.get('total_tools_synced', 0),
                'details': result['details'],
                'errors': result.get('errors', []),
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)


@staff_member_required
def platform_wallet_view(request):
    """
    Platform Wallet for tracking inflow, outflow, and complex profit calculations.
    """
    from accounts.models import WithdrawalRequest
    from orders.models import OrderItem

    # 1. Total Inflow (from paid orders)
    paid_orders = Order.objects.filter(status='paid')
    total_inflow = paid_orders.aggregate(total=Sum('total_amount_ngn'))['total'] or 0.00
    total_inflow = float(total_inflow)

    # 2. Total Outflow (Referrer Payouts)
    approved_withdrawals = WithdrawalRequest.objects.filter(status='approved')
    total_outflow = approved_withdrawals.aggregate(total=Sum('amount'))['total'] or 0.00
    total_outflow = float(total_outflow)

    # 3. Vendor Costs & Breakdown
    paid_items = OrderItem.objects.filter(order__status='paid').select_related('tool__vendor_product__vendor', 'order')
    
    total_vendor_cost = 0.00
    vendor_breakdown = {}

    for item in paid_items:
        if not item.tool or not item.tool.vendor_product:
            continue
            
        v = item.tool.vendor_product.vendor
        if v.id not in vendor_breakdown:
            vendor_breakdown[v.id] = {
                'name': v.name,
                'total_sales_ngn': 0.0,
                'total_cost_ngn': 0.0,
                'items_sold': 0,
            }
            
        exchange_rate = item.order.exchange_rate or 1500.00
        vendor_price_usd = float(item.tool.vendor_product.price or 0)
        item_cost_ngn = vendor_price_usd * float(exchange_rate)
        
        # Add to global vendor cost
        total_vendor_cost += item_cost_ngn
        
        # Add to specific vendor
        vendor_breakdown[v.id]['total_cost_ngn'] += item_cost_ngn
        vendor_breakdown[v.id]['total_sales_ngn'] += float(item.price_ngn)
        vendor_breakdown[v.id]['items_sold'] += 1

    # Calculate profit per vendor
    vendor_breakdown_list = []
    for vid, data in vendor_breakdown.items():
        data['profit_ngn'] = data['total_sales_ngn'] - data['total_cost_ngn']
        data['margin'] = (data['profit_ngn'] / data['total_sales_ngn'] * 100) if data['total_sales_ngn'] > 0 else 0
        vendor_breakdown_list.append(data)

    # Sort breakdown by profit descending
    vendor_breakdown_list.sort(key=lambda x: x['profit_ngn'], reverse=True)

    # 4. Profit calculations
    gross_profit = total_inflow - total_vendor_cost
    net_profit = gross_profit - total_outflow

    # 5. Tables Data
    recent_orders = Order.objects.all().select_related('user').order_by('-created_at')[:50]
    payout_transactions = WithdrawalRequest.objects.all().select_related('user').order_by('-created_at')[:50]

    context = {
        'total_inflow': total_inflow,
        'total_outflow': total_outflow,
        'total_vendor_cost': total_vendor_cost,
        'gross_profit': gross_profit,
        'net_profit': net_profit,
        'vendor_breakdown': vendor_breakdown_list,
        'recent_orders': recent_orders,
        'payout_transactions': payout_transactions,
    }

    return render(request, 'analytics/platform_wallet.html', context)


@staff_member_required
def activity_logs_view(request):
    """
    Full Activity Logs & Audit Monitor view for staff/admins.
    Includes filtering by severity, action type, search query, and pagination.
    """
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from .models import ActivityLog

    logs_qs = ActivityLog.objects.all().select_related('user')

    # Filters
    severity_filter = request.GET.get('severity', '').strip()
    action_filter = request.GET.get('action_type', '').strip()
    search_q = request.GET.get('q', '').strip()

    if severity_filter:
        logs_qs = logs_qs.filter(severity=severity_filter)
    if action_filter:
        logs_qs = logs_qs.filter(action_type=action_filter)
    if search_q:
        logs_qs = logs_qs.filter(
            Q(title__icontains=search_q) |
            Q(details__icontains=search_q) |
            Q(user__email__icontains=search_q) |
            Q(ip_address__icontains=search_q)
        )

    # Statistics
    total_logs_count = ActivityLog.objects.count()
    error_count = ActivityLog.objects.filter(severity='error').count()
    warning_count = ActivityLog.objects.filter(severity='warning').count()
    success_count = ActivityLog.objects.filter(severity='success').count()

    # Pagination
    paginator = Paginator(logs_qs, 30) # 30 logs per page
    page = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    context = {
        'page_obj': page_obj,
        'logs': page_obj.object_list,
        'total_logs_count': total_logs_count,
        'error_count': error_count,
        'warning_count': warning_count,
        'success_count': success_count,
        'current_severity': severity_filter,
        'current_action': action_filter,
        'search_q': search_q,
        'action_choices': ActivityLog.ACTION_TYPES,
        'severity_choices': ActivityLog.SEVERITY_LEVELS,
    }

    return render(request, 'analytics/activity_logs.html', context)


@staff_member_required
def fund_user_wallet_api(request):
    """
    AJAX / Form endpoint for Admin to manually fund a user's wallet (Cash, POS, Bank Transfer).
    """
    if request.method == 'POST':
        import json
        import uuid
        from decimal import Decimal
        from django.contrib.auth import get_user_model
        from accounts.models import WalletTransaction
        from notifications.models import Notification
        from .models import ActivityLog

        User = get_user_model()
        data = request.POST if request.POST else (json.loads(request.body) if request.body else {})

        email = data.get('user_email', '').strip()
        amount_raw = data.get('amount_ngn', 0)
        currency = data.get('currency', 'NGN').strip().upper()
        source = data.get('payment_source', 'POS / Cash Transfer').strip()
        notes = data.get('notes', '').strip()

        if not email:
            return JsonResponse({'success': False, 'error': 'User email is required.'}, status=400)

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return JsonResponse({'success': False, 'error': f'No user account found with email "{email}".'}, status=404)

        try:
            amount = Decimal(str(amount_raw))
            if amount <= 0:
                return JsonResponse({'success': False, 'error': 'Funding amount must be greater than zero.'}, status=400)
        except Exception:
            return JsonResponse({'success': False, 'error': 'Invalid funding amount format.'}, status=400)

        from core.services import get_live_usd_rates
        rates = get_live_usd_rates() or {}
        ngn_rate = float(rates.get('NGN', 1500.0) or 1500.0)
        target_rate = float(rates.get(currency, 1.0) if currency != 'USD' else 1.0)

        if currency == 'NGN':
            amount_ngn = Decimal(str(round(float(amount), 2)))
        else:
            usd_val = float(amount) / target_rate
            amount_ngn = Decimal(str(round(usd_val * ngn_rate, 2)))

        profile = user.profile
        profile.wallet_balance += amount_ngn
        profile.save(update_fields=['wallet_balance'])

        from core.templatetags.currency_tags import CURRENCY_SYMBOLS
        symbol = CURRENCY_SYMBOLS.get(currency, currency)

        total_usd = float(profile.wallet_balance) / ngn_rate if ngn_rate else float(profile.wallet_balance) / 1500.0
        new_balance_converted = float(profile.wallet_balance) if currency == 'NGN' else (total_usd * target_rate)

        funded_str = f"{symbol} {float(amount):,.2f} {currency}"
        new_bal_str = f"{symbol} {new_balance_converted:,.2f} {currency}"

        ref = f"ADMIN_DEPOSIT_{uuid.uuid4().hex[:8].upper()}"
        desc = f"Manual Deposit ({source}) [{funded_str}]"
        if notes:
            desc += f": {notes}"

        WalletTransaction.objects.create(
            user=user,
            transaction_type='deposit',
            amount_ngn=amount_ngn,
            status='success',
            reference=ref,
            description=desc
        )

        ActivityLog.log(
            action_type='wallet_funding',
            title=f"Admin Funded Wallet for {user.email}",
            details=f"Amount: {funded_str} | Source: {source} | Admin: {request.user.email}",
            user=user,
            performed_by=request.user,
            severity='success'
        )

        Notification.objects.create(
            user=user,
            title="💰 Wallet Balance Credited",
            message=f"Your wallet balance has been credited with {funded_str} via {source}.",
            notification_type='payment',
            action_url="/dashboard/wallet/"
        )

        return JsonResponse({
            'success': True,
            'message': f"Successfully funded {funded_str} to {user.email}'s wallet. New balance: {new_bal_str}",
            'funded_amount_formatted': funded_str,
            'new_balance_formatted': new_bal_str,
            'new_balance': float(profile.wallet_balance)
        })

    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)


@staff_member_required
def refund_user_wallet_api(request):
    """
    AJAX / Form endpoint for Admin to issue a wallet refund to a user (e.g. for failed orders).
    """
    if request.method == 'POST':
        import json
        import uuid
        from decimal import Decimal
        from django.contrib.auth import get_user_model
        from orders.models import Order, RefundRequest
        from accounts.models import WalletTransaction
        from notifications.models import Notification
        from .models import ActivityLog

        User = get_user_model()
        data = request.POST if request.POST else (json.loads(request.body) if request.body else {})

        email = data.get('user_email', '').strip()
        order_id = data.get('order_id', '').strip()
        amount_raw = data.get('amount_ngn', 0)
        reason = data.get('reason', 'Order refund requested by admin').strip()

        order = None
        user = None

        if order_id:
            order = Order.objects.filter(id=order_id).first()
            if not order and str(order_id).startswith('OS-'):
                try:
                    num = int(str(order_id).replace('OS-', ''))
                    order = Order.objects.filter(id=num).first()
                except ValueError:
                    pass
            if order:
                user = order.user
                if not amount_raw or float(amount_raw) == 0:
                    amount_raw = order.total_amount_ngn

        if not user and email:
            user = User.objects.filter(email__iexact=email).first()

        if not user:
            return JsonResponse({'success': False, 'error': 'Target user or order not found.'}, status=404)

        try:
            amount = Decimal(str(amount_raw))
            if amount <= 0:
                return JsonResponse({'success': False, 'error': 'Refund amount must be greater than zero.'}, status=400)
        except Exception:
            return JsonResponse({'success': False, 'error': 'Invalid refund amount format.'}, status=400)

        profile = user.profile
        profile.wallet_balance += amount
        profile.save(update_fields=['wallet_balance'])

        if order:
            order.status = 'refunded'
            order.save(update_fields=['status'])
            rr = RefundRequest.objects.filter(order=order, status='pending').first()
            if rr:
                from django.utils import timezone
                rr.status = 'approved'
                rr.processed_at = timezone.now()
                rr.save()

        ref = f"REFUND_{order.order_number if order else uuid.uuid4().hex[:8].upper()}"
        desc = f"Wallet Refund"
        if order:
            desc += f" for Order #{order.order_number}"
        if reason:
            desc += f": {reason}"

        WalletTransaction.objects.create(
            user=user,
            transaction_type='refund',
            amount_ngn=amount,
            status='success',
            reference=ref,
            description=desc
        )

        ActivityLog.log(
            action_type='order_refunded',
            title=f"Wallet Refund Issued for {user.email}",
            details=f"Amount: NGN {amount:,.2f} | Reason: {reason} | Order: #{order.order_number if order else 'N/A'} | Admin: {request.user.email}",
            user=user,
            performed_by=request.user,
            severity='info'
        )

        Notification.objects.create(
            user=user,
            title="↩️ Wallet Refund Credited",
            message=f"A refund of NGN {amount:,.2f} has been credited back to your wallet balance.",
            notification_type='order',
            action_url="/dashboard/wallet/"
        )

        return JsonResponse({
            'success': True,
            'message': f"Successfully refunded NGN {amount:,.2f} to {user.email}'s wallet. New balance: NGN {profile.wallet_balance:,.2f}",
            'new_balance': float(profile.wallet_balance)
        })

    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)


@staff_member_required
def buy_tool_for_user_api(request):
    """
    AJAX / Form endpoint for Admin to purchase a tool on behalf of a user.
    Can use the user's wallet balance or mark as Complimentary Admin Gift.
    Automatically executes vendor API purchase, updates access_details, and sends email/in-app notification.
    """
    if request.method == 'POST':
        import json
        import logging
        from decimal import Decimal
        from django.contrib.auth import get_user_model
        from products.models import Tool
        from orders.models import Order, OrderItem, PaymentTransaction
        from accounts.models import WalletTransaction
        from vendors.tasks import _fulfill_order_logic
        from orders.delivery import trigger_delivery
        from notifications.models import Notification
        from .models import ActivityLog

        logger = logging.getLogger(__name__)
        User = get_user_model()
        data = request.POST if request.POST else (json.loads(request.body) if request.body else {})

        email = data.get('user_email', '').strip()
        tool_id = data.get('tool_id')
        payment_method = data.get('payment_method', 'wallet').strip()

        if not email:
            return JsonResponse({'success': False, 'error': 'User email is required.'}, status=400)
        if not tool_id:
            return JsonResponse({'success': False, 'error': 'Tool selection is required.'}, status=400)

        user = User.objects.filter(email__iexact=email).first()

        tool = Tool.objects.filter(id=tool_id, is_active=True).first()
        if not tool:
            return JsonResponse({'success': False, 'error': 'Selected tool is invalid or inactive.'}, status=404)

        price_ngn = Decimal(str(round(tool.get_ngn_price(), 2)))

        import uuid
        claim_token = None

        if not user:
            if payment_method == 'wallet':
                return JsonResponse({
                    'success': False,
                    'error': f'No account found with email "{email}". Please select "🎁 Complimentary Admin Gift / Cash Paid Direct" to purchase for an unregistered customer.'
                }, status=400)

            claim_token = f"CLAIM_{uuid.uuid4().hex}"
            order = Order.objects.create(
                user=None,
                claim_token=claim_token,
                total_amount_ngn=price_ngn,
                local_currency='NGN',
                local_amount=price_ngn,
                exchange_rate=Decimal('1500.00'),
                delivery_email=email,
                status='paid',
            )
        else:
            profile = user.profile
            if payment_method == 'wallet':
                if profile.wallet_balance < price_ngn:
                    return JsonResponse({
                        'success': False,
                        'error': f"User has insufficient wallet balance (Bal: NGN {profile.wallet_balance:,.2f}, Tool Price: NGN {price_ngn:,.2f}). Please fund user's wallet first or select Complimentary Admin Gift."
                    }, status=400)

                profile.wallet_balance -= price_ngn
                profile.save(update_fields=['wallet_balance'])

                WalletTransaction.objects.create(
                    user=user,
                    transaction_type='purchase',
                    amount_ngn=price_ngn,
                    status='success',
                    reference=f"ADMIN_BUY_{tool.id}",
                    description=f"Purchased {tool.name} (Admin Purchase)"
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
            gateway='wallet' if (user and payment_method == 'wallet') else 'manual',
            transaction_id=f"ADMIN_PAY_{order.id}",
            reference=f"ADMIN_PAY_{order.id}",
            status='success',
            amount_paid=price_ngn,
            currency_paid='NGN',
        )

        ActivityLog.log(
            action_type='wallet_purchase',
            title=f"Admin Purchased {tool.name} for {email}",
            details=f"Order #{order.order_number} | Amount: NGN {price_ngn:,.2f} | Payment: {payment_method.title()} | Admin: {request.user.email} | User Registered: {bool(user)}",
            user=user,
            performed_by=request.user,
            severity='success'
        )

        try:
            _fulfill_order_logic(order.id)
            order.refresh_from_db()
        except Exception as ve:
            logger.error(f"Admin purchase vendor fulfillment error for Order #{order.id}: {ve}")

        trigger_delivery(order)

        claim_url = None
        if not user and claim_token:
            from core.models import SiteSettings
            cfg = SiteSettings.get()
            base_site_url = (cfg.site_url or 'https://onesolai.com').rstrip('/')
            claim_url = f"{base_site_url}/auth/signup/?claim_token={claim_token}&email={email}"
            
            try:
                from core.email_utils import send_async_email
                sub = f"🎁 Action Required: Claim your {tool.name} Access on {cfg.site_name or 'OneSol AI Hub'}"
                msg = f"Hello,\n\nAn order for {tool.name} has been processed for your email address.\n\nPlease register your account using the link below to view your activation credentials in your dashboard:\n{claim_url}\n\nThank you,\n{cfg.site_name or 'OneSol AI Hub'} Team"
                html_msg = f"""
                <div style="font-family: Arial, sans-serif; background: #0b0f29; color: #ffffff; padding: 30px; border-radius: 12px; max-width: 550px; margin: 0 auto;">
                    <h2 style="color: #6366F1; margin-top: 0;">🎁 {tool.name} Purchased For You!</h2>
                    <p style="color: #aeb5ca; font-size: 15px; line-height: 1.6;">
                        An order for <strong>{tool.name}</strong> has been processed for your email address.
                    </p>
                    <div style="background: #161b40; padding: 20px; border-radius: 10px; margin: 20px 0; border: 1px solid rgba(255,255,255,0.1);">
                        <p style="margin: 0 0 10px 0; font-size: 14px; color: #aeb5ca;">Click the button below to create your free account and access your product credentials instantly in your User Dashboard:</p>
                        <div style="text-align: center; margin-top: 15px;">
                            <a href="{claim_url}" style="background: linear-gradient(135deg, #6366f1, #4f46e5); color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: bold; display: inline-block;">Create Account &amp; Claim Credentials</a>
                        </div>
                    </div>
                    <p style="color: #6b7280; font-size: 12px;">Or copy &amp; paste this URL in your browser: <br><a href="{claim_url}" style="color: #8c9eff;">{claim_url}</a></p>
                </div>
                """
                send_async_email(sub, msg, [email], html_message=html_msg)
            except Exception as em_err:
                logger.error(f"Failed to send claim email to {email}: {em_err}")

        return JsonResponse({
            'success': True,
            'order_id': order.id,
            'order_number': order.order_number,
            'is_new_user': not bool(user),
            'claim_url': claim_url,
            'message': f"Successfully purchased {tool.name} for {email}! Order #{order.order_number} processed." + (f" Registration link generated." if claim_url else "")
        })

    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)

