"""Referral dashboard and withdrawal views."""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import timezone
from decimal import Decimal, InvalidOperation

from accounts.models import Referral, WithdrawalRequest
from core.models import SiteSettings


@login_required(login_url='/auth/login/')
def referrals_view(request):
    """Premium referral dashboard page."""
    user = request.user
    profile = user.profile
    cfg = SiteSettings.get()

    # All referrals made by this user
    referrals = (
        Referral.objects
        .filter(referrer=user)
        .select_related('referred_user')
        .order_by('-date_referred')
    )

    total_referrals = referrals.count()
    successful_referrals = referrals.filter(status__in=['rewarded', 'successful']).count()
    total_earned = referrals.filter(status='rewarded').count() * cfg.referral_commission_ngn

    # Withdrawal requests
    withdrawals = WithdrawalRequest.objects.filter(user=user).order_by('-created_at')
    has_pending_withdrawal = withdrawals.filter(status='pending').exists()

    # Build absolute referral link
    site_url = cfg.site_url.rstrip('/')
    referral_link = f'{site_url}/auth/signup/?ref={profile.referral_code or ""}'

    context = {
        'profile': profile,
        'referrals': referrals,
        'withdrawals': withdrawals,
        'total_referrals': total_referrals,
        'successful_referrals': successful_referrals,
        'total_earned': total_earned,
        'available_balance': profile.earnings,
        'referral_link': referral_link,
        'referral_code': profile.referral_code or '',
        'min_withdrawal': cfg.min_withdrawal_ngn,
        'commission_per_referral': cfg.referral_commission_ngn,
        'has_pending_withdrawal': has_pending_withdrawal,
    }
    return render(request, 'dashboard/referrals.html', context)


@login_required(login_url='/auth/login/')
@require_POST
def withdrawal_request_view(request):
    """Handle withdrawal request form submission."""
    user = request.user
    profile = user.profile
    cfg = SiteSettings.get()

    # Check for pending request
    if WithdrawalRequest.objects.filter(user=user, status='pending').exists():
        messages.error(request, 'You already have a pending withdrawal request. Please wait for it to be processed.')
        return redirect('dashboard:referrals')

    # Parse amount
    try:
        amount = Decimal(request.POST.get('amount', '0'))
    except InvalidOperation:
        messages.error(request, 'Invalid withdrawal amount.')
        return redirect('dashboard:referrals')

    # Validate minimum
    if amount < cfg.min_withdrawal_ngn:
        messages.error(request, f'Minimum withdrawal is NGN {cfg.min_withdrawal_ngn:,.0f}.')
        return redirect('dashboard:referrals')

    # Validate sufficient balance
    if profile.earnings < amount:
        messages.error(request, 'Insufficient earnings balance for this withdrawal amount.')
        return redirect('dashboard:referrals')

    bank_name = request.POST.get('bank_name', '').strip()
    account_number = request.POST.get('account_number', '').strip()
    account_name = request.POST.get('account_name', '').strip()

    if not all([bank_name, account_number, account_name]):
        messages.error(request, 'Please fill in all bank details.')
        return redirect('dashboard:referrals')

    # Create withdrawal request
    WithdrawalRequest.objects.create(
        user=user,
        amount=amount,
        bank_name=bank_name,
        account_number=account_number,
        account_name=account_name,
    )

    messages.success(request, f'Withdrawal request for NGN {amount:,.0f} submitted! We will process it within 24 hours.')
    return redirect('dashboard:referrals')
