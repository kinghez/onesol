from django.shortcuts import render
from django.http import JsonResponse
from . import currency
from . import dashboard_views  # re-export


from .models import HeroSlide, Testimonial, FAQ, ContactMessage, SiteSettings

def home(request):
    """Render the home page."""
    from products.models import Category, Tool
    hero_slides = HeroSlide.objects.filter(is_active=True).order_by('order')
    categories = Category.objects.filter(tools__is_active=True).distinct()
    total_tools_count = Tool.objects.filter(is_active=True).count()
    testimonials = Testimonial.objects.filter(is_active=True).order_by('order', '-id')
    faqs = FAQ.objects.filter(is_active=True).order_by('order', 'id')
    return render(request, 'home/index.html', {
        'hero_slides': hero_slides,
        'categories': categories,
        'total_tools_count': total_tools_count,
        'testimonials': testimonials,
        'faqs': faqs,
    })


def about_us(request):
    """Redirect to homepage about section."""
    from django.shortcuts import redirect
    return redirect('/#aboutUs')


def features_page(request):
    """Render the features page."""
    return render(request, 'home/features.html')


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


def refer_and_earn(request):
    """Render Refer & Earn page."""
    cfg = SiteSettings.get()
    return render(request, 'pages/refer_and_earn.html', {
        'custom_content': cfg.referral_page_content,
        'site_settings': cfg,
    })


from django.contrib import messages
from django.shortcuts import redirect

def contact_us(request):
    """Render and handle Contact Us page."""
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        category = request.POST.get('category', '').strip()
        message_text = request.POST.get('message', '').strip()

        if full_name and email and message_text:
            # Save Contact Inquiry to database table for Admin access
            ContactMessage.objects.create(
                full_name=full_name,
                email=email,
                subject=subject,
                category=category or 'General Inquiry',
                message=message_text,
            )

            try:
                from analytics.models import ActivityLog
                ActivityLog.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    activity_type='user_signup',
                    description=f'Contact Form Inquiry from {full_name} ({email}) - Category: {category} - Subject: {subject}',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            except Exception:
                pass

            messages.success(request, f"Thank you {full_name}! Your message has been received. Our team will get back to you shortly.")
            return redirect('contact_us')
        else:
            messages.error(request, "Please fill in all required fields.")

    return render(request, 'pages/contact.html')
