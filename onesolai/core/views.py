from django.shortcuts import render
from django.http import JsonResponse
from . import currency
from . import dashboard_views  # re-export


from .models import HeroSlide

def home(request):
    """Render the home page."""
    hero_slides = HeroSlide.objects.filter(is_active=True).order_by('order')
    return render(request, 'home/index.html', {'hero_slides': hero_slides})


def api_currency_rates(request):
    """
    Returns currency conversion rates from NGN as JSON.
    Used by the frontend JS to display localized prices.
    """
    return JsonResponse({'currencies': currency.get_currency_list()})
