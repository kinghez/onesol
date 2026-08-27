from django import template
from django.conf import settings
from core.services import get_live_usd_rates

register = template.Library()

DEFAULT_RATES = {
    'USD': 1.0, 'NGN': 1500.0, 'GBP': 0.78, 'EUR': 0.92,
    'GHS': 15.4, 'KES': 129.5, 'ZAR': 18.2, 'CAD': 1.36,
    'AUD': 1.50, 'JPY': 155.0, 'INR': 83.5, 'ZMW': 26.5,
    'UGX': 3700.0, 'TZS': 2600.0, 'RWF': 1300.0, 'EGP': 48.0,
}

CURRENCY_SYMBOLS = {
    'USD': '$', 'NGN': '₦', 'GBP': '£', 'EUR': '€',
    'GHS': 'GH₵', 'KES': 'KSh', 'ZAR': 'R', 'CAD': 'CA$',
    'AUD': 'A$', 'JPY': '¥', 'INR': '₹', 'ZMW': 'ZK',
    'UGX': 'USh', 'TZS': 'TSh', 'RWF': 'FRw', 'EGP': 'E£',
    'NZD': 'NZ$', 'CHF': 'CHF', 'CNY': '¥', 'BRL': 'R$',
    'MXN': 'Mex$', 'SAR': 'SR', 'AED': 'AED', 'QAR': 'QR',
    'KWD': 'KD', 'OMR': 'OMR', 'BHD': 'BD', 'JOD': 'JD',
    'TRY': '₺', 'SGD': 'S$', 'MYR': 'RM', 'THB': '฿',
    'IDR': 'Rp', 'PHP': '₱', 'VND': '₫', 'PKR': 'Rs',
    'BDT': '৳', 'LKR': 'Rs', 'NPR': 'Rs', 'KRW': '₩',
    'HKD': 'HK$', 'TWD': 'NT$', 'ILS': '₪', 'RUB': '₽',
    'PLN': 'zł', 'SEK': 'kr', 'NOK': 'kr', 'DKK': 'kr',
    'CZK': 'Kč', 'HUF': 'Ft', 'RON': 'lei', 'BGN': 'lv',
    'UAH': '₴', 'ARS': '$', 'CLP': '$', 'COP': '$',
    'PEN': 'S/', 'UYU': '$U', 'ETB': 'Br', 'MWK': 'MK',
    'MUR': 'Rs', 'XOF': 'CFA', 'XAF': 'FCFA', 'DZD': 'DA',
    'AOA': 'Kz', 'BWP': 'P', 'NAD': 'N$', 'ZWG': 'ZiG',
    'MAD': 'MAD', 'TND': 'DT', 'LYD': 'LD', 'IQD': 'IQD',
}

def _get_rates():
    rates = get_live_usd_rates()
    if not rates:
        rates = DEFAULT_RATES.copy()
    rates['USD'] = 1.0
    return rates

@register.filter(name='convert_ngn')
def convert_ngn(amount, target_currency='NGN'):
    if amount is None or amount == '':
        amount = 0
    try:
        val = float(amount)
    except (ValueError, TypeError):
        val = 0.0

    target_currency = (target_currency or 'NGN').upper()
    rates = _get_rates()

    ngn_rate = float(rates.get('NGN', 1500.0) or 1500.0)
    usd_val = val / ngn_rate if ngn_rate else val / 1500.0

    target_rate = float(rates.get(target_currency, 1.0) if target_currency != 'USD' else 1.0)
    if target_currency == 'NGN':
        converted_val = val
    else:
        converted_val = usd_val * (target_rate or 1.0)

    symbol = CURRENCY_SYMBOLS.get(target_currency, getattr(settings, 'CURRENCY_SYMBOLS', {}).get(target_currency, target_currency))
    formatted_num = f'{converted_val:,.2f}'
    return f'{symbol} {formatted_num} {target_currency}'

@register.filter(name='convert_usd')
def convert_usd(amount, target_currency='USD'):
    if amount is None or amount == '':
        amount = 0
    try:
        val = float(amount)
    except (ValueError, TypeError):
        val = 0.0

    target_currency = (target_currency or 'USD').upper()
    rates = _get_rates()

    target_rate = float(rates.get(target_currency, 1.0) if target_currency != 'USD' else 1.0)
    if target_currency == 'USD':
        converted_val = val
    else:
        converted_val = val * (target_rate or 1.0)

    symbol = CURRENCY_SYMBOLS.get(target_currency, getattr(settings, 'CURRENCY_SYMBOLS', {}).get(target_currency, target_currency))
    formatted_num = f'{converted_val:,.2f}'
    return f'{symbol} {formatted_num} {target_currency}'

@register.filter(name='currency_symbol')
def currency_symbol(currency_code):
    code = (currency_code or 'NGN').upper()
    return CURRENCY_SYMBOLS.get(code, getattr(settings, 'CURRENCY_SYMBOLS', {}).get(code, code))
