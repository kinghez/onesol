from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Tool, Category


def tools_list(request):
    """Render the all-tools listing page with real DB data."""
    tools = Tool.objects.filter(is_active=True).select_related('category')
    categories = Category.objects.all()

    # Filter by category slug
    category_slug = request.GET.get('category')
    active_category = None
    if category_slug:
        try:
            active_category = Category.objects.get(slug=category_slug)
            tools = tools.filter(category=active_category)
        except Category.DoesNotExist:
            pass

    # Filter popular only
    if request.GET.get('popular_only'):
        tools = tools.filter(is_popular=True)

    # Sort
    sort = request.GET.get('sort', 'popular')
    sort_map = {
        'price_asc': 'sell_price_usd',
        'price_desc': '-sell_price_usd',
        'newest': '-created_at',
        'popular': '-is_popular',
    }
    tools = tools.order_by(sort_map.get(sort, '-is_popular'))

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        tools = tools.filter(name__icontains=q) | tools.filter(description__icontains=q)

    import json

    # Pre-serialize tools for JS
    tools_data = []
    for tool in tools:
        tools_data.append({
            'id': tool.id,
            'name': tool.name,
            'slug': tool.slug,
            'category': tool.category.name,
            'description': tool.short_description or tool.description[:150],
            'image_url': tool.image_url or '',
            'developer': tool.developer,
            'base_price_usd': tool.get_usd_price(),
            'price_ngn': tool.get_ngn_price(),
            'in_stock': tool.is_in_stock,
            'is_new': tool.is_new,
            'is_popular': tool.is_popular,
            'is_featured': tool.is_featured,
            'badge': ('Best Seller' if tool.is_featured and tool.is_popular else
                      'Popular' if tool.is_popular else
                      'New' if tool.is_new else None),
            'rating': float(tool.rating),
            'review_count': tool.review_count,
            'users_count': tool.users_count,
            'detail_url': f'/tools/{tool.slug}/',
        })

    context = {
        'tools': tools,
        'tools_json': json.dumps(tools_data),
        'categories': categories,
        'active_category': active_category,
        'sort': sort,
        'q': q,
        'hide_header_footer': request.user.is_authenticated,
    }
    return render(request, 'tools/tools.html', context)


def tool_detail(request, slug):
    """Render a single tool's detail page."""
    tool = get_object_or_404(
        Tool.objects.filter(is_active=True)
        .select_related('category')
        .prefetch_related('screenshots', 'features', 'faqs', 'reviews'),
        slug=slug
    )
    in_wishlist = False
    if request.user.is_authenticated:
        from .models import Wishlist
        in_wishlist = Wishlist.objects.filter(user=request.user, tool=tool).exists()

    context = {
        'tool': tool,
        'in_wishlist': in_wishlist,
        'related_tools': Tool.objects.filter(
            category=tool.category, is_active=True
        ).exclude(pk=tool.pk)[:4],
        'hide_header_footer': request.user.is_authenticated,
    }
    return render(request, 'tools/tool_detail.html', context)


def get_popular_tools(limit=10, category_name=None):
    """
    Automated Popular Tools selection:
    Top 10 most recent items purchased on platform or added to tool table.
    If recently purchased items < limit, complete list with recently added tools.
    """
    from orders.models import OrderItem
    base_qs = Tool.objects.filter(is_active=True).select_related('category', 'vendor_product')
    if category_name and category_name != 'all':
        base_qs = base_qs.filter(category__name__iexact=category_name.strip())

    purchased_ids = []
    order_items = (
        OrderItem.objects.filter(order__status='paid', tool__in=base_qs)
        .order_by('-order__created_at')
        .select_related('tool')
    )
    for item in order_items:
        if item.tool_id and item.tool_id not in purchased_ids:
            purchased_ids.append(item.tool_id)
            if len(purchased_ids) >= limit:
                break

    needed = limit - len(purchased_ids)
    if needed > 0:
        recent_ids = list(
            base_qs.exclude(id__in=purchased_ids)
            .order_by('-created_at')
            .values_list('id', flat=True)[:needed]
        )
        popular_ids = purchased_ids + recent_ids
    else:
        popular_ids = purchased_ids[:limit]

    tools_dict = {t.id: t for t in base_qs.filter(id__in=popular_ids)}
    return [tools_dict[tid] for tid in popular_ids if tid in tools_dict]


