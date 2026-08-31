from django.db import migrations

def update_shopbot_vendor(apps, schema_editor):
    Vendor = apps.get_model('vendors', 'Vendor')
    conn_str = "conn_eyJrIjoic2tfZDdiYTIxOThiMTc2YTM5MzliYTAxNTUyYTYyNTg4MDhiZWRlN2RiMGQ1NmViMDJiIiwidSI6Imh0dHBzOi8vaW5zMjExMjEzMS1md2YxLm9ucmVuZGVyLmNvbS88ZjcxYWVkZDM0OTRlMDQyYmIwNjQwOGY1MGI3ZjkzOCJ9"
    new_url = "https://ins2112131-fwf1.onrender.com/8f71aedd3494e042bb06408f50b7f938"

    for v in Vendor.objects.filter(api_type='shopbot'):
        v.api_key = conn_str
        v.base_url = new_url
        v.save()

def reverse_func(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(update_shopbot_vendor, reverse_func),
    ]
