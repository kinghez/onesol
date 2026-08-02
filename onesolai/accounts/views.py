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

            # Send Professional HTML Welcome Email
            from core.email_utils import send_welcome_email
            send_welcome_email(user)

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


from django.views.decorators.http import require_POST
from django.http import JsonResponse
import json

@require_POST
def update_location_session(request):
    """
    Endpoint called by frontend IP detection script to update user currency, country, and country code.
    Saves in session and updates user profile if logged in.
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    currency = data.get('currency', '').strip().upper()
    country = data.get('country', '').strip()
    country_code = data.get('country_code', '').strip().upper()

    if currency:
        request.session['detected_currency'] = currency
    if country:
        request.session['detected_country'] = country
    if country_code:
        request.session['detected_country_code'] = country_code

    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        profile = request.user.profile
        changed = False
        if currency and profile.currency_preference != currency:
            profile.currency_preference = currency
            changed = True
        if country and profile.country_preference != country:
            profile.country_preference = country
            changed = True
        if changed:
            profile.save()

    return JsonResponse({
        'status': 'success',
        'currency': currency or request.session.get('detected_currency', 'NGN'),
        'country_code': country_code or request.session.get('detected_country_code', ''),
    })


import secrets
import requests
from django.urls import reverse
from core.models import SiteSettings
from analytics.models import ActivityLog


def google_login_view(request):
    """Initiate Google OAuth 2.0 Login redirect."""
    cfg = SiteSettings.get()
    client_id = (cfg.google_client_id or '').strip()

    if not client_id:
        messages.error(request, 'Google Sign-In is not configured yet. Please configure Google Client ID in Site Settings.')
        return redirect('accounts:login')

    # Construct redirect URI
    redirect_uri = request.build_absolute_uri(reverse('accounts:google_callback'))
    if request.headers.get('x-forwarded-proto') == 'https' or (not ('127.0.0.1' in redirect_uri or 'localhost' in redirect_uri) and redirect_uri.startswith('http://')):
        redirect_uri = redirect_uri.replace('http://', 'https://')

    state = secrets.token_urlsafe(16)
    request.session['google_oauth_state'] = state

    google_auth_url = (
        'https://accounts.google.com/o/oauth2/v2/auth?'
        f'client_id={client_id}&'
        f'response_type=code&'
        f'scope=openid%20email%20profile&'
        f'redirect_uri={redirect_uri}&'
        f'state={state}&'
        'prompt=select_account'
    )
    return redirect(google_auth_url)


def google_callback_view(request):
    """Handle callback from Google OAuth 2.0."""
    code = request.GET.get('code')
    state = request.GET.get('state')
    saved_state = request.session.pop('google_oauth_state', None)

    if not code or not state or state != saved_state:
        messages.error(request, 'Authentication failed or request timed out. Please try again.')
        return redirect('accounts:login')

    cfg = SiteSettings.get()
    client_id = (cfg.google_client_id or '').strip()
    client_secret = (cfg.google_client_secret or '').strip()
    redirect_uri = request.build_absolute_uri(reverse('accounts:google_callback'))
    if request.headers.get('x-forwarded-proto') == 'https' or (not ('127.0.0.1' in redirect_uri or 'localhost' in redirect_uri) and redirect_uri.startswith('http://')):
        redirect_uri = redirect_uri.replace('http://', 'https://')

    # Exchange code for access token
    token_url = 'https://oauth2.googleapis.com/token'
    token_data = {
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
    }

    try:
        token_res = requests.post(token_url, data=token_data, timeout=10)
        token_json = token_res.json()
        access_token = token_json.get('access_token')

        if not access_token:
            messages.error(request, 'Failed to obtain access token from Google.')
            return redirect('accounts:login')

        # Fetch user info from Google
        user_info_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        user_info_res = requests.get(user_info_url, headers={'Authorization': f'Bearer {access_token}'}, timeout=10)
        user_info = user_info_res.json()

        email = (user_info.get('email') or '').strip().lower()
        first_name = (user_info.get('given_name') or '').strip()
        last_name = (user_info.get('family_name') or '').strip()

        if not email:
            messages.error(request, 'Could not retrieve email from your Google account.')
            return redirect('accounts:login')

        # Get or create user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email,
                'first_name': first_name,
                'last_name': last_name,
                'is_active': True,
            }
        )

        if created:
            user.set_unusable_password()
            user.save()

            # Automatically capture detected country & currency for Google signup
            from accounts.utils import get_client_ip, get_location_data_from_ip
            ip = get_client_ip(request)
            loc = get_location_data_from_ip(ip)

            country = request.session.get('detected_country') or loc.get('country') or 'Nigeria'
            currency = request.session.get('detected_currency') or loc.get('currency') or 'NGN'

            profile = getattr(user, 'profile', None)
            if profile:
                profile.country_preference = country
                profile.currency_preference = currency
                profile.save()

            ActivityLog.log(
                action_type='user_signup',
                title='New User Registered via Google',
                details=f'User {user.email} signed up using Google OAuth 2.0 (Location: {country})',
                user=user,
                severity='success'
            )
            from core.email_utils import send_welcome_email
            send_welcome_email(user)
        else:
            ActivityLog.log(
                action_type='user_login',
                title='User Logged In via Google',
                details=f'User {user.email} signed in using Google OAuth 2.0',
                user=user,
                severity='info'
            )

        # Log in the user
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, f'Welcome back, {user.first_name or user.email}!')
        return redirect('dashboard:home')

    except Exception as e:
        messages.error(request, f'Google Sign-In error: {e}')
        return redirect('accounts:login')

