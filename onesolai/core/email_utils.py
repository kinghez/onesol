import threading
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from notifications.models import Notification

def _send_email_thread(subject, message, recipient_list, html_message=None):
    """Function to send email in a background thread."""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=True,
        )
    except Exception as e:
        print(f"Failed to send email: {e}")

def send_async_email(subject, message, recipient_list, html_message=None):
    """Sends an email asynchronously so it doesn't block the request."""
    threading.Thread(
        target=_send_email_thread,
        args=(subject, message, recipient_list, html_message),
        daemon=True
    ).start()

def send_welcome_email(user):
    """
    Sends a rich, beautifully designed HTML welcome email to newly registered users.
    """
    try:
        from core.models import SiteSettings
        cfg = SiteSettings.get()
        site_name = cfg.site_name or 'OneSol AI Hub'
        support_email = cfg.support_email or 'support@onesolai.com'
        site_url = (cfg.site_url or 'https://onesolai.com').rstrip('/')

        logo_url = ''
        if cfg.site_logo:
            try:
                logo_url = cfg.site_logo.url
                if not logo_url.startswith('http'):
                    logo_url = f"{site_url}{logo_url}"
            except Exception:
                logo_url = ''

        user_name = user.get_full_name() or user.first_name or user.email.split('@')[0]

        context = {
            'user': user,
            'user_name': user_name,
            'site_name': site_name,
            'support_email': support_email,
            'site_url': site_url,
            'logo_url': logo_url,
        }

        html_content = render_to_string('emails/welcome_email.html', context)
        plain_text = strip_tags(html_content)
        subject = f"Welcome to {site_name}! 🚀 Your Gateway to Premium AI & SaaS Tools"

        # Create In-App Notification
        Notification.objects.create(
            user=user,
            title=f"Welcome to {site_name}!",
            message="Thank you for joining. Explore our catalog of 100+ premium AI tools at unbeatable prices!",
            notification_type='system',
            action_url='/tools/'
        )

        if user.email:
            send_async_email(
                subject=subject,
                message=plain_text,
                recipient_list=[user.email],
                html_message=html_content
            )

    except Exception as e:
        print(f"Error sending welcome email: {e}")

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
        email_body = f"Hello {user.get_full_name() or 'User'},\n\n{message}\n\nBest regards,\nThe OneSol AI Hub Team"
        send_async_email(subject, email_body, [user.email])
