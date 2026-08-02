from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from .models import Vendor, VendorProduct
from .services import get_vendor_service
from .sync import sync_single_vendor_products


class VendorProductInline(admin.TabularInline):
    model = VendorProduct
    extra = 0
    readonly_fields = ('vendor_product_id', 'name', 'price', 'stock', 'is_manual', 'last_synced_at')
    can_delete = False
    max_num = 0


from django import forms


class VendorAdminForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = '__all__'
        widgets = {
            'api_key': forms.PasswordInput(render_value=True, attrs={'autocomplete': 'new-password'}),
            'webhook_secret': forms.PasswordInput(render_value=True, attrs={'autocomplete': 'new-password'}),
        }


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    form = VendorAdminForm
    list_display = ('name', 'api_type', 'is_active', 'created_at')
    list_filter = ('api_type', 'is_active')
    search_fields = ('name',)
    actions = ['sync_products', 'check_balance']
    inlines = [VendorProductInline]

    @admin.action(description="🔄 Sync Products from Vendor API (+ update linked Tools)")
    def sync_products(self, request, queryset):
        for vendor in queryset:
            if not vendor.is_active:
                messages.warning(request, f"Skipped {vendor.name} — vendor is inactive.")
                continue
            try:
                result = sync_single_vendor_products(vendor, triggered_by=f"Admin ({request.user})")
                created = result['created']
                updated = result['updated']
                tools_synced = result['tools_synced']
                messages.success(
                    request,
                    f"✅ {vendor.name}: {created} new products, {updated} updated, {tools_synced} linked tools price/stock synced."
                )
            except Exception as e:
                messages.error(request, f"❌ Failed to sync {vendor.name}: {e}")

    @admin.action(description="💰 Check Account Balance")
    def check_balance(self, request, queryset):
        for vendor in queryset:
            try:
                service = get_vendor_service(vendor)
                balance = service.get_balance()
                messages.info(request, f"{vendor.name} Balance: {balance}")
            except Exception as e:
                messages.error(request, f"Failed to get balance for {vendor.name}: {e}")


from core.admin_utils import export_as_csv

@admin.register(VendorProduct)
class VendorProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'vendor', 'vendor_product_id', 'price', 'stock',
        'is_added_to_tools', 'tool_price_badge', 'is_manual', 'last_synced_at'
    )
    list_filter = ('vendor', 'is_manual')
    search_fields = ('name', 'vendor_product_id')
    readonly_fields = (
        'vendor', 'vendor_product_id', 'name', 'description',
        'price', 'stock', 'is_manual', 'raw_data', 'last_synced_at'
    )
    actions = ['create_tools_from_products', 'pull_price_stock_updates', export_as_csv]

    def has_add_permission(self, request):
        return False

    @admin.display(description="In Tools?", boolean=True)
    def is_added_to_tools(self, obj):
        from products.models import Tool
        return Tool.objects.filter(vendor_product=obj).exists()

    @admin.display(description="Tool Sell Price")
    def tool_price_badge(self, obj):
        from products.models import Tool
        tool = Tool.objects.filter(vendor_product=obj).first()
        if tool:
            price = tool.get_ngn_price()
            if price:
                return format_html(
                    '<span style="background:#10B981;color:#fff;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:700;">₦{}</span>',
                    f"{price:,.0f}"
                )
        return format_html('<span style="color:#6B7280;font-size:11px;">—</span>')

    @admin.action(description="🛒 Create Frontend Tools from Selected")
    def create_tools_from_products(self, request, queryset):
        from products.models import Tool, Category
        from core.ai_service import refine_product_copy
        cat, _ = Category.objects.get_or_create(
            name='Uncategorized',
            defaults={'slug': 'uncategorized', 'order': 999}
        )

        created = 0
        skipped = 0
        ai_refined = 0

        for vp in queryset:
            if Tool.objects.filter(vendor_product=vp).exists():
                skipped += 1
                continue

            try:
                tool_name = vp.name
                tool_desc = vp.description or f"Purchase {vp.name} securely and instantly."
                tool_short_desc = ""

                # Try AI Refinement
                categories = list(Category.objects.values_list('name', flat=True))
                refined = refine_product_copy(tool_name, tool_desc, available_categories=categories)
                assigned_cat = cat
                if refined:
                    tool_name = refined.get('name', tool_name)
                    tool_short_desc = refined.get('short_description', '')
                    tool_desc = refined.get('description', tool_desc)
                    ai_cat_name = refined.get('category')
                    if ai_cat_name:
                        matched_cat = Category.objects.filter(name__iexact=ai_cat_name.strip()).first()
                        if matched_cat:
                            assigned_cat = matched_cat
                    ai_refined += 1

                Tool.objects.create(
                    name=tool_name,
                    category=assigned_cat,
                    vendor_product=vp,
                    description=tool_desc,
                    short_description=tool_short_desc,
                    is_ai_refined=bool(refined),
                    is_active=True
                )
                created += 1
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error creating tool for VendorProduct '{vp.name}': {e}")

        msg = f"Successfully created {created} new Frontend Tools from Vendor Products."
        if ai_refined > 0:
            msg += f" {ai_refined} descriptions were polished by AI."
        if skipped > 0:
            msg += f" Skipped {skipped} already existing tools."
        messages.success(request, msg)

    @admin.action(description="🔃 Pull Price & Stock Updates → Sync to Linked Tools")
    def pull_price_stock_updates(self, request, queryset):
        """
        For selected VendorProducts, re-fetch latest price/stock from the vendor API
        and update both the VendorProduct record AND any linked Tool record.
        """
        from products.models import Tool
        vendors_to_sync = set(vp.vendor for vp in queryset)
        total_updated = 0
        tools_updated = 0

        for vendor in vendors_to_sync:
            try:
                service = get_vendor_service(vendor)
                fetched = service.fetch_products()
                fetched_map = {p['vendor_product_id']: p for p in fetched}

                # Only update the selected VendorProducts for this vendor
                selected_for_vendor = queryset.filter(vendor=vendor)
                for vp in selected_for_vendor:
                    fresh = fetched_map.get(vp.vendor_product_id)
                    if not fresh:
                        continue

                    # Update VendorProduct fields
                    vp.price = fresh['price']
                    vp.stock = fresh['stock']
                    vp.is_manual = fresh['is_manual']
                    vp.raw_data = fresh['raw_data']
                    vp.save(update_fields=['price', 'stock', 'is_manual', 'raw_data', 'last_synced_at'])
                    total_updated += 1

                    # Sync to linked Tool if exists and not manually priced
                    linked_tool = Tool.objects.filter(vendor_product=vp).first()
                    if linked_tool and not linked_tool.is_manual_price:
                        linked_tool.save(update_fields=['updated_at'])
                        tools_updated += 1

            except Exception as e:
                messages.error(request, f"❌ Failed to pull updates from {vendor.name}: {e}")

        messages.success(
            request,
            f"✅ Updated {total_updated} vendor product(s) with fresh price/stock. "
            f"{tools_updated} linked Tool(s) were also synced."
        )
