from django.contrib import admin
from django.contrib import messages
from .models import Vendor, VendorProduct
from .services import get_vendor_service

class VendorProductInline(admin.TabularInline):
    model = VendorProduct
    extra = 0
    readonly_fields = ('vendor_product_id', 'name', 'price', 'stock', 'is_manual', 'last_synced_at')
    can_delete = False
    max_num = 0

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'api_type', 'is_active', 'created_at')
    list_filter = ('api_type', 'is_active')
    search_fields = ('name',)
    actions = ['sync_products', 'check_balance']
    inlines = [VendorProductInline]

    @admin.action(description="Sync Products from Vendor")
    def sync_products(self, request, queryset):
        for vendor in queryset:
            if not vendor.is_active:
                continue
            try:
                service = get_vendor_service(vendor)
                products = service.fetch_products()
                
                created = 0
                updated = 0
                for p_data in products:
                    obj, is_new = VendorProduct.objects.update_or_create(
                        vendor=vendor,
                        vendor_product_id=p_data['vendor_product_id'],
                        defaults={
                            'name': p_data['name'],
                            'description': p_data['description'],
                            'price': p_data['price'],
                            'stock': p_data['stock'],
                            'is_manual': p_data['is_manual'],
                            'raw_data': p_data['raw_data'],
                        }
                    )
                    if is_new:
                        created += 1
                    else:
                        updated += 1
                messages.success(request, f"Synced {vendor.name}: {created} created, {updated} updated.")
            except Exception as e:
                messages.error(request, f"Failed to sync {vendor.name}: {e}")

    @admin.action(description="Check Account Balance")
    def check_balance(self, request, queryset):
        for vendor in queryset:
            try:
                service = get_vendor_service(vendor)
                balance = service.get_balance()
                messages.info(request, f"{vendor.name} Balance: {balance}")
            except Exception as e:
                messages.error(request, f"Failed to get balance for {vendor.name}: {e}")

@admin.register(VendorProduct)
class VendorProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'vendor', 'vendor_product_id', 'price', 'stock', 'is_added_to_tools', 'is_manual', 'last_synced_at')
    list_filter = ('vendor', 'is_manual')
    search_fields = ('name', 'vendor_product_id')
    readonly_fields = ('vendor', 'vendor_product_id', 'name', 'description', 'price', 'stock', 'is_manual', 'raw_data', 'last_synced_at')
    actions = ['create_tools_from_products']

    def has_add_permission(self, request):
        return False

    @admin.display(description="Added to Tools?", boolean=True)
    def is_added_to_tools(self, obj):
        from products.models import Tool
        return Tool.objects.filter(vendor_product=obj).exists()

    @admin.action(description="Create Frontend Tools from Selected")
    def create_tools_from_products(self, request, queryset):
        from products.models import Tool, Category
        from core.ai_service import refine_product_copy
        cat, _ = Category.objects.get_or_create(name='Uncategorized', defaults={'slug': 'uncategorized', 'order': 999})
        
        created = 0
        skipped = 0
        ai_refined = 0
        
        for vp in queryset:
            if Tool.objects.filter(vendor_product=vp).exists():
                skipped += 1
                continue
            
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
            
        msg = f"Successfully created {created} new Frontend Tools from Vendor Products."
        if ai_refined > 0:
            msg += f" {ai_refined} descriptions were polished by AI."
        if skipped > 0:
            msg += f" Skipped {skipped} already existing tools."
        messages.success(request, msg)
