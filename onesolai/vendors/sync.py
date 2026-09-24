import logging
import re
from django.utils import timezone

logger = logging.getLogger(__name__)

CATEGORY_KEYWORDS = [
    (["chatgpt", "claude", "gemini", "deepseek", "grok", "copilot", "perplexity", "bot", "gpt", "poe"], "AI Chatbots"),
    (["capcut", "veo", "sora", "runway", "pika", "heygen", "synthesia", "video", "kling", "luma"], "Video Creation"),
    (["canva", "midjourney", "adobe", "photoshop", "illustrator", "figma", "leonardo", "freepik", "envato"], "Design"),
    (["cursor", "codex", "github", "replit", "windsurf", "api", "token", "credits", "credit", "v0"], "Development"),
    (["grammarly", "quillbot", "jasper", "copy.ai", "turnitin", "write"], "Writing"),
    (["notion", "vpn", "nord", "expressvpn", "office", "excel", "microsoft"], "Productivity"),
    (["netflix", "spotify", "youtube", "prime", "crunchyroll", "disney", "apple", "duolingo"], "Entertainment"),
]


def _normalize_name(name: str) -> str:
    if not name:
        return ""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _determine_category_for_product(name: str, desc: str = ""):
    from products.models import Category
    text = f"{name} {desc}".lower()
    for keywords, cat_name in CATEGORY_KEYWORDS:
        if any(kw in text for kw in keywords):
            cat = Category.objects.filter(name=cat_name).first()
            if cat:
                return cat
    cat, _ = Category.objects.get_or_create(
        name="Uncategorized",
        defaults={"slug": "uncategorized", "order": 999}
    )
    return cat


def _sync_tool_for_vendor_product(vp, vendor):
    """
    Ensures a Tool is linked to the VendorProduct, reactivates restocked tools,
    re-links tools when vendor product IDs rotate, or auto-creates a new Tool.
    Returns (tool, was_created, was_relinked).
    """
    from products.models import Tool

    tool = Tool.objects.filter(vendor_product=vp).first()
    was_created = False
    was_relinked = False

    # Check for rotated product ID match among unlinked or inactive tools for this vendor
    if not tool:
        norm_vp_name = _normalize_name(vp.name)
        candidate_tools = Tool.objects.filter(vendor_product__vendor=vendor, is_active=False).select_related("vendor_product")
        for cand in candidate_tools:
            cand_vp = cand.vendor_product
            cand_old_name = cand_vp.name if cand_vp else ""
            if (
                cand_old_name.strip().lower() == vp.name.strip().lower()
                or (cand_old_name and _normalize_name(cand_old_name) == norm_vp_name)
                or _normalize_name(cand.name) == norm_vp_name
            ):
                tool = cand
                tool.vendor_product = vp
                was_relinked = True
                logger.info(f"Re-linked Tool '{tool.name}' to rotated VendorProduct '{vp.name}' (ID: {vp.vendor_product_id})")
                break

    # If no Tool is linked, do not auto-create: products must be manually pulled/curated to Tools
    if not tool:
        return None, False, False

    # Sync active status and pricing
    if vp.stock != "0":
        tool.is_active = True
    else:
        tool.is_active = False

    if not tool.is_manual_price and vp.price is not None:
        tool.save()
    else:
        update_fields = ["is_active", "updated_at"]
        if was_relinked:
            update_fields.append("vendor_product")
        tool.save(update_fields=update_fields)

    return tool, was_created, was_relinked


