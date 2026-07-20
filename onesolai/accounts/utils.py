import requests
import logging

logger = logging.getLogger(__name__)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_location_data_from_ip(ip):
    """
    Returns a dict with 'country' and 'currency' based on IP.
    Uses ipapi.co or ip-api.com.
    """
    if not ip or ip == '127.0.0.1':
        # Default fallback for local testing
        return {'country': 'Nigeria', 'currency': 'NGN'}
        
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}?fields=country,currency,status', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return {
                    'country': data.get('country'),
                    'currency': data.get('currency', 'USD') # some free endpoints might not return currency
                }
    except Exception as e:
        logger.error(f"IP Geolocation failed for IP {ip}: {e}")
        
    return {'country': None, 'currency': None}
