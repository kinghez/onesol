import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onesolai.settings')
django.setup()

from accounts.models import Referral

print('Referrals:', Referral.objects.all().values('referrer__email', 'referred_user__email', 'status'))
