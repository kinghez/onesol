import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onesolai.settings')
django.setup()

from products.models import Tool

for t in Tool.objects.all():
    print(f"{t.slug}: {t.image_url}")
