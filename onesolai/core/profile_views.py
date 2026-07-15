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
        
        profile.currency_preference = currency_preference
        profile.country_preference = country_preference
        profile.phone_number = phone_number
        
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
            
        profile.save()
        messages.success(request, "Your profile has been updated successfully.")
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
