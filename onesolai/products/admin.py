from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Tool, SubscriptionPlan


# ─────────────────────────────────────────────
#  Inline: SubscriptionPlan inside Tool admin
# ─────────────────────────────────────────────
class SubscriptionPlanInline(admin.TabularInline):
    model = SubscriptionPlan
    extra = 1
    fields = ('name', 'duration_type', 'duration_days', 'price_ngn', 'is_best_value', 'is_active')
    ordering = ('duration_days',)


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
        'logo_preview', 'name', 'category', 'base_price_ngn',
        'is_featured', 'is_popular', 'is_new', 'is_active', 'plan_count', 'updated_at'
    )
    list_display_links = ('logo_preview', 'name')
    list_filter = ('category', 'is_featured', 'is_popular', 'is_new', 'is_active')
    list_editable = ('is_featured', 'is_popular', 'is_new', 'is_active')
    search_fields = ('name', 'description', 'developer')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at', 'logo_preview_large')
    ordering = ('-is_featured', '-is_popular', 'name')
    inlines = [SubscriptionPlanInline]

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name', 'slug', 'category', 'developer',
                'description', 'short_description',
            )
        }),
        ('Pricing', {
            'fields': ('base_price_ngn',)
        }),
        ('Display & Media', {
            'fields': ('image_url', 'logo_preview_large', 'users_count', 'rating', 'review_count')
        }),
        ('Status Flags', {
            'fields': ('is_active', 'is_featured', 'is_popular', 'is_new')
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

    @admin.display(description='Plans')
    def plan_count(self, obj):
        return obj.plans.count()


# ─────────────────────────────────────────────
#  SubscriptionPlan Admin (standalone)
# ─────────────────────────────────────────────
@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('tool', 'name', 'duration_type', 'duration_days', 'price_ngn', 'is_best_value', 'is_active')
    list_filter = ('duration_type', 'is_active', 'is_best_value', 'tool__category')
    search_fields = ('tool__name', 'name')
    list_editable = ('price_ngn', 'is_best_value', 'is_active')
    ordering = ('tool__name', 'duration_days')
