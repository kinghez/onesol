from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from orders.models import Order, OrderItem


@login_required(login_url='/auth/login/')
def dashboard_home(request):
    """Main dashboard view with real DB data."""
    user = request.user

    # Fetch real data
    orders = Order.objects.filter(user=user).select_related('payment')
    paid_orders = orders.filter(status='paid')
    recent_orders = paid_orders[:5]

    # Active subscriptions = items from paid orders
    recent_subscriptions = (
        OrderItem.objects
        .filter(order__user=user, order__status='paid')
        .select_related('tool', 'plan')
        .order_by('-order__created_at')[:4]
    )

    # Wallet & earnings from profile
    wallet_balance = '0.00'
    referral_earnings = '0.00'
    try:
        profile = user.profile
        wallet_balance = f"{profile.wallet_balance:,.2f}"
        referral_earnings = f"{profile.earnings:,.2f}"
    except Exception:
        pass

    context = {
        'active_subscriptions_count': recent_subscriptions.count(),
        'total_orders_count': paid_orders.count(),
        'referral_earnings': referral_earnings,
        'wallet_balance': wallet_balance,
        'recent_subscriptions': recent_subscriptions,
        'recent_orders': recent_orders,
    }
    return render(request, 'dashboard/dashboard.html', context)


from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.http import Http404

@login_required(login_url='/auth/login/')
def subscriptions(request):
    """Subscriptions management view with real data."""
    user = request.user

    all_items = (
        OrderItem.objects
        .filter(order__user=user, order__status='paid')
        .select_related('tool', 'plan', 'order')
        .order_by('-order__created_at')
    )
    
    now = timezone.now()
    active_subs = []
    expired_subs = []
    
    for item in all_items:
        if item.expires_at and item.expires_at < now:
            expired_subs.append(item)
        else:
            active_subs.append(item)

    # Calculate days remaining for active subs for the ring UI
    for item in active_subs:
        if item.expires_at:
            delta = item.expires_at - now
            item.days_remaining = max(0, delta.days)
            item.total_days = item.duration_days or 30
            item.progress_percent = max(0, min(100, (item.days_remaining / item.total_days) * 100))
        else:
            item.days_remaining = 30
            item.progress_percent = 100

    context = {
        'active_subscriptions': active_subs,
        'expired_subscriptions': expired_subs,
        'active_count': len(active_subs),
        'expired_count': len(expired_subs),
    }
    return render(request, 'dashboard/subscriptions.html', context)


@login_required(login_url='/auth/login/')
def order_history_view(request):
    """Premium order history page."""
    user = request.user
    status_filter = request.GET.get('status', 'all').lower()
    
    orders_qs = Order.objects.filter(user=user).order_by('-created_at')
    
    if status_filter in ['paid', 'pending', 'failed', 'refunded']:
        orders_qs = orders_qs.filter(status=status_filter)
        
    context = {
        'orders': orders_qs,
        'current_status': status_filter,
        'has_orders': Order.objects.filter(user=user).exists()
    }
    return render(request, 'dashboard/orders.html', context)


@login_required(login_url='/auth/login/')
def order_detail_view(request, order_id):
    """View to fetch a single order's details via AJAX or full page."""
    user = request.user
    order = get_object_or_404(Order, id=order_id, user=user)
    
    context = {
        'order': order,
        'items': order.items.all()
    }
    return render(request, 'dashboard/partials/order_detail.html', context)

