def unread_notifications(request):
    if request.user.is_authenticated:
        from notifications.models import Notification
        from products.models import Wishlist
        notif_count = Notification.objects.filter(user=request.user, is_read=False).count()
        wl_count = Wishlist.objects.filter(user=request.user).count()
        admin_tools = []
        if request.user.is_staff:
            from products.models import Tool
            admin_tools = list(Tool.objects.filter(is_active=True).values('id', 'name'))
            for t in Tool.objects.filter(is_active=True):
                for at in admin_tools:
                    if at['id'] == t.id:
                        at['price_ngn'] = float(t.get_ngn_price())
                        at['price_usd'] = float(t.get_usd_price())
        return {
            'unread_notifications_count': notif_count,
            'wishlist_count': wl_count,
            'admin_active_tools': admin_tools,
        }
    return {
        'unread_notifications_count': 0,
        'wishlist_count': 0,
        'admin_active_tools': [],
    }


def site_settings(request):
    from core.models import SiteSettings
    try:
        settings_obj = SiteSettings.get()
    except Exception:
        settings_obj = None

    return {
        'site_settings': settings_obj,
        # Live Chat Widget convenience vars — used directly in base templates
        'livechat_enabled': getattr(settings_obj, 'livechat_enabled', False),
        'livechat_show_on_dashboard': getattr(settings_obj, 'livechat_show_on_dashboard', False),
        'livechat_script': getattr(settings_obj, 'livechat_script', ''),
    }


def currency_settings(request):
    import json
    from django.conf import settings
    from core.services import get_live_usd_rates
    from accounts.utils import get_client_ip, get_location_data_from_ip, CURRENCY_TO_FLAG, COUNTRY_TO_CURRENCY

    rates = get_live_usd_rates()
    if not rates:
        rates = {
            'USD': 1.0, 'NGN': 1500.0, 'GBP': 0.78, 'EUR': 0.92,
            'GHS': 15.4, 'KES': 129.5, 'ZAR': 18.2, 'CAD': 1.36, 'AUD': 1.50,
        }
    else:
        rates['USD'] = 1.0

    symbols = settings.CURRENCY_SYMBOLS

    # 1. Perform server-side IP lookup for current location if not in session
    detected_currency = request.session.get('detected_currency')
    detected_country = request.session.get('detected_country')
    detected_country_code = request.session.get('detected_country_code')

    if not detected_currency or not detected_country:
        ip = get_client_ip(request)
        loc = get_location_data_from_ip(ip)
        if loc.get('currency'):
            detected_currency = loc.get('currency')
            request.session['detected_currency'] = detected_currency
        if loc.get('country'):
            detected_country = loc.get('country')
            request.session['detected_country'] = detected_country
        if loc.get('country_code'):
            detected_country_code = loc.get('country_code')
            request.session['detected_country_code'] = detected_country_code

    detected_currency = (detected_currency or 'NGN').upper()
    detected_country = detected_country or 'Nigeria'

    # 2. User active currency & country: profile settings take strict priority if logged in!
    show_location_switch_modal = False
    profile_country = None
    profile_currency = None

    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        profile = request.user.profile
        profile_country = profile.country_preference or ''
        profile_currency = (profile.currency_preference or 'NGN').upper()

        # Active currency is strictly profile's currency
        user_currency = profile_currency

        # Check for location mismatch: detected IP country vs profile country preference
        location_switch_dismissed = request.session.get('location_switch_dismissed', False)
        if (
            detected_country
            and profile_country
            and profile_country != '-'
            and detected_country.lower() != profile_country.lower()
            and not location_switch_dismissed
        ):
            show_location_switch_modal = True
    else:
        # For guests, check manual session currency override or detected IP currency
        user_currency = request.session.get('user_selected_currency') or detected_currency or 'NGN'

    user_currency = user_currency.upper()

    # 3. Flag Alignment: Flag is strictly matched to the active currency!
    country_flag_code = CURRENCY_TO_FLAG.get(user_currency, 'us').lower()
    user_flag_url = f"https://flagcdn.com/w20/{country_flag_code}.png"

    return {
        'live_rates_json': json.dumps(rates),
        'currency_symbols_json': json.dumps(symbols),
        'user_currency': user_currency,
        'user_country_code': country_flag_code,
        'user_flag_url': user_flag_url,
        'show_location_switch_modal': show_location_switch_modal,
        'detected_country': detected_country,
        'detected_currency': detected_currency,
        'profile_country': profile_country,
        'profile_currency': profile_currency,
    }
