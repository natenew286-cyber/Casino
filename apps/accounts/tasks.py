from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_email_task(subject, message, recipient_list, html_message=None):
    """
    Async task to send emails
    """
    try:
        logger.info(f"Sending email to {recipient_list}")
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=recipient_list,
            fail_silently=False,
            html_message=html_message
        )
        return True
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        # In a real app, you might want to retry here
        return False
