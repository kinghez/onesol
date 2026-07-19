import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "onesolai.settings")
django.setup()

from vendors.models import Vendor
from vendors.services import get_vendor_service

for vendor in Vendor.objects.filter(is_active=True):
    print(f"Syncing {vendor.name}...")
    try:
        service = get_vendor_service(vendor)
        products_data = service.fetch_products()
        from vendors.models import VendorProduct
        created_count = 0
        updated_count = 0
        for p_data in products_data:
            obj, created = VendorProduct.objects.update_or_create(
                vendor=vendor,
                vendor_product_id=p_data['vendor_product_id'],
                defaults={
                    'name': p_data['name'],
                    'description': p_data['description'],
                    'price': p_data['price'],
                    'stock': p_data['stock'],
                    'is_manual': p_data['is_manual'],
                    'raw_data': p_data['raw_data']
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1
        print(f"  Created: {created_count}, Updated: {updated_count}")
    except Exception as e:
        print(f"  Error: {e}")
