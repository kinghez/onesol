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


def api_tools_json(request):
    """API endpoint returning tools as JSON for the JS carousels on the home page."""
    tools = Tool.objects.filter(is_active=True).select_related('category')

    # Optional filter: featured or popular
    filter_type = request.GET.get('filter', 'featured')
    if filter_type == 'featured':
        tools = tools.filter(is_featured=True)
    elif filter_type == 'popular':
        tools = tools.filter(is_popular=True)
    # filter_type == 'all' returns all active tools (no extra filter)

    category_filter = request.GET.get('category')
    if category_filter and category_filter != 'all':
        tools = tools.filter(category__name=category_filter)

    # Slice logic: only limit for carousels, not for 'all'
    if filter_type != 'all':
        tools = tools[:20]

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
