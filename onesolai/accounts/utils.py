import requests
import logging

logger = logging.getLogger(__name__)

CURRENCY_TO_FLAG = {
    'USD': 'us', 'NGN': 'ng', 'GBP': 'gb', 'EUR': 'eu',
    'GHS': 'gh', 'KES': 'ke', 'ZAR': 'za', 'UGX': 'ug',
    'TZS': 'tz', 'RWF': 'rw', 'XOF': 'sn', 'XAF': 'cm',
    'ZMW': 'zm', 'MWK': 'mw', 'MUR': 'mu', 'EGP': 'eg',
    'ETB': 'et', 'CAD': 'ca', 'AUD': 'au', 'INR': 'in',
    'BRL': 'br', 'JPY': 'jp', 'CNY': 'cn',
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
        # Try getting public IP if running locally behind dev server
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
                curr = data.get('currency') or 'USD'
                cc = data.get('countryCode') or CURRENCY_TO_FLAG.get(curr, 'US').upper()
                return {
                    'country': data.get('country', 'United States'),
                    'country_code': cc,
                    'currency': curr
                }
    except Exception as e:
        logger.error(f"IP Geolocation failed for IP {ip}: {e}")

    return {'country': None, 'country_code': None, 'currency': None}
