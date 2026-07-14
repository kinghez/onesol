"""
Paystack API helper for OneSol AI Hub.
All keys are loaded from SiteSettings (admin-configurable), never hardcoded.
"""
import uuid
import requests
from decimal import Decimal


def _get_settings():
    """Lazily load SiteSettings to avoid circular imports."""
    from core.models import SiteSettings
    return SiteSettings.get()


def get_headers():
    cfg = _get_settings()
    return {
        'Authorization': f'Bearer {cfg.paystack_secret_key}',
        'Content-Type': 'application/json',
    }


def generate_reference():
    """Generate a unique payment reference."""
    return f'ONESOL-{uuid.uuid4().hex[:12].upper()}'


def initialize_transaction(email: str, amount_ngn: Decimal, reference: str, callback_url: str, metadata: dict = None):
    """
    Initialize a Paystack transaction.
    Returns (authorization_url, reference) on success, raises ValueError on failure.
    Amount is in NGN (Decimal); Paystack expects kobo (int).
    """
    amount_kobo = int(amount_ngn * 100)  # convert NGN → kobo
    payload = {
        'email': email,
        'amount': amount_kobo,
        'reference': reference,
        'callback_url': callback_url,
        'currency': 'NGN',
        'metadata': metadata or {},
        'channels': ['card', 'bank', 'ussd', 'qr', 'mobile_money', 'bank_transfer'],
    }
    try:
        resp = requests.post(
            'https://api.paystack.co/transaction/initialize',
            json=payload,
            headers=get_headers(),
            timeout=30,
        )
        data = resp.json()
    except requests.RequestException as e:
        raise ValueError(f'Paystack network error: {e}')

    if not data.get('status'):
        raise ValueError(f'Paystack error: {data.get("message", "Unknown error")}')

    return data['data']['authorization_url'], data['data']['reference']


def verify_transaction(reference: str):
    """
    Verify a Paystack transaction by reference.
    Returns the full data dict on success, raises ValueError on failure.
    """
    try:
        resp = requests.get(
            f'https://api.paystack.co/transaction/verify/{reference}',
            headers=get_headers(),
            timeout=30,
        )
        data = resp.json()
    except requests.RequestException as e:
        raise ValueError(f'Paystack network error: {e}')

    if not data.get('status'):
        raise ValueError(f'Paystack verify error: {data.get("message", "Unknown error")}')

    return data['data']
