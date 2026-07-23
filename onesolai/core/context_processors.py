def unread_notifications(request):
    if request.user.is_authenticated:
        from notifications.models import Notification
        from products.models import Wishlist
        notif_count = Notification.objects.filter(user=request.user, is_read=False).count()
        wl_count = Wishlist.objects.filter(user=request.user).count()
        return {
            'unread_notifications_count': notif_count,
            'wishlist_count': wl_count,
        }
    return {
        'unread_notifications_count': 0,
        'wishlist_count': 0,
    }

def site_settings(request):
    from core.models import SiteSettings
    return {'site_settings': SiteSettings.get()}


def currency_settings(request):
    import json
    from django.conf import settings
    from core.services import get_live_usd_rates
    from accounts.utils import get_client_ip, get_location_data_from_ip, CURRENCY_TO_FLAG

    rates = get_live_usd_rates()
    if not rates:
        rates = {
            'USD': 1.0,
            'NGN': 1500.0,
            'GBP': 0.78,
            'EUR': 0.92,
            'GHS': 15.4,
            'KES': 129.5,
            'ZAR': 18.2,
            'CAD': 1.36,
            'AUD': 1.50,
        }
    else:
        rates['USD'] = 1.0

    symbols = settings.CURRENCY_SYMBOLS

    # 1. Check if session already has IP geolocation stored
    detected_currency = request.session.get('detected_currency')
    detected_country_code = request.session.get('detected_country_code')

    # If not in session, perform server-side IP lookup immediately
    if not detected_currency or not detected_country_code:
        ip = get_client_ip(request)
        loc = get_location_data_from_ip(ip)
        if loc.get('currency'):
            detected_currency = loc.get('currency')
            request.session['detected_currency'] = detected_currency
        if loc.get('country_code'):
            detected_country_code = loc.get('country_code')
            request.session['detected_country_code'] = detected_country_code
        if loc.get('country'):
            request.session['detected_country'] = loc.get('country')

    # 2. Determine active currency for user/visitor
    user_currency = None
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        user_currency = request.user.profile.currency_preference

    if not user_currency:
        user_currency = detected_currency or 'NGN'

    user_currency = user_currency.upper()

    # 3. Determine country code and corresponding flag
    user_country_code = detected_country_code or ''
    if not user_country_code and request.user.is_authenticated and hasattr(request.user, 'profile'):
        pref = (request.user.profile.country_preference or '').lower()
        if pref in ['usa', 'united states', 'us']:
            user_country_code = 'US'
        elif pref in ['nigeria', 'ng']:
            user_country_code = 'NG'
        elif pref in ['united kingdom', 'uk', 'gb']:
            user_country_code = 'GB'

    if not user_country_code:
        user_country_code = CURRENCY_TO_FLAG.get(user_currency, 'us').upper()

    user_country_code_lower = user_country_code.lower()
    user_flag_url = f"https://flagcdn.com/w20/{user_country_code_lower}.png"

    # Sync user profile if logged in and profile currency doesn't match detected IP currency
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        profile = request.user.profile
        if profile.currency_preference != user_currency:
            profile.currency_preference = user_currency
            profile.save(update_fields=['currency_preference'])

    return {
        'live_rates_json': json.dumps(rates),
        'currency_symbols_json': json.dumps(symbols),
        'user_currency': user_currency,
        'user_country_code': user_country_code_lower,
        'user_flag_url': user_flag_url,
    }

