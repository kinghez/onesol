from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Tool, ToolScreenshot, ToolFeature, ToolFAQ, ToolReview


# ─────────────────────────────────────────────
#  Inlines for Tool admin
# ─────────────────────────────────────────────
# Removed SubscriptionPlanInline

class ToolScreenshotInline(admin.TabularInline):
    model = ToolScreenshot
    extra = 1

class ToolFeatureInline(admin.TabularInline):
    model = ToolFeature
    extra = 1

class ToolFAQInline(admin.TabularInline):
    model = ToolFAQ
    extra = 1

class ToolReviewInline(admin.TabularInline):
    model = ToolReview
    extra = 1


# ─────────────────────────────────────────────
#  Category Admin
# ─────────────────────────────────────────────
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon', 'tool_count', 'order')
    list_editable = ('order',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('order', 'name')

    @admin.display(description='Tools')
    def tool_count(self, obj):
        return obj.tools.count()


# ─────────────────────────────────────────────
#  Tool Admin
# ─────────────────────────────────────────────
@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = (
        'logo_preview', 'name', 'category', 'vendor_name', 'vendor_price_usd', 'get_sell_price_usd', 'get_stock',
        'is_featured', 'is_active', 'updated_at'
    )
    list_display_links = ('logo_preview', 'name')
    list_filter = ('category', 'is_featured', 'is_active')
    list_editable = ('is_featured', 'is_active')
    search_fields = ('name', 'description', 'developer')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at', 'logo_preview_large')
    ordering = ('-is_featured', '-is_popular', 'name')
    inlines = [
        ToolScreenshotInline,
        ToolFeatureInline,
        ToolFAQInline,
        ToolReviewInline
    ]
    actions = ['refine_tools_with_ai']

    @admin.action(description="🤖 Refine selected tools with AI (OpenRouter)")
    def refine_tools_with_ai(self, request, queryset):
        from core.ai_service import refine_product_copy
        from django.contrib import messages
        
        refined_count = 0
        failed_count = 0
        
        for tool in queryset:
            raw_name = tool.vendor_product.name if tool.vendor_product else tool.name
            raw_desc = tool.vendor_product.description if tool.vendor_product else tool.description
            
            refined = refine_product_copy(raw_name, raw_desc)
            if refined:
                tool.name = refined.get('name', tool.name)
                tool.short_description = refined.get('short_description', tool.short_description)
                tool.description = refined.get('description', tool.description)
                tool.save()
                refined_count += 1
            else:
                failed_count += 1
                
        if refined_count > 0:
            messages.success(request, f"Successfully refined {refined_count} tools using AI.")
        if failed_count > 0:
            messages.warning(request, f"Failed to refine {failed_count} tools. Check API key and rate limits.")

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name', 'slug', 'category', 'developer',
                'description', 'short_description',
            )
        }),
        ('Pricing & Vendor Link', {
            'fields': ('vendor_product', 'markup_percent', 'markup_fixed_usd', 'sell_price_usd', 'is_manual_price'),
            'description': 'Leave markup fields at 0 to use global defaults. Set sell_price_usd and check is_manual_price to hardcode a price.'
        }),
        ('Display & Media', {
            'fields': ('image_url', 'logo_preview_large', 'users_count', 'rating', 'review_count')
        }),
        ('Status Flags', {
            'fields': ('is_active', 'is_featured', 'is_popular', 'is_new')
        }),
        ('Tab Visibility Controls', {
            'fields': ('show_overview_tab', 'show_features_tab', 'show_reviews_tab', 'show_faqs_tab')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Logo')
    def logo_preview(self, obj):
        if obj.image_url:
            return format_html(
                '<img src="{}" style="width:32px;height:32px;object-fit:contain;border-radius:6px;" />',
                obj.image_url
            )
        return '—'

    @admin.display(description='Logo')
    def logo_preview_large(self, obj):
        if obj.image_url:
            return format_html(
                '<img src="{}" style="width:64px;height:64px;object-fit:contain;border-radius:8px;'
                'background:#1a1a2e;padding:4px;" />',
                obj.image_url
            )
        return '—'

    @admin.display(description='Vendor')
    def vendor_name(self, obj):
        return obj.vendor_product.vendor.name if obj.vendor_product else '—'

    @admin.display(description='Vendor Price ($)')
    def vendor_price_usd(self, obj):
        return obj.vendor_product.price if obj.vendor_product and obj.vendor_product.price else '—'

    @admin.display(description='Sell Price ($)')
    def get_sell_price_usd(self, obj):
        return obj.get_usd_price()

    @admin.display(description='Stock')
    def get_stock(self, obj):
        if obj.vendor_product:
            stock = obj.vendor_product.stock
            if stock.lower() in ['0', 'none', 'out of stock', 'out_of_stock']:
                return format_html('<span style="color:red;font-weight:bold;">{}</span>', stock)
            return format_html('<span style="color:green;font-weight:bold;">{}</span>', stock)
        return '—'

# ─────────────────────────────────────────────
#  SubscriptionPlan Admin removed
# ─────────────────────────────────────────────
