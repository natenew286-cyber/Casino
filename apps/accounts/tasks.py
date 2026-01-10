import os
import logging
import smtplib
import requests
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
        logger.info(f"Attempting PHP mail fallback for {recipient_email}")
        
        # Fallback: Send via PHP endpoint
        try:
            php_endpoint = getattr(settings, 'PHP_MAIL_ENDPOINT', 'http://localhost/mail/index.php')
            
            # Prepare POST data
            post_data = {
                'email_host': settings.EMAIL_HOST,
                'email_port': settings.EMAIL_PORT,
                'email_host_user': sender_email,
                'email_host_password': sender_password,
                'recipient': recipient_email,
                'subject': subject,
                'body': body,
            }
            
            # Prepare files if attachment exists
            files = None
            file_handle = None
            try:
                if attachment_path and os.path.exists(attachment_path):
                    file_handle = open(attachment_path, 'rb')
                    files = {
                        'attachment': (
                            os.path.basename(attachment_path),
                            file_handle,
                            'application/octet-stream'
                        )
                    }
                
                # Make POST request to PHP endpoint
                response = requests.post(php_endpoint, data=post_data, files=files, timeout=30)
            finally:
                # Ensure file is always closed
                if file_handle:
                    file_handle.close()
            
            # Check response
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('success', False):
                        logger.info(f"Email sent successfully to {recipient_email} via PHP endpoint")
                        return True
                    else:
                        logger.error(f"PHP endpoint returned error: {result.get('error', result.get('message', 'Unknown error'))}")
                except ValueError:
                    logger.error(f"PHP endpoint returned invalid JSON: {response.text}")
            else:
                logger.error(f"PHP endpoint returned status code {response.status_code}: {response.text}")
                
        except Exception as php_error:
            logger.error(f"PHP mail fallback failed for {recipient_email}: {str(php_error)}")
        
        return False