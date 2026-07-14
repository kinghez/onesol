from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Profile, WalletTransaction
from django.conf import settings
from core.models import SiteSettings
import uuid
import requests

@login_required(login_url='/auth/login/')
def wallet_dashboard_view(request):
    user = request.user
    profile = user.profile
    transactions = user.wallet_transactions.all()
    
    context = {
        'profile': profile,
        'transactions': transactions,
    }
    return render(request, 'dashboard/wallet.html', context)


@login_required(login_url='/auth/login/')
def wallet_topup_initialize(request):
    if request.method == 'POST':
        amount_str = request.POST.get('amount')
        try:
            amount = float(amount_str)
            if amount < 100:
                messages.error(request, "Minimum top-up amount is NGN 100.")
                return redirect('dashboard:wallet')
        except (ValueError, TypeError):
            messages.error(request, "Invalid amount.")
            return redirect('dashboard:wallet')
            
        cfg = SiteSettings.get()
        secret_key = cfg.paystack_secret_key
        
        if not secret_key:
            messages.error(request, "Payment gateway is not configured.")
            return redirect('dashboard:wallet')
            
        reference = f"TOPUP_{uuid.uuid4().hex[:12].upper()}"
        
        # Initialize Paystack
        headers = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json"
        }
        
        # Build the callback URL (using absolute URI if possible, or relative)
        callback_url = request.build_absolute_uri('/dashboard/wallet/topup/callback/')
        
        data = {
            "email": request.user.email,
            "amount": int(amount * 100),  # Paystack uses kobo
            "reference": reference,
            "callback_url": callback_url,
            "metadata": {
                "user_id": request.user.id,
                "type": "wallet_topup"
            }
        }
        
        resp = requests.post("https://api.paystack.co/transaction/initialize", headers=headers, json=data)
        
        if resp.status_code == 200:
            res_data = resp.json()
            auth_url = res_data['data']['authorization_url']
            return redirect(auth_url)
        else:
            messages.error(request, "Failed to initialize payment. Please try again.")
            return redirect('dashboard:wallet')
            
    return redirect('dashboard:wallet')


@login_required(login_url='/auth/login/')
def wallet_topup_callback(request):
    reference = request.GET.get('reference')
    if not reference:
        messages.error(request, "Payment reference missing.")
        return redirect('dashboard:wallet')
        
    cfg = SiteSettings.get()
    secret_key = cfg.paystack_secret_key
    
    headers = {
        "Authorization": f"Bearer {secret_key}",
    }
    
    resp = requests.get(f"https://api.paystack.co/transaction/verify/{reference}", headers=headers)
    
    if resp.status_code == 200:
        res_data = resp.json()
        if res_data['data']['status'] == 'success':
            amount_ngn = res_data['data']['amount'] / 100
            
            # Check if transaction already exists
            if not WalletTransaction.objects.filter(reference=reference).exists():
                # Add to wallet balance
                profile = request.user.profile
                profile.wallet_balance += type(profile.wallet_balance)(str(amount_ngn))
                profile.save(update_fields=['wallet_balance'])
                
                # Record transaction
                WalletTransaction.objects.create(
                    user=request.user,
                    transaction_type='deposit',
                    amount_ngn=amount_ngn,
                    reference=reference,
                    description="Wallet Top-up via Paystack"
                )
                
                # Notify User
                from notifications.models import Notification
                Notification.objects.create(
                    user=request.user,
                    title="Wallet Funded",
                    message=f"Your wallet has been successfully credited with NGN {amount_ngn:,.2f}.",
                    notification_type='system',
                    action_url='/dashboard/wallet/'
                )
                
                messages.success(request, f"Successfully added NGN {amount_ngn:,.2f} to your wallet.")
            else:
                messages.info(request, "This transaction has already been processed.")
        else:
            messages.error(request, "Payment was not successful.")
    else:
        messages.error(request, "Failed to verify payment with Paystack.")
        
    return redirect('dashboard:wallet')
