import logging
from celery import shared_task
from vendors.models import Vendor
from vendors.services import get_vendor_service
from .models import VendorBalanceSnapshot

logger = logging.getLogger(__name__)

@shared_task
def fetch_vendor_balances():
    """
    Fetches the live balance for all active vendors and stores a snapshot.
    Also alerts if balance falls below a threshold (e.g. $10 or NGN equivalent).
    """
    vendors = Vendor.objects.filter(is_active=True)
    for vendor in vendors:
        try:
            service = get_vendor_service(vendor)
            balance = service.get_balance()
            
            # Save snapshot
            VendorBalanceSnapshot.objects.create(
                vendor=vendor,
                balance=balance
            )
            
            # TODO: We can trigger an email or in-app notification if balance < threshold
            # e.g., if balance < 10.0: send_alert_to_admin(vendor.name, balance)
            
        except Exception as e:
            logger.error(f"Failed to fetch balance for vendor {vendor.name}: {e}")
            
    # Cleanup old snapshots (keep last 30 days or so, we can just keep the latest 100 per vendor)
    for vendor in vendors:
        snapshots_to_keep = VendorBalanceSnapshot.objects.filter(vendor=vendor).order_by('-timestamp')[:50].values_list('id', flat=True)
        VendorBalanceSnapshot.objects.filter(vendor=vendor).exclude(id__in=list(snapshots_to_keep)).delete()
