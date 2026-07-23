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


from django.views.decorators.http import require_POST
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import json
from .models import NewsletterSubscriber


@require_POST
def subscribe_newsletter(request):
    """API view to subscribe a user's email to the newsletter."""
    try:
        data = json.loads(request.body.decode('utf-8'))
        email = data.get('email', '').strip().lower()
    except Exception:
        email = request.POST.get('email', '').strip().lower()

    if not email:
        return JsonResponse({'status': 'error', 'message': 'Please enter a valid email address.'}, status=400)

    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'status': 'error', 'message': 'Invalid email address format.'}, status=400)

    subscriber, created = NewsletterSubscriber.objects.get_or_create(email=email)
    if not created:
        if not subscriber.is_active:
            subscriber.is_active = True
            subscriber.save()
            return JsonResponse({'status': 'success', 'message': 'Welcome back! Your subscription has been reactivated.'})
        return JsonResponse({'status': 'info', 'message': 'You are already subscribed to our newsletter!'})

    return JsonResponse({'status': 'success', 'message': 'Thank you for subscribing to OneSol AI Hub!'})


from .models import SiteSettings, NewsletterSubscriber


def privacy_policy(request):
    """Render Privacy Policy page."""
    cfg = SiteSettings.get()
    return render(request, 'legal/privacy_policy.html', {'custom_content': cfg.privacy_policy_content})


def terms_of_service(request):
    """Render Terms of Service page."""
    cfg = SiteSettings.get()
    return render(request, 'legal/terms_of_service.html', {'custom_content': cfg.terms_of_service_content})


def refund_policy(request):
    """Render Refund Policy page."""
    cfg = SiteSettings.get()
    return render(request, 'legal/refund_policy.html', {'custom_content': cfg.refund_policy_content})
