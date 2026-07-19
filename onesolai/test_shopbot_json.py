import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "onesolai.settings")
django.setup()

from vendors.models import VendorProduct

vps = VendorProduct.objects.filter(vendor__api_type='shopbot')
if vps.exists():
    vp = vps.first()
    print("ShopBot Sample raw_data keys:", vp.raw_data.keys())
    print("ShopBot Sample raw_data json:", json.dumps(vp.raw_data, indent=2))
else:
    print("No ShopBot products found.")

