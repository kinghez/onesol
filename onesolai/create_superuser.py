import os
import django
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onesolai.settings')
django.setup()

User = get_user_model()

if not User.objects.filter(email='admin@onesolai.com').exists():
    User.objects.create_superuser(
        email='admin@onesolai.com',
        username='admin',
        password='adminpassword123',
        first_name='System',
        last_name='Admin'
    )
    print("Superuser created successfully (admin@onesolai.com / adminpassword123)")
else:
    print("Superuser already exists.")
