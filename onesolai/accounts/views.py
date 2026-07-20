from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import User, Profile


def login_view(request):
    """Handle login page GET and POST. Uses email as the login field."""
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        # Django's authenticate needs username field when using custom USERNAME_FIELD
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', '')
            return redirect(next_url if next_url else 'dashboard:home')
        else:
            messages.error(request, 'Invalid email or password. Please try again.')

    return render(request, 'accounts/login.html')


def signup_view(request):
    """Handle signup page GET and POST."""
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    referrer_name = None
    ref_code = request.GET.get('ref', '')
    if ref_code:
        profile = Profile.objects.filter(referral_code__iexact=ref_code).first()
        if profile:
            referrer_name = profile.user.get_full_name() or profile.user.email

    if request.method == 'POST':
        fullname = request.POST.get('fullname', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        terms = request.POST.get('terms')
        post_ref_code = request.POST.get('ref_code', '').strip()
        if not post_ref_code and ref_code:
            post_ref_code = ref_code
        
        # Preserve the ref_code for the template in case of errors
        ref_code = post_ref_code
        if ref_code:
            profile = Profile.objects.filter(referral_code__iexact=ref_code).first()
            if profile:
                referrer_name = profile.user.get_full_name() or profile.user.email

        # Validation
        referrer_profile = None
        if post_ref_code:
            referrer_profile = Profile.objects.filter(referral_code__iexact=post_ref_code).first()
            if not referrer_profile:
                messages.error(request, 'The referral code provided is invalid.')
        if not terms:
            messages.error(request, 'You must accept the Terms and Privacy Policy.')
        elif not fullname or not email or not password:
            messages.error(request, 'All fields are required.')
        elif len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'An account with this email already exists.')
        elif post_ref_code and not referrer_profile:
            # We already added an error message above for invalid referral code
            pass
        else:
            parts = fullname.split(' ', 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ''

            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            # Profile is auto-created by post_save signal in models.py
            profile = user.profile
            
            # Save detected location/currency if provided
            detected_country = request.POST.get('detected_country', '').strip()
            detected_currency = request.POST.get('detected_currency', '').strip()
            
            # If frontend didn't detect, fallback to backend IP geoloc
            if not detected_country:
                from .utils import get_client_ip, get_location_data_from_ip
                ip = get_client_ip(request)
                location_data = get_location_data_from_ip(ip)
                if location_data['country']:
                    detected_country = location_data['country']
                if location_data['currency']:
                    detected_currency = location_data['currency']

            if detected_country:
                profile.country_preference = detected_country
            if detected_currency:
                profile.currency_preference = detected_currency
                
            # Default to Nigeria if still empty to ensure map renders nicely
            if not profile.country_preference:
                profile.country_preference = 'Nigeria'
                
            profile.save()

            # Handle referral
            if referrer_profile:
                from . import models as acc_models
                acc_models.Referral.objects.create(
                    referrer=referrer_profile.user,
                    referred_user=user,
                    status='pending',
                )

            # Send Welcome Email and In-App Notification
            from core.email_utils import send_alert
            send_alert(
                user=user,
                title="Welcome to OneSol AI Hub!",
                message="Thank you for joining OneSol AI Hub. Explore our premium AI and SaaS tools at unbeatable prices today!",
                notification_type='system'
            )

            login(request, user)
            messages.success(request, f'Welcome to OneSol AI Hub, {first_name}!')
            return redirect('dashboard:home')

    context = {
        'ref_code': ref_code,
        'referrer_name': referrer_name
    }
    return render(request, 'accounts/signup.html', context)


def logout_view(request):
    """Log the user out and redirect to home."""
    logout(request)
    return redirect('home')
