from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from orders.models import Order, RefundRequest

@login_required(login_url='/auth/login/')
def request_refund_view(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id, user=request.user)
        reason = request.POST.get('reason', '').strip()
        
        if not reason:
            messages.error(request, "Please provide a reason for the refund request.")
            return redirect('dashboard:order_history')
            
        if order.status != 'paid':
            messages.error(request, "Only paid orders can be refunded.")
            return redirect('dashboard:order_history')
            
        # Check if already requested
        if RefundRequest.objects.filter(order=order, status='pending').exists():
            messages.warning(request, "You already have a pending refund request for this order.")
            return redirect('dashboard:order_history')
            
        RefundRequest.objects.create(
            order=order,
            reason=reason
        )
        
        messages.success(request, "Refund request submitted successfully. Our team will review it shortly.")
        
    return redirect('dashboard:order_history')
