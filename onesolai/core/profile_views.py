from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Profile

@login_required(login_url='/auth/login/')
def profile_settings_view(request):
    user = request.user
    profile = user.profile

    if request.method == 'POST':
        # Update User fields
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        
        user.first_name = first_name
        user.last_name = last_name
        user.save(update_fields=['first_name', 'last_name'])
        
        # Update Profile fields
        currency_preference = request.POST.get('currency_preference', 'NGN').strip()
        country_preference = request.POST.get('country_preference', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        
        # Payout & Financial Settings
        bank_name = request.POST.get('bank_name', '').strip()
        account_number = request.POST.get('account_number', '').strip()
        account_name = request.POST.get('account_name', '').strip()
        crypto_wallet_address = request.POST.get('crypto_wallet_address', '').strip()
        crypto_network = request.POST.get('crypto_network', 'USDT (TRC20)').strip()
        preferred_withdrawal_method = request.POST.get('preferred_withdrawal_method', 'bank').strip()
        
        profile.currency_preference = currency_preference
        profile.country_preference = country_preference
        profile.phone_number = phone_number
        profile.bank_name = bank_name
        profile.account_number = account_number
        profile.account_name = account_name
        profile.crypto_wallet_address = crypto_wallet_address
        profile.crypto_network = crypto_network
        profile.preferred_withdrawal_method = preferred_withdrawal_method
        
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
            
        profile.save()

        if 'avatar' in request.FILES and profile.avatar:
            try:
                profile.avatar_url = profile.avatar.url
                profile.save(update_fields=['avatar_url'])
            except Exception:
                pass
        messages.success(request, "Your profile and payout settings have been updated successfully.")
        return redirect('dashboard:profile')

    # Comprehensive list of major world and African currencies
    all_currencies = [
        {'code': 'NGN', 'name': 'Nigeria'}, {'code': 'USD', 'name': 'United States'},
        {'code': 'EUR', 'name': 'Eurozone'}, {'code': 'GBP', 'name': 'United Kingdom'},
        {'code': 'GHS', 'name': 'Ghana'}, {'code': 'KES', 'name': 'Kenya'},
        {'code': 'ZAR', 'name': 'South Africa'}, {'code': 'CAD', 'name': 'Canada'},
        {'code': 'AUD', 'name': 'Australia'}, {'code': 'JPY', 'name': 'Japan'},
        {'code': 'CHF', 'name': 'Switzerland'}, {'code': 'CNY', 'name': 'China'},
        {'code': 'INR', 'name': 'India'}, {'code': 'BRL', 'name': 'Brazil'},
        {'code': 'MXN', 'name': 'Mexico'}, {'code': 'RUB', 'name': 'Russia'},
        {'code': 'KRW', 'name': 'South Korea'}, {'code': 'SGD', 'name': 'Singapore'},
        {'code': 'NZD', 'name': 'New Zealand'}, {'code': 'ZMW', 'name': 'Zambia'},
        {'code': 'UGX', 'name': 'Uganda'}, {'code': 'RWF', 'name': 'Rwanda'},
        {'code': 'TZS', 'name': 'Tanzania'}, {'code': 'XOF', 'name': 'West African CFA'},
        {'code': 'XAF', 'name': 'Central African CFA'}, {'code': 'MAD', 'name': 'Morocco'},
        {'code': 'EGP', 'name': 'Egypt'}, {'code': 'DZD', 'name': 'Algeria'},
        {'code': 'SDG', 'name': 'Sudan'}, {'code': 'AOA', 'name': 'Angola'}
    ]
    
    # Sort by code
    all_currencies = sorted(all_currencies, key=lambda x: x['code'])

    context = {
        'currencies': all_currencies,
    }
    return render(request, 'dashboard/profile.html', context)


from django.contrib.auth import update_session_auth_hash

@login_required(login_url='/auth/login/')
def security_view(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not request.user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return redirect('dashboard:security')

        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect('dashboard:security')

        if len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect('dashboard:security')

        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user)  # Keep user logged in
        
        messages.success(request, "Password updated successfully.")
        return redirect('dashboard:security')
    return render(request, 'dashboard/security.html')


@login_required(login_url='/auth/login/')
def support_view(request):
    if request.method == 'POST':
        messages.success(request, "Support ticket created. We will get back to you shortly.")
        return redirect('dashboard:support')
    return render(request, 'dashboard/support.html')


from django.http import JsonResponse
from accounts.utils import COUNTRY_TO_CURRENCY

@login_required(login_url='/auth/login/')
def update_location_preference_view(request):
    """AJAX endpoint for Location Mismatch Modal Popup."""
    if request.method == 'POST':
        action = request.POST.get('action')
        new_country = request.POST.get('country', '').strip()
        new_currency = request.POST.get('currency', '').strip()

        if action == 'accept' and new_country:
            profile = request.user.profile
            profile.country_preference = new_country
            if new_currency:
                profile.currency_preference = new_currency.upper()
            else:
                profile.currency_preference = COUNTRY_TO_CURRENCY.get(new_country, 'USD')
            profile.save()
            request.session['location_switch_dismissed'] = True
            return JsonResponse({
                'status': 'success',
                'country': profile.country_preference,
                'currency': profile.currency_preference
            })
        else:
            request.session['location_switch_dismissed'] = True
            return JsonResponse({'status': 'dismissed'})
    return JsonResponse({'status': 'invalid'}, status=400)
