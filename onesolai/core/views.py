from django.shortcuts import render
from django.http import JsonResponse
from . import currency
from . import dashboard_views  # re-export


def home(request):
    """Render the home page."""
    return render(request, 'home/index.html')


def api_currency_rates(request):
    """
    Returns currency conversion rates from NGN as JSON.
    Used by the frontend JS to display localized prices.
    """
    return JsonResponse({'currencies': currency.get_currency_list()})
