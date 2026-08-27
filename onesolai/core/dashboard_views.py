from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from orders.models import Order, OrderItem


@login_required(login_url='/auth/login/')
def dashboard_home(request):
    """Main dashboard view with Popular Tools & Recommended Tools for the user."""
    user = request.user
    from products.models import Tool

    # Wallet & earnings from profile
    wallet_balance = '0.00'
    referral_earnings = '0.00'
    try:
        profile = user.profile
        wallet_balance = f"{profile.wallet_balance:,.2f}"
        referral_earnings = f"{profile.earnings:,.2f}"
    except Exception:
        pass

    # Fetch active tools for calculations
    all_tools = list(
        Tool.objects.filter(is_active=True)
        .select_related('category', 'vendor_product')
    )

    for t in all_tools:
        try:
            t.price_ngn_display = t.get_ngn_price()
            t.price_usd_display = t.get_usd_price()
        except Exception:
            t.price_ngn_display = 0.0
            t.price_usd_display = 0.0

    # 1. Popular Tools: sorted by popular flag, featured flag, and cheapest USD price (in stock only)
    in_stock_tools = [t for t in all_tools if t.is_in_stock]
    popular_tools = sorted(
        in_stock_tools,
        key=lambda t: (not t.is_popular, not t.is_featured, t.price_usd_display)
    )[:5]

    # 2. Recommended For You: based on user wishlist categories, purchased categories, or top featured tools
    from products.models import Wishlist

    wishlist_tool_ids = set(
        Wishlist.objects.filter(user=user).values_list('tool_id', flat=True)
    )
    wishlist_category_ids = set(
        Wishlist.objects.filter(user=user, tool__category__isnull=False).values_list('tool__category_id', flat=True)
    )

    purchased_category_ids = set(
        OrderItem.objects
        .filter(order__user=user, order__status='paid', tool__isnull=False)
        .values_list('tool__category_id', flat=True)
    )

    bought_tool_ids = set(
        OrderItem.objects
        .filter(order__user=user, order__status='paid', tool__isnull=False)
        .values_list('tool_id', flat=True)
    )

    recommended_list = []
    seen_ids = set()

    # Priority A: Top cheapest products in same categories as tools in user's wishlist
    if wishlist_category_ids:
        wishlist_cat_tools = [
            t for t in all_tools 
            if t.category_id in wishlist_category_ids 
            and t.id not in bought_tool_ids 
            and t.id not in wishlist_tool_ids
        ]
        wishlist_cat_tools.sort(key=lambda t: t.price_usd_display)
        for t in wishlist_cat_tools:
            if t.id not in seen_ids:
                recommended_list.append(t)
                seen_ids.add(t.id)

    # Priority B: Products from categories user previously purchased
    if purchased_category_ids:
        purchased_cat_tools = [
            t for t in all_tools 
            if t.category_id in purchased_category_ids 
            and t.id not in bought_tool_ids 
            and t.id not in seen_ids
        ]
        purchased_cat_tools.sort(key=lambda t: (not t.is_featured, t.price_usd_display))
        for t in purchased_cat_tools:
            if t.id not in seen_ids:
                recommended_list.append(t)
                seen_ids.add(t.id)

    # Priority C: Fill remaining slots with top featured / rated / popular tools
    fallback_tools = sorted(
        [t for t in all_tools if t.id not in bought_tool_ids and t.id not in seen_ids],
        key=lambda t: (not t.is_featured, -t.rating, t.price_usd_display)
    )
    for t in fallback_tools:
        if t.id not in seen_ids:
            recommended_list.append(t)
            seen_ids.add(t.id)

    recommended_tools = recommended_list[:5]

    context = {
        'profile': profile,
        'referral_earnings': referral_earnings,
        'wallet_balance': wallet_balance,
        'popular_tools': popular_tools,
        'recommended_tools': recommended_tools,
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
        .select_related('tool', 'order')
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


@login_required(login_url='/auth/login/')
def wishlist_view(request):
    """Render user wishlist page in dashboard."""
    from products.models import Wishlist
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('tool', 'tool__category')
    return render(request, 'dashboard/wishlist.html', {
        'wishlist_items': wishlist_items,
        'wishlist_count': wishlist_items.count(),
    })

