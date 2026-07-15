import threading
from django.core.mail import send_mail
from django.conf import settings
from notifications.models import Notification

def _send_email_thread(subject, message, recipient_list):
    """Function to send email in a background thread."""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=True,
        )
    except Exception as e:
        print(f"Failed to send email: {e}")

def send_async_email(subject, message, recipient_list):
    """Sends an email asynchronously so it doesn't block the request."""
    threading.Thread(
        target=_send_email_thread,
        args=(subject, message, recipient_list),
        daemon=True
    ).start()

def send_alert(user, title, message, notification_type='system', send_email=True):
    """
    Creates an in-app notification for the user and optionally sends an email.
    """
    # 1. Create In-App Notification
    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type
    )

    # 2. Send Async Email
    if send_email and user.email:
        subject = f"OneSol AI Hub - {title}"
        # Adding a simple signature
        email_body = f"Hello {user.get_full_name() or 'User'},\n\n{message}\n\nBest regards,\nThe OneSol AI Hub Team"
        send_async_email(subject, email_body, [user.email])
