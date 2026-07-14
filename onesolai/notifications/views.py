from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Notification

@login_required(login_url='/auth/login/')
def notifications_view(request):
    """View to list all notifications for the user."""
    notifications = request.user.notifications.all()
    context = {
        'notifications': notifications,
    }
    return render(request, 'dashboard/notifications.html', context)


@login_required(login_url='/auth/login/')
def mark_read(request, notif_id):
    """Mark a single notification as read via AJAX."""
    if request.method == 'POST':
        notif = get_object_or_404(Notification, id=notif_id, user=request.user)
        notif.is_read = True
        notif.save(update_fields=['is_read'])
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required(login_url='/auth/login/')
def mark_all_read(request):
    """Mark all notifications as read."""
    if request.method == 'POST':
        request.user.notifications.filter(is_read=False).update(is_read=True)
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required(login_url='/auth/login/')
def unread_count(request):
    """Get the unread notification count via AJAX."""
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({'count': count})
