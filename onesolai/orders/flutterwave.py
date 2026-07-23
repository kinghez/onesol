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


def get_headers():
    key = get_secret_key()
    return {
        'Authorization': f'Bearer {key}',
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

    try:
        if transaction_id:
            url = f'https://api.flutterwave.com/v3/transactions/{transaction_id}/verify'
        elif reference:
            url = f'https://api.flutterwave.com/v3/transactions/verify_by_address?tx_ref={reference}'
        else:
            raise ValueError("Transaction ID or reference is required for verification.")

        resp = requests.get(
            url,
            headers=get_headers(),
            timeout=30,
        )
        data = resp.json()
    except requests.RequestException as e:
        raise ValueError(f'Flutterwave verification network error: {e}')

    if data.get('status') != 'success':
        raise ValueError(f'Flutterwave verify error: {data.get("message", "Verification failed")}')

    return data.get('data', {})
