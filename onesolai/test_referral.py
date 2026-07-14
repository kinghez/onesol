import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onesolai.settings')
django.setup()

from accounts.models import User, Profile, Referral

# Get admin profile
admin_user = User.objects.get(email='admin@onesolai.com')
admin_profile = admin_user.profile
ref_code = admin_profile.referral_code
print(f"Admin referral code: {ref_code}")

# Create a test user using this ref code programmatically
test_email = 'testref2@example.com'
if not User.objects.filter(email=test_email).exists():
    user = User.objects.create_user(
        username=test_email,
        email=test_email,
        password='password123',
        first_name='Test',
        last_name='User',
    )
    
    # simulate the view logic
    try:
        referrer_profile = Profile.objects.get(referral_code=ref_code)
        Referral.objects.create(
            referrer=referrer_profile.user,
            referred_user=user,
            status='pending',
        )
        print("Referral created successfully!")
    except Exception as e:
        print(f"Error creating referral: {e}")
else:
    print("Test user already exists.")

print('Referrals:', Referral.objects.all().values('referrer__email', 'referred_user__email', 'status'))