def get_cheapest_tools(limit=10, category_name=None):
    """
    Automated Top & Best Selling Tools selection:
    Top 10 cheapest tools in the tool table.
    """
    base_qs = Tool.objects.filter(is_active=True).select_related('category', 'vendor_product')
    if category_name and category_name != 'all':
        base_qs = base_qs.filter(category__name__iexact=category_name.strip())

    tools = list(base_qs)
    tools.sort(key=lambda t: t.get_usd_price())
    return tools[:limit]


def api_tools_json(request):
    """API endpoint returning tools as JSON for the JS carousels on the home page."""
    filter_type = request.GET.get('filter', 'featured')
    category_filter = request.GET.get('category')

    if filter_type == 'popular':
        tools = get_popular_tools(limit=10, category_name=category_filter)
    elif filter_type == 'featured':
        tools = get_cheapest_tools(limit=10, category_name=category_filter)
    else:
        tools = Tool.objects.filter(is_active=True).select_related('category')
        if category_filter and category_filter != 'all':
            tools = tools.filter(category__name__iexact=category_filter.strip())

    # Get user wishlisted tool IDs if authenticated
    user_wishlist_ids = set()
    if request.user.is_authenticated:
        from .models import Wishlist
        user_wishlist_ids = set(Wishlist.objects.filter(user=request.user).values_list('tool_id', flat=True))

    data = []
    for tool in tools:
        data.append({
            'id': tool.id,
            'name': tool.name,
            'slug': tool.slug,
            'category': tool.category.name,
            'description': tool.short_description or tool.description[:150],
            'image_url': tool.image_url or '',
            'developer': tool.developer,
            'base_price_usd': tool.get_usd_price(),
            'price_ngn': tool.get_ngn_price(),
            'in_stock': tool.is_in_stock,
            'is_new': tool.is_new,
            'is_popular': tool.is_popular,
            'is_featured': tool.is_featured,
            'badge': ('Best Seller' if tool.is_featured and tool.is_popular else
                      'Popular' if tool.is_popular else
                      'New' if tool.is_new else None),
            'rating': float(tool.rating),
            'review_count': tool.review_count,
            'users_count': tool.users_count,
            'detail_url': f'/tools/{tool.slug}/',
            'in_wishlist': tool.id in user_wishlist_ids,
        })

    return JsonResponse({'tools': data})


from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import redirect


@login_required(login_url='/auth/login/')
@require_POST
def toggle_wishlist(request):
    """
    POST: tool_id or tool_slug
    Toggles a tool in the user's wishlist.
    """
    from .models import Wishlist
    tool_id = request.POST.get('tool_id')
    tool_slug = request.POST.get('tool_slug')

    if tool_id:
        tool = get_object_or_404(Tool, id=tool_id, is_active=True)
    elif tool_slug:
        tool = get_object_or_404(Tool, slug=tool_slug, is_active=True)
    else:
        return JsonResponse({'status': 'error', 'message': 'Tool ID or slug required.'}, status=400)

    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, tool=tool)
    if not created:
        wishlist_item.delete()
        in_wishlist = False
        msg = f"{tool.name} removed from your Wishlist."
    else:
        in_wishlist = True
        msg = f"{tool.name} added to your Wishlist!"

    count = Wishlist.objects.filter(user=request.user).count()

    accept_header = request.headers.get('Accept', '')
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in accept_header or 'text/html' not in accept_header
    if is_ajax:
        return JsonResponse({
            'status': 'success',
            'in_wishlist': in_wishlist,
            'message': msg,
            'wishlist_count': count,
        })

    from django.contrib import messages
    messages.success(request, msg)
    return redirect(request.META.get('HTTP_REFERER', '/dashboard/wishlist/'))
