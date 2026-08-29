import logging
import traceback
import json

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Tool, Category

# Dedicated logger for the tools page — shows up in Django's runserver output
logger = logging.getLogger('products.tools')


def tools_list(request):
    """
    Render the all-tools listing page.
    Uses Django's Paginator (server-side) – no JS grid injection, no race conditions.
    Detailed logging is active so any error will appear in the console.
    """
    logger.info("=== tools_list called | user=%s | GET=%s ===", getattr(request, 'user', 'Anonymous'), dict(request.GET))

    # ── 1. Fetch & validate categories ──────────────────────────────────────
    try:
        categories = list(Category.objects.all().order_by('order', 'name'))
        logger.info("Categories loaded: %d", len(categories))
    except Exception as exc:
        logger.error("ERROR loading categories: %s\n%s", exc, traceback.format_exc())
        categories = []

    # ── 2. Base queryset ─────────────────────────────────────────────────────
    try:
        qs = Tool.objects.in_stock().select_related('category', 'vendor_product')
        total_all = qs.count()
        logger.info("Active tools in DB (total): %d", total_all)
    except Exception as exc:
        logger.error("ERROR building base queryset: %s\n%s", exc, traceback.format_exc())
        qs = Tool.objects.none()
        total_all = 0

    # ── 3. Category filter ───────────────────────────────────────────────────
    category_slug = request.GET.get('category', '').strip()
    active_category = None
    if category_slug:
        try:
            active_category = Category.objects.get(slug=category_slug)
            qs = qs.filter(category=active_category)
            logger.info("Filtered by category slug=%s → %s", category_slug, active_category.name)
        except Category.DoesNotExist:
            logger.warning("Category slug '%s' not found, ignoring filter", category_slug)
        except Exception as exc:
            logger.error("ERROR in category filter: %s\n%s", exc, traceback.format_exc())

    # ── 4. Search ────────────────────────────────────────────────────────────
    q = request.GET.get('q', '').strip()
    if q:
        try:
            from django.db.models import Q
            qs = qs.filter(Q(name__icontains=q) | Q(short_description__icontains=q) | Q(description__icontains=q))
            logger.info("Search q='%s' applied", q)
        except Exception as exc:
            logger.error("ERROR in search filter: %s\n%s", exc, traceback.format_exc())

    # ── 5. Popular-only checkbox ─────────────────────────────────────────────
    popular_only = bool(request.GET.get('popular_only'))
    if popular_only:
        qs = qs.filter(is_popular=True)
        logger.info("popular_only filter applied")

    # ── 6. Evaluate queryset & compute prices ────────────────────────────────
    try:
        tools_list_qs = list(qs)
        filtered_total = len(tools_list_qs)
        logger.info("Queryset evaluated: %d tools after filters", filtered_total)
    except Exception as exc:
        logger.error("ERROR evaluating queryset: %s\n%s", exc, traceback.format_exc())
        tools_list_qs = []
        filtered_total = 0

    # Attach computed prices — use non-underscore names so Django templates can access them
    for tool in tools_list_qs:
        try:
            tool.price_ngn_display = tool.get_ngn_price()
            tool.price_usd_display = tool.get_usd_price()
        except Exception as exc:
            logger.warning("Price calc failed for tool id=%s '%s': %s", tool.id, tool.name, exc)
            tool.price_ngn_display = 0.0
            tool.price_usd_display = 0.0

    # ── 7. Sort tools accurately by computed price / criteria ────────────────
    sort = request.GET.get('sort', 'newest').strip().lower()
    try:
        if sort == 'price_asc':
            tools_list_qs.sort(key=lambda t: t.price_usd_display)
        elif sort == 'price_desc':
            tools_list_qs.sort(key=lambda t: t.price_usd_display, reverse=True)
        elif sort == 'name_asc':
            tools_list_qs.sort(key=lambda t: t.name.lower())
        elif sort == 'name_desc':
            tools_list_qs.sort(key=lambda t: t.name.lower(), reverse=True)
        elif sort == 'popular':
            tools_list_qs.sort(key=lambda t: (not t.is_popular, not t.is_featured, t.name.lower()))
        else: # newest (default)
            tools_list_qs.sort(key=lambda t: t.created_at, reverse=True)
        logger.info("Sort applied successfully: sort=%s", sort)
    except Exception as exc:
        logger.error("ERROR applying sort: %s\n%s", exc, traceback.format_exc())

    # ── 8. Pagination ────────────────────────────────────────────────────────
    PAGE_SIZE = 12
    paginator = Paginator(tools_list_qs, PAGE_SIZE)
    page_param = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_param)
    except PageNotAnInteger:
        logger.warning("page param '%s' is not an integer, defaulting to page 1", page_param)
        page_obj = paginator.page(1)
    except EmptyPage:
        logger.warning("page param '%s' is out of range, defaulting to last page", page_param)
        page_obj = paginator.page(paginator.num_pages)

    logger.info(
        "Pagination: page=%s of %s | PAGE_SIZE=%d | items_on_page=%d",
        page_obj.number, paginator.num_pages, PAGE_SIZE, len(page_obj.object_list)
    )

    # ── 9. Page range helper (e.g. for numbered buttons) ────────────────────
    # Show at most 5 page number buttons around current page
    current = page_obj.number
    total_pages = paginator.num_pages
    half = 2
    page_range_start = max(1, current - half)
    page_range_end = min(total_pages, current + half)
    # Expand if near start/end
    if page_range_end - page_range_start < 4:
        if page_range_start == 1:
            page_range_end = min(total_pages, 5)
        elif page_range_end == total_pages:
            page_range_start = max(1, total_pages - 4)
    page_range = list(range(page_range_start, page_range_end + 1))

    # ── 10. Wishlist IDs (for authenticated users) ───────────────────────────
    wishlist_ids = set()
    if request.user.is_authenticated:
        try:
            from .models import Wishlist
            wishlist_ids = set(
                Wishlist.objects.filter(user=request.user)
                .values_list('tool_id', flat=True)
            )
            logger.info("Wishlist IDs for user %s: %s", request.user, wishlist_ids)
        except Exception as exc:
            logger.error("ERROR fetching wishlist: %s\n%s", exc, traceback.format_exc())

    # Tag tools on current page with wishlist flag (non-underscore so Django template can read it)
    for tool in page_obj.object_list:
        tool.in_wishlist_flag = tool.id in wishlist_ids

    # ── 11. Build context ────────────────────────────────────────────────────
    context = {
        'page_obj': page_obj,
        'paginator': paginator,
        'page_range': page_range,
        'total_all': total_all,           # Total active tools in DB (unfiltered)
        'filtered_total': filtered_total, # Tools matching current filters
        'categories': categories,
        'active_category': active_category,
        'sort': sort,
        'q': q,
        'popular_only': popular_only,
        'page_size': PAGE_SIZE,
        'hide_header_footer': request.user.is_authenticated,
    }

    logger.info("=== tools_list rendering complete, context keys: %s ===", list(context.keys()))
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
    Top 10 most recent items purchased on platform or added to tool table that are in stock.
    If recently purchased items < limit, complete list with recently added in-stock tools.
    """
    from orders.models import OrderItem
    base_qs = Tool.objects.in_stock().select_related('category', 'vendor_product')
    if category_name and category_name != 'all':
        base_qs = base_qs.filter(category__name__iexact=category_name.strip())

    base_tools = [t for t in base_qs if t.is_in_stock]
    in_stock_ids = [t.id for t in base_tools]
    base_dict = {t.id: t for t in base_tools}

    purchased_ids = []
    order_items = (
        OrderItem.objects.filter(order__status='paid', tool_id__in=in_stock_ids)
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
        recent_in_stock = [t for t in base_tools if t.id not in purchased_ids]
        recent_in_stock.sort(key=lambda t: t.created_at, reverse=True)
        recent_ids = [t.id for t in recent_in_stock[:needed]]
        popular_ids = purchased_ids + recent_ids
    else:
        popular_ids = purchased_ids[:limit]

    return [base_dict[tid] for tid in popular_ids if tid in base_dict]


def get_cheapest_tools(limit=10, category_name=None):
    """
    Automated Top & Best Selling Tools selection:
    Top 10 cheapest tools in the tool table that are currently in stock.
    """
    base_qs = Tool.objects.in_stock().select_related('category', 'vendor_product')
    if category_name and category_name != 'all':
        base_qs = base_qs.filter(category__name__iexact=category_name.strip())

    tools = [t for t in base_qs if t.is_in_stock]
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
        tools_qs = Tool.objects.in_stock().select_related('category', 'vendor_product')
        if category_filter and category_filter != 'all':
            tools_qs = tools_qs.filter(category__name__iexact=category_filter.strip())
        tools = [t for t in tools_qs if t.is_in_stock]

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
