import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onesolai.settings')
django.setup()

from accounts.models import Profile

Profile.objects.filter(country_preference__isnull=True).update(country_preference='Nigeria')
Profile.objects.filter(country_preference='').update(country_preference='Nigeria')
print("Profiles updated successfully.")
