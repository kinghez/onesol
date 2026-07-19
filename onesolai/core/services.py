import requests
from django.core.cache import cache

def get_live_usd_rates():
    """
    Fetches the live exchange rates for USD from open.er-api.com.
    Caches the result for 12 hours (43200 seconds) to ensure lightning fast page loads.
    Returns a dictionary of rates, e.g. {'NGN': 1500.0, 'GHS': 12.0, ...}
    If the API fails, returns None.
    """
    cache_key = 'live_usd_rates'
    rates = cache.get(cache_key)
    
    if rates is not None:
        return rates

    try:
        response = requests.get('https://open.er-api.com/v6/latest/USD', timeout=5)
        if response.status_code == 200:
            data = response.json()
            rates = data.get('rates')
            if rates:
                # Cache for 12 hours (12 * 60 * 60 = 43200 seconds)
                cache.set(cache_key, rates, 43200)
                return rates
    except Exception as e:
        # Silently fail and return None, which will trigger the fallback
        pass
        
    return None
