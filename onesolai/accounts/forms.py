import logging
import threading
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.core.mail import EmailMultiAlternatives
from django.template import loader

logger = logging.getLogger(__name__)
UserModel = get_user_model()


class CustomPasswordResetForm(PasswordResetForm):
    """
    Custom password reset form that:
    1. Normalizes and strips whitespace from email input.
    2. Overrides get_users() to match active users even if they do not yet
       have a usable password (e.g. users who signed up via Google OAuth or social login).
    3. Sends reset emails asynchronously via threading so the HTTP request finishes immediately.
    """

    def clean_email(self):
        email = self.cleaned_data.get("email", "")
        return email.strip().lower()

    def get_users(self, email):
        """
        Given an email, return matching active user(s) who should receive a reset.
        Includes users even if they have an unusable password (e.g. social/OAuth signups)
        so they can set a password.
        """
        email_field_name = UserModel.get_email_field_name()
        active_users = UserModel._default_manager.filter(**{
            f"{email_field_name}__iexact": email,
            "is_active": True,
        })
        return active_users

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        """
        Send a django.core.mail.EmailMultiAlternatives to `to_email`.
        Renders plain-text body and optional HTML alternative.
        Dispatches in a background thread to prevent slow email APIs from blocking the request.
        """
        subject = loader.render_to_string(subject_template_name, context)
        subject = "".join(subject.splitlines())
        body = loader.render_to_string(email_template_name, context)

        email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
        if html_email_template_name is not None:
            html_email = loader.render_to_string(html_email_template_name, context)
            email_message.attach_alternative(html_email, "text/html")

        def _send():
            try:
                email_message.send(fail_silently=False)
                logger.info(f"Password reset email sent to {to_email}")
            except Exception as e:
                logger.error(f"Failed to send password reset email to {to_email}: {e}")

        threading.Thread(target=_send, daemon=True).start()
