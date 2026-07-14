import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onesolai.settings')
django.setup()

from accounts.models import User, Profile, Referral

print("Most recent users:")
for u in User.objects.all().order_by('-date_joined')[:5]:
    print(f"User: {u.email}")
    has_ref = hasattr(u, 'referred_by')
    if has_ref:
        ref = u.referred_by
        print(f"  Referred by: {ref.referrer.email if ref.referrer else 'None'}")
    else:
        print("  Referred by: None")

print("\nAll Referrals:")
for r in Referral.objects.all():
    print(f"Referrer: {r.referrer.email} -> Referred: {r.referred_user.email} (Status: {r.status})")
