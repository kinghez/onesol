"""
Currency conversion utilities for OneSol AI Hub.
Converts from NGN (base currency) to any supported African / global currency.
"""
from django.conf import settings
from decimal import Decimal


def get_rate(currency: str) -> Decimal:
    """Return NGN-to-currency conversion rate (from settings fallback)."""
    rates = settings.CURRENCY_RATES_FALLBACK
    rate = rates.get(currency.upper(), 1)
    return Decimal(str(rate))


def convert_from_ngn(amount_ngn: Decimal, currency: str) -> Decimal:
    """Convert an NGN amount to the target currency."""
    if currency.upper() == 'NGN':
        return amount_ngn
    rate = get_rate(currency)
    return (amount_ngn * rate).quantize(Decimal('0.01'))


def convert_to_ngn(amount: Decimal, currency: str) -> Decimal:
    """Convert an amount in a foreign currency back to NGN."""
    if currency.upper() == 'NGN':
        return amount
    rate = get_rate(currency)
    if rate == 0:
        return amount
    return (amount / rate).quantize(Decimal('0.01'))


def format_price(amount_ngn: Decimal, currency: str = 'NGN') -> str:
    """Return a formatted price string e.g. '₦5,000' or 'GH₵220'."""
    converted = convert_from_ngn(amount_ngn, currency)
    symbol = settings.CURRENCY_SYMBOLS.get(currency.upper(), currency)
    return f"{symbol}{converted:,.2f}"


def get_currency_list() -> list:
    """Return all supported currencies as a list of dicts for JS/templates."""
    symbols = settings.CURRENCY_SYMBOLS
    rates = settings.CURRENCY_RATES_FALLBACK
    return [
        {
            'code': code,
            'symbol': symbols.get(code, code),
            'rate_from_ngn': rate,
        }
        for code, rate in rates.items()
    ]
