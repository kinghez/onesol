import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "onesolai.settings")
django.setup()

from products.models import Tool

for t in Tool.objects.all():
    print('Tool:', t.name)
    print('is_in_stock:', t.is_in_stock)
    print('vp_stock:', t.vendor_product.stock if t.vendor_product else 'No vendor product')
