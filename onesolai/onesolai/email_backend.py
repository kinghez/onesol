"""
Custom Django Email Backend using Resend API.
Replaces SMTP — no SMTP server needed, works on Render free tier.
"""
import resend
import os
import logging
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings

logger = logging.getLogger(__name__)


class ResendEmailBackend(BaseEmailBackend):
    """
    Django email backend that sends via Resend API.
    Set RESEND_API_KEY in your environment variables.
    """

    def open(self):
        pass

    def close(self):
        pass

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        api_key = getattr(settings, 'RESEND_API_KEY', '') or os.environ.get('RESEND_API_KEY', '')
        if not api_key:
            logger.error("RESEND_API_KEY is not set. Cannot send emails.")
            return 0

        resend.api_key = api_key
        sent_count = 0

        for message in email_messages:
            try:
                # Build recipients
                to_list = message.to or []
                if not to_list:
                    continue

                # Build the email payload
                params = {
                    "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
                    "to": to_list,
                    "subject": message.subject,
                    "text": message.body,
                }

                # Add CC and BCC if present
                if message.cc:
                    params["cc"] = message.cc
                if message.bcc:
                    params["bcc"] = message.bcc
                if message.reply_to:
                    params["reply_to"] = [str(r) for r in message.reply_to]

                # Add HTML alternative if present
                for content, mimetype in getattr(message, 'alternatives', []):
                    if mimetype == 'text/html':
                        params["html"] = content
                        break

                resend.Emails.send(params)
                sent_count += 1
                logger.info(f"Email sent via Resend to {', '.join(to_list)} | Subject: {message.subject}")

            except Exception as e:
                logger.error(f"Failed to send email via Resend to {message.to}: {e}")
                if not self.fail_silently:
                    raise

        return sent_count
