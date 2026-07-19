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
    context = {
        'tool': tool,
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
        })

    return JsonResponse({'tools': data})
