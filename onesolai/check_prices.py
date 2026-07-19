import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "onesolai.settings")
django.setup()

from vendors.models import VendorProduct

print("--- Akunding ---")
p_akun = VendorProduct.objects.filter(vendor__name__icontains='Akunding').first()
if p_akun:
    print(json.dumps(p_akun.raw_data, indent=2))

print("\n--- ShopBot ---")
p_shop = VendorProduct.objects.filter(vendor__name__icontains='Shop').first()
if p_shop:
    print(json.dumps(p_shop.raw_data, indent=2))
