import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


def sync_all_vendor_products(triggered_by="manual"):
    """
    Synchronous replacement for the old Celery sync_all_vendor_products task.
    Fetches products from all active vendors, updates VendorProduct table,
    and also syncs price/stock back to any linked Tool records.

    Can be called from:
    - Admin action on Vendor or VendorProduct admin pages
    - The "Pull Products" button on the Admin Analytics Dashboard
    """
    from .models import VendorProduct, Vendor
    from products.models import Tool
    from analytics.models import ActivityLog
    from .services import get_vendor_service

    active_vendors = Vendor.objects.filter(is_active=True)
    if not active_vendors.exists():
        logger.info("No active vendors found to sync products.")
        return {'status': 'no_active_vendors', 'total_created': 0, 'total_updated': 0, 'details': []}

    total_created = 0
    total_updated = 0
    total_tools_synced = 0
    synced_details = []
    errors = []

    for vendor in active_vendors:
        try:
            service = get_vendor_service(vendor)
            products = service.fetch_products()

            created = 0
            updated = 0
            tools_synced = 0

            live_product_ids = set()
            for p_data in products:
                vp_id_str = str(p_data['vendor_product_id'])
                live_product_ids.add(vp_id_str)
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

                # Sync price/stock and reactivate tool if restocked
                try:
                    linked_tool = Tool.objects.filter(vendor_product=obj).first()
                    if linked_tool:
                        if not linked_tool.is_active:
                            linked_tool.is_active = True
                        if not linked_tool.is_manual_price and p_data.get('price') is not None:
                            linked_tool.save()
                        else:
                            linked_tool.save(update_fields=['is_active', 'updated_at'])
                        tools_synced += 1
                except Exception as tool_err:
                    logger.warning(f"Could not sync Tool for VendorProduct '{obj.name}': {tool_err}")

            # ── Soft-deactivate out-of-stock products for THIS vendor ──
            delisted_vps = VendorProduct.objects.filter(vendor=vendor).exclude(vendor_product_id__in=live_product_ids)
            for delisted_vp in delisted_vps:
                delisted_vp.stock = '0'
                delisted_vp.save(update_fields=['stock'])
                linked_tool = Tool.objects.filter(vendor_product=delisted_vp).first()
                if linked_tool and linked_tool.is_active:
                    linked_tool.is_active = False
                    linked_tool.save(update_fields=['is_active'])
                    ActivityLog.log(
                        action_type='vendor_sync',
                        severity='warning',
                        title=f"Tool Out of Stock ({linked_tool.name})",
                        details=f"Tool '{linked_tool.name}' hidden from catalog because ID {delisted_vp.vendor_product_id} is out of stock on {vendor.name} API."
                    )

            total_created += created
            total_updated += updated
            total_tools_synced += tools_synced
            detail_str = f"{vendor.name}: {created} new, {updated} updated, {tools_synced} tools synced"
            synced_details.append(detail_str)
            logger.info(f"Synced {vendor.name}: {created} created, {updated} updated.")

        except Exception as e:
            error_msg = f"Failed to sync products for vendor {vendor.name}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            try:
                ActivityLog.log(
                    action_type='vendor_sync',
                    severity='error',
                    title=f"Vendor Product Sync Failed ({vendor.name})",
                    details=error_msg
                )
            except Exception:
                pass

    summary_msg = (
        f"Vendor Product Sync complete ({triggered_by}). "
        f"Total: {total_created} created, {total_updated} updated, {total_tools_synced} tools synced. "
        f"({', '.join(synced_details)})"
    )
    try:
        ActivityLog.log(
            action_type='vendor_sync',
            severity='success' if not errors else 'warning',
            title=f"Vendor Products Synced ({triggered_by})",
            details=summary_msg
        )
    except Exception:
        pass

    logger.info(summary_msg)

    return {
        'status': 'done',
        'total_created': total_created,
        'total_updated': total_updated,
        'total_tools_synced': total_tools_synced,
        'details': synced_details,
        'errors': errors,
    }


def sync_single_vendor_products(vendor, triggered_by="manual"):
    """
    Sync products for a single Vendor. Also updates any linked Tools.
    """
    from .models import VendorProduct
    from products.models import Tool
    from .services import get_vendor_service

    service = get_vendor_service(vendor)
    products = service.fetch_products()

    created = 0
    updated = 0
    tools_synced = 0

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

        # Sync price/stock back to linked Tool
        try:
            linked_tool = Tool.objects.filter(vendor_product=obj).first()
            if linked_tool and not linked_tool.is_manual_price:
                linked_tool.save(update_fields=['updated_at'])
                tools_synced += 1
        except Exception as tool_err:
            logger.warning(f"Could not sync Tool for VendorProduct '{obj.name}': {tool_err}")

    return {'created': created, 'updated': updated, 'tools_synced': tools_synced}
