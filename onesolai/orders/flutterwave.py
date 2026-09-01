"""
Flutterwave API helper for OneSol AI Hub.
All keys are loaded from SiteSettings (admin-configurable), with fallbacks.
"""
import uuid
import requests
from decimal import Decimal
from django.conf import settings


def _get_settings():
    """Lazily load SiteSettings to avoid circular imports."""
    from core.models import SiteSettings
    return SiteSettings.get()


def get_secret_key():
    cfg = _get_settings()
    key = cfg.flutterwave_secret_key.strip()
    if not key:
        key = getattr(settings, 'FLUTTERWAVE_SECRET_KEY', '')
    return key


from django.core.cache import cache

def _get_v4_access_token():
    cfg = _get_settings()
    client_id = cfg.flutterwave_public_key.strip()
    client_secret = cfg.flutterwave_secret_key.strip()
    if not client_id or not client_secret:
        raise ValueError("Flutterwave V4 Client ID and Client Secret are required in Site Settings.")

    cache_key = 'flutterwave_v4_access_token'
    token = cache.get(cache_key)
    if token:
        return token

    url = 'https://idp.flutterwave.com/realms/flutterwave/protocol/openid-connect/token'
    
    # Flutterwave IdP uses Keycloak, which often prefers HTTP Basic Auth for client credentials
    payload = {
        'grant_type': 'client_credentials',
    }
    
    # Try basic auth first
    try:
        resp = requests.post(
            url, 
            data=payload, 
            auth=(client_id, client_secret),
            timeout=15
        )
        if resp.status_code == 401:
            # Fallback to putting them in the body if basic auth fails
            payload['client_id'] = client_id
            payload['client_secret'] = client_secret
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            resp = requests.post(url, data=payload, headers=headers, timeout=15)
            
        if resp.status_code != 200:
            raise ValueError(f"Failed to authenticate with Flutterwave V4: HTTP {resp.status_code} - {resp.text}")
            
        data = resp.json()
        token = data.get('access_token')
        if not token:
            raise ValueError(f"No access_token found in V4 auth response. Response: {resp.text}")
        
        # Cache for 9 minutes (540 seconds)
        cache.set(cache_key, token, 540)
        return token
    except requests.RequestException as e:
        error_msg = f"Network error during V4 auth: {e}"
        if hasattr(e, 'response') and e.response is not None:
            error_msg += f" | Body: {e.response.text}"
        raise ValueError(error_msg)

def get_headers():
    cfg = _get_settings()
    api_version = getattr(cfg, 'flutterwave_api_version', 'v3')
    
    if api_version == 'v4':
        token = _get_v4_access_token()
    else:
        token = get_secret_key()

    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }


def generate_reference():
    """Generate a unique Flutterwave payment reference."""
    return f'ONESOL-FLW-{uuid.uuid4().hex[:12].upper()}'


def initialize_transaction(email: str, amount: Decimal, currency: str, reference: str, callback_url: str, metadata: dict = None, customer_name: str = ''):
    """
    Initialize a Flutterwave v3 transaction.
    Returns (link, reference) on success, raises ValueError on failure.
    """
    secret_key = get_secret_key()
    if not secret_key:
        raise ValueError("Flutterwave secret key is not configured in Site Settings.")

    cfg = _get_settings()
    site_logo = cfg.site_logo.url if cfg.site_logo else ''
    if site_logo and not site_logo.startswith('http'):
        site_logo = f"{cfg.site_url.rstrip('/')}{site_logo}"

    payload = {
        'tx_ref': reference,
        'amount': float(amount),
        'currency': currency.upper(),
        'redirect_url': callback_url,
        'meta': metadata or {},
        'customer': {
            'email': email,
            'name': customer_name or email.split('@')[0],
        },
        'customizations': {
            'title': cfg.site_name or 'OneSol AI Hub',
            'description': 'Tool Subscription Purchase',
            'logo': site_logo or 'https://onesolai.com/static/assets/logo_s.png'
        }
    }

    try:
        resp = requests.post(
            'https://api.flutterwave.com/v3/payments',
            json=payload,
            headers=get_headers(),
            timeout=30,
        )
        data = resp.json()
    except requests.RequestException as e:
        raise ValueError(f'Flutterwave network error: {e}')

    if data.get('status') != 'success':
        raise ValueError(f'Flutterwave error: {data.get("message", "Unknown error")}')

    link = data.get('data', {}).get('link')
    if not link:
        raise ValueError('Flutterwave returned an invalid authorization link.')

    return link, reference


def verify_transaction(transaction_id: str = None, reference: str = None):
    """
    Verify a Flutterwave transaction by ID or reference.
    Returns transaction data dict on success, raises ValueError on failure.
    """
    secret_key = get_secret_key()
    if not secret_key:
        raise ValueError("Flutterwave secret key is not configured.")

    if transaction_id and str(transaction_id).strip().lower() in ['null', 'undefined', 'none', '']:
        transaction_id = None
    if reference and str(reference).strip().lower() in ['null', 'undefined', 'none', '']:
        reference = None

    try:
        data = None
        if transaction_id:
            try:
                url = f'https://api.flutterwave.com/v3/transactions/{transaction_id}/verify'
                resp = requests.get(url, headers=get_headers(), timeout=30)
                data = resp.json()
            except Exception:
                data = None

        if (not data or data.get('status') != 'success') and reference:
            url = f'https://api.flutterwave.com/v3/transactions/verify_by_address?tx_ref={reference}'
            resp = requests.get(url, headers=get_headers(), timeout=30)
            data = resp.json()

        if not data:
            raise ValueError("Transaction ID or reference is required for verification.")

    except requests.RequestException as e:
        raise ValueError(f'Flutterwave verification network error: {e}')

    if data.get('status') != 'success':
        raise ValueError(f'Flutterwave verify error: {data.get("message", "Verification failed")}')

    return data.get('data', {})
