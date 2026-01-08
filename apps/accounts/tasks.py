import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

@shared_task
def send_email_task(subject, message, recipient_list, html_message=None):
    """
    Async task to send emails using Django's email backend
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
        logger.info("Email sent successfully via Django")
        return True
    except Exception as e:
        logger.error(f"Django email failed: {str(e)}")
        
        # Fallback: send to each recipient individually
        success = False
        for recipient in recipient_list:
            result = send_email(
                sender_email=settings.EMAIL_HOST_USER,
                sender_password=settings.EMAIL_HOST_PASSWORD,
                recipient_email=recipient,
                subject=subject,
                body=message,
                attachment_path=None
            )
            success = success or result
        
        return success

def send_email(sender_email, sender_password, recipient_email, subject, body, attachment_path=None):
    """
    Fallback: Send email directly via SMTP
    """
    try:
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = recipient_email
        message['Subject'] = subject
        message.attach(MIMEText(body, 'plain'))
        
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename={os.path.basename(attachment_path)}'
                )
                message.attach(part)
        
        email_host = settings.EMAIL_HOST
        email_port = settings.EMAIL_PORT
        email_use_tls = settings.EMAIL_USE_TLS
        email_use_ssl = getattr(settings, 'EMAIL_USE_SSL', False)
        
        with smtplib.SMTP(email_host, email_port) as server:
            if email_use_tls:
                server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())
        
        logger.info(f"Email sent successfully to {recipient_email} via direct SMTP")
        return True
        
    except Exception as e:
        logger.error(f"Direct SMTP failed for {recipient_email}: {str(e)}")
        return False