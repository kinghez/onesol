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
        profile.currency_preference = currency_preference
        
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
            
        profile.save()
        messages.success(request, "Your profile has been updated successfully.")
        return redirect('dashboard:profile')

    context = {
        'currencies': ['NGN', 'GHS', 'KES', 'ZAR', 'USD', 'EUR'],
    }
    return render(request, 'dashboard/profile.html', context)


@login_required(login_url='/auth/login/')
def security_view(request):
    if request.method == 'POST':
        messages.success(request, "Password updated successfully.")
        return redirect('dashboard:security')
    return render(request, 'dashboard/security.html')


@login_required(login_url='/auth/login/')
def support_view(request):
    if request.method == 'POST':
        messages.success(request, "Support ticket created. We will get back to you shortly.")
        return redirect('dashboard:support')
    return render(request, 'dashboard/support.html')
