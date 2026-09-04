import requests
import logging

logger = logging.getLogger(__name__)

CURRENCY_TO_FLAG = {
    'NGN': 'ng', 'USD': 'us', 'GBP': 'gb', 'EUR': 'eu',
    'GHS': 'gh', 'KES': 'ke', 'ZAR': 'za', 'UGX': 'ug',
    'TZS': 'tz', 'RWF': 'rw', 'XOF': 'sn', 'XAF': 'cm',
    'ZMW': 'zm', 'MWK': 'mw', 'MUR': 'mu', 'EGP': 'eg',
    'ETB': 'et', 'CAD': 'ca', 'AUD': 'au', 'INR': 'in',
    'BRL': 'br', 'JPY': 'jp', 'CNY': 'cn', 'MAD': 'ma',
    'NZD': 'nz', 'CHF': 'ch', 'MXN': 'mx', 'SAR': 'sa',
    'AED': 'ae', 'QAR': 'qa', 'KWD': 'kw', 'OMR': 'om',
    'BHD': 'bh', 'JOD': 'jo', 'TRY': 'tr', 'SGD': 'sg',
    'MYR': 'my', 'THB': 'th', 'IDR': 'id', 'PHP': 'ph',
    'VND': 'vn', 'PKR': 'pk', 'BDT': 'bd', 'LKR': 'lk',
    'NPR': 'np', 'KRW': 'kr', 'HKD': 'hk', 'TWD': 'tw',
    'ILS': 'il', 'RUB': 'ru', 'PLN': 'pl', 'SEK': 'se',
    'NOK': 'no', 'DKK': 'dk', 'CZK': 'cz', 'HUF': 'hu',
    'RON': 'ro', 'BGN': 'bg', 'UAH': 'ua', 'ARS': 'ar',
    'CLP': 'cl', 'COP': 'co', 'PEN': 'pe', 'UYU': 'uy',
    'DZD': 'dz', 'AOA': 'ao', 'BWP': 'bw', 'NAD': 'na',
}

COUNTRY_TO_CURRENCY = {
    'Nigeria': 'NGN', 'United States': 'USD', 'United Kingdom': 'GBP',
    'Ghana': 'GHS', 'Kenya': 'KES', 'South Africa': 'ZAR',
    'Canada': 'CAD', 'Australia': 'AUD', 'India': 'INR',
    'France': 'EUR', 'Germany': 'EUR', 'Spain': 'EUR',
    'Italy': 'EUR', 'Netherlands': 'EUR', 'Uganda': 'UGX',
    'Tanzania': 'TZS', 'Rwanda': 'RWF', 'Zambia': 'ZMW',
    'Egypt': 'EGP', 'Morocco': 'MAD', 'China': 'CNY', 'Japan': 'JPY',
}


def get_client_ip(request):
    """Extract real client IP considering proxies, Cloudflare, ngrok, and load balancers."""
    cf_ip = request.META.get('HTTP_CF_CONNECTING_IP')
    if cf_ip:
        return cf_ip.strip()

    real_ip = request.META.get('HTTP_X_REAL_IP')
    if real_ip:
        return real_ip.strip()

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
        return ip

    return request.META.get('REMOTE_ADDR', '').strip()


def get_location_data_from_ip(ip):
    """
    Returns a dict with 'country', 'country_code', and 'currency' based on IP.
    """
    is_local = (not ip or ip in ['127.0.0.1', 'localhost', '::1'] or ip.startswith('192.168.') or ip.startswith('10.'))

    if is_local:
        try:
            res = requests.get('https://api.ipify.org?format=json', timeout=2)
            if res.status_code == 200:
                ip = res.json().get('ip')
        except Exception:
            pass

    if not ip or ip in ['127.0.0.1', 'localhost', '::1']:
        return {'country': 'Nigeria', 'country_code': 'NG', 'currency': 'NGN'}

    try:
        response = requests.get(f'http://ip-api.com/json/{ip}?fields=country,countryCode,currency,status', timeout=4)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                country = data.get('country')
                cc = data.get('countryCode')
                curr = data.get('currency')
                if not curr and country in COUNTRY_TO_CURRENCY:
                    curr = COUNTRY_TO_CURRENCY[country]
                if not curr:
                    curr = 'NGN' if cc == 'NG' else 'USD'
                if not cc:
                    cc = CURRENCY_TO_FLAG.get(curr, 'NG' if curr == 'NGN' else 'US').upper()
                return {
                    'country': country or ('Nigeria' if curr == 'NGN' else None),
                    'country_code': cc,
                    'currency': curr
                }
    except Exception as e:
        logger.error(f"IP Geolocation failed for IP {ip}: {e}")

    return {'country': None, 'country_code': None, 'currency': None}


def get_active_user_currency(request):
    """
    Returns active user currency code (e.g. 'USD', 'NGN', 'GBP').
    Strict precedence:
    1. If user is logged in AND has an explicit country preference set,
       their profile currency_preference takes strict priority.
    2. Otherwise (guest or user without a configured country preference),
       fall back to session manual override, then IP detected currency, then 'NGN'.
    """
    if hasattr(request, 'user') and request.user.is_authenticated and hasattr(request.user, 'profile'):
        profile = request.user.profile
        if profile.country_preference and profile.currency_preference:
            return profile.currency_preference.upper()
    return (request.session.get('user_selected_currency') or request.session.get('detected_currency') or 'NGN').upper()