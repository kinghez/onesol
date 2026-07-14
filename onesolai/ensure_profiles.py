import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onesolai.settings')
django.setup()

from accounts.models import User, Profile

for u in User.objects.all():
    Profile.objects.get_or_create(user=u)

print("Profiles ensured for all users.")