def sync_all_vendor_products(triggered_by="manual"): 
    from .models import VendorProduct, Vendor
    from products.models import Tool
    from analytics.models import ActivityLog
    from .services import get_vendor_service

    active_vendors = Vendor.objects.filter(is_active=True)
    if not active_vendors.exists():
        logger.info("No active vendors found to sync products.")
        return {"status": "no_active_vendors", "total_created": 0, "total_updated": 0, "details": []}

    total_created = 0
    total_updated = 0
    total_tools_synced = 0
    total_tools_created = 0
    total_tools_relinked = 0
    synced_details = []
    errors = []

    for vendor in active_vendors:
        try:
            service = get_vendor_service(vendor)
            products = service.fetch_products()

            created = 0
            updated = 0
            tools_synced = 0
            tools_created = 0
            tools_relinked = 0

            live_product_ids = set()
            for p_data in products:
                vp_id_str = str(p_data["vendor_product_id"])
                live_product_ids.add(vp_id_str)
                obj, is_new = VendorProduct.objects.update_or_create(
                    vendor=vendor,
                    vendor_product_id=p_data["vendor_product_id"],
                    defaults={
                        "name": p_data["name"],
                        "description": p_data["description"],
                        "price": p_data["price"],
                        "stock": p_data["stock"],
                        "is_manual": p_data["is_manual"],
                        "raw_data": p_data["raw_data"],
                    }
                )

                if is_new:
                    created += 1
                else:
                    updated += 1

                try:
                    tool_obj, was_tool_created, was_tool_relinked = _sync_tool_for_vendor_product(obj, vendor)
                    tools_synced += 1
                    if was_tool_created:
                        tools_created += 1
                    if was_tool_relinked:
                        tools_relinked += 1
                except Exception as tool_err:
                    logger.warning(f"Could not sync Tool for VendorProduct '{obj.name}': {tool_err}")

            # Soft-deactivate out-of-stock products for THIS vendor
            delisted_vps = VendorProduct.objects.filter(vendor=vendor).exclude(vendor_product_id__in=live_product_ids)
            for delisted_vp in delisted_vps:
                delisted_vp.stock = "0"
                delisted_vp.save(update_fields=["stock"])
                linked_tool = Tool.objects.filter(vendor_product=delisted_vp).first()
                if linked_tool:
                    if linked_tool.vendor_product and linked_tool.vendor_product.vendor_product_id in live_product_ids:
                        continue
                    if linked_tool.is_active:
                        linked_tool.is_active = False
                        linked_tool.save(update_fields=["is_active"])
                        ActivityLog.log(
                            action_type="vendor_sync",
                            severity="warning",
                            title=f"Tool Out of Stock ({linked_tool.name})",
                            details=f"Tool '{linked_tool.name}' hidden from catalog because ID {delisted_vp.vendor_product_id} is out of stock on {vendor.name} API."
                        )

            total_created += created
            total_updated += updated
            total_tools_synced += tools_synced
            total_tools_created += tools_created
            total_tools_relinked += tools_relinked
            detail_str = (
                f"{vendor.name}: {created} new VP, {updated} updated VP, "
                f"{tools_synced} tools synced ({tools_created} new tools, {tools_relinked} re-linked)"
            )
            synced_details.append(detail_str)
            logger.info(f"Synced {vendor.name}: {created} created, {updated} updated, {tools_synced} tools.")

        except Exception as e:
            raw_err = str(e)
            if "SUSPENDED" in raw_err or "suspended" in raw_err.lower():
                error_msg = (
                    f"{vendor.name}: Vendor server is SUSPENDED. "
                    f"The ShopBot API server on Render.com has been shut down. "
                    f"Please contact the vendor to restore their service. ({raw_err[:300]})"
                )
                severity = "error"
            elif "503" in raw_err and ("render.com" in raw_err.lower() or "Service Unavailable" in raw_err):
                error_msg = (
                    f"{vendor.name}: Vendor API server is temporarily unavailable (503). "
                    f"If this is a Render.com cold-start, try again in 1 minute. ({raw_err[:200]})"
                )
                severity = "warning"
            else:
                error_msg = f"Failed to sync products for vendor {vendor.name}: {raw_err}"
                severity = "error"
            logger.error(error_msg)
            errors.append(error_msg)
            try:
                ActivityLog.log(action_type="vendor_sync", severity=severity, title=f"Vendor Sync Issue: {vendor.name}", details=error_msg)
            except Exception:
                pass

    summary_msg = (
        f"Vendor Product Sync complete ({triggered_by}). "
        f"Total: {total_created} created, {total_updated} updated, {total_tools_synced} tools synced "
        f"({total_tools_created} new tools, {total_tools_relinked} re-linked). "
        f"({', '.join(synced_details)})"
    )
    try:
        ActivityLog.log(action_type="vendor_sync", severity="success" if not errors else "warning", title=f"Vendor Products Synced ({triggered_by})", details=summary_msg)
    except Exception:
        pass

    logger.info(summary_msg)

    return {
        "status": "done",
        "total_created": total_created,
        "total_updated": total_updated,
        "total_tools_synced": total_tools_synced,
        "total_tools_created": total_tools_created,
        "total_tools_relinked": total_tools_relinked,
        "details": synced_details,
        "errors": errors,
    }


def sync_single_vendor_products(vendor, triggered_by="manual"): 
    from .models import VendorProduct
    from products.models import Tool
    from .services import get_vendor_service

    service = get_vendor_service(vendor)
    products = service.fetch_products()

    created = 0
    updated = 0
    tools_synced = 0
    tools_created = 0
    tools_relinked = 0

    live_product_ids = set()
    for p_data in products:
        vp_id_str = str(p_data["vendor_product_id"])
        live_product_ids.add(vp_id_str)
        obj, is_new = VendorProduct.objects.update_or_create(
            vendor=vendor,
            vendor_product_id=p_data["vendor_product_id"],
            defaults={
                "name": p_data["name"],
                "description": p_data["description"],
                "price": p_data["price"],
                "stock": p_data["stock"],
                "is_manual": p_data["is_manual"],
                "raw_data": p_data["raw_data"],
            }
        )
        if is_new:
            created += 1
        else:
            updated += 1

        try:
            tool_obj, was_tool_created, was_tool_relinked = _sync_tool_for_vendor_product(obj, vendor)
            tools_synced += 1
            if was_tool_created:
                tools_created += 1
            if was_tool_relinked:
                tools_relinked += 1
        except Exception as tool_err:
            logger.warning(f"Could not sync Tool for VendorProduct '{obj.name}': {tool_err}")

    delisted_vps = VendorProduct.objects.filter(vendor=vendor).exclude(vendor_product_id__in=live_product_ids)
    for delisted_vp in delisted_vps:
        delisted_vp.stock = "0"
        delisted_vp.save(update_fields=["stock"])
        linked_tool = Tool.objects.filter(vendor_product=delisted_vp).first()
        if linked_tool:
            if linked_tool.vendor_product and linked_tool.vendor_product.vendor_product_id in live_product_ids:
                continue
            if linked_tool.is_active:
                linked_tool.is_active = False
                linked_tool.save(update_fields=["is_active"])

    return {
        "created": created,
        "updated": updated,
        "tools_synced": tools_synced,
        "tools_created": tools_created,
        "tools_relinked": tools_relinked,
    }
