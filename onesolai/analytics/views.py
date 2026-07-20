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
    Dedicated view for vendor wallets monitoring.
    """
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
        
    # Failed Transactions
    failed_orders = Order.objects.filter(status='failed').select_related('user').order_by('-created_at')[:50]
        
    return render(request, 'analytics/vendor_wallets.html', {
        'vendor_data': vendor_data,
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
