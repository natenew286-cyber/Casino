import secrets
import os
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import User, OTP, PasswordResetToken
from .tasks import send_email_task


def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    return f"{secrets.randbelow(900000) + 100000:06d}"


def create_otp(user: User, otp_type: str, expiry_minutes: int = None) -> OTP:
    """Create and store an OTP for a user"""
    import logging
    logger = logging.getLogger(__name__)

    # Generate new OTP
    otp_code = generate_otp()
    if expiry_minutes is None:
        expiry_minutes = getattr(settings, 'OTP_EXPIRY_MINUTES', 10)
    
    # Use timezone.now() which is aware if USE_TZ=True
    expires_at = timezone.now() + timedelta(minutes=expiry_minutes)

    # Invalidate any previous unused OTPs of the same type (avoid user confusion / multiple valid codes).
    OTP.objects.filter(user=user, otp_type=otp_type, is_used=False).update(is_used=True)
    
    otp = OTP.objects.create(
        user=user,
        otp_code=otp_code,
        otp_type=otp_type,
        expires_at=expires_at
    )

    logger.info(
        f"Created OTP for user {user.email} (type={otp_type}) "
        f"expires_at={expires_at} (expiry_minutes={expiry_minutes})"
    )
    
    return otp


def verify_otp(user: User, otp_code: str, otp_type: str) -> bool:
    """Verify an OTP code"""
    import logging
    from django.utils import timezone
    logger = logging.getLogger(__name__)

    try:
        cleaned_code = (otp_code or "").strip()
        now = timezone.now()

        # Only accept unused + unexpired OTPs (fast-path).
        otp = (
            OTP.objects.filter(
                user=user,
                otp_code=cleaned_code,
                otp_type=otp_type,
                is_used=False,
                expires_at__gt=now,
            )
            .order_by("-created_at")
            .first()
        )

        if not otp:
            # Extra logging to help diagnose "invalid vs expired vs used".
            latest = (
                OTP.objects.filter(
                    user=user,
                    otp_code=cleaned_code,
                    otp_type=otp_type,
                )
                .order_by("-created_at")
                .first()
            )
            if not latest:
                logger.warning(
                    f"OTP verification failed: No OTP found for user {user.email} (type={otp_type}) with code {cleaned_code!r}"
                )
            elif latest.is_used:
                logger.warning(f"OTP verification failed: OTP already used for user {user.email} (type={otp_type})")
            else:
                logger.warning(
                    f"OTP verification failed: OTP expired for user {user.email} (type={otp_type}). "
                    f"Expiry: {latest.expires_at}, Now: {now}"
                )
            return False

        # Mark as used atomically (prevents races / double verification).
        updated = OTP.objects.filter(pk=otp.pk, is_used=False).update(is_used=True)
        if updated != 1:
            logger.warning(f"OTP verification failed: OTP already used (race) for user {user.email} (type={otp_type})")
            return False

        logger.info(f"OTP verified successfully for user {user.email} (type={otp_type})")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying OTP: {str(e)}")
        return False


def send_otp_email(user: User, otp_code: str, otp_type: str) -> bool:
    """Send OTP via email using Celery task"""
    site_name = os.getenv('SITE_NAME', 'Casino')
    
    if otp_type == 'EMAIL_VERIFICATION':
        subject = os.getenv('EMAIL_VERIFICATION_SUBJECT', 'Email Verification Code')
        template_name = 'emails/otp_email.html'
        context = {
            'user': user,
            'otp_code': otp_code,
            'expiry_minutes': getattr(settings, 'OTP_EXPIRY_MINUTES', 10),
            'site_name': site_name,
            'subject': subject
        }
    elif otp_type == 'PASSWORD_RESET':
        subject = os.getenv('PASSWORD_RESET_OTP_SUBJECT', 'Password Reset Code')
        template_name = 'emails/otp_email.html'
        context = {
            'user': user,
            'otp_code': otp_code,
            'expiry_minutes': getattr(settings, 'OTP_EXPIRY_MINUTES', 10),
            'site_name': site_name,
            'subject': subject
        }
    
    # Render email body
    try:
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)
    except Exception as e:
        # Fallback if template fails
        plain_message = f"Your OTP is {otp_code}"
        html_message = None

    # Send asynchronously
    try:
        # Check if Celery worker is available/Redis is connected
        from celery.exceptions import OperationalError
        import socket
        
        send_email_task.apply_async(
            kwargs={
                'subject': subject,
                'message': plain_message,
                'recipient_list': [user.email],
                'html_message': html_message
            },
            retry=True,
            retry_policy={
                'max_retries': 3,
                'interval_start': 0,
                'interval_step': 0.2,
                'interval_max': 0.2,
            }
        )
    except (OperationalError, socket.error, ConnectionRefusedError) as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.critical(f"CRITICAL: Redis/Celery connection failed. Cannot send OTP email to {user.email}.")
        logger.critical(f"  REDIS_URL from settings: {getattr(settings, 'REDIS_URL', 'NOT SET')}")
        logger.critical(f"  CELERY_BROKER_URL from settings: {getattr(settings, 'CELERY_BROKER_URL', 'NOT SET')}")
        logger.critical(f"  Error: {str(e)}")
        return False
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to queue OTP email for {user.email}: {str(e)}", exc_info=True)
        return False
    
    return True


def create_password_reset_token(user: User) -> PasswordResetToken:
    """Create a password reset token"""
    # Deactivate previous unused tokens
    PasswordResetToken.objects.filter(
        user=user,
        is_used=False
    ).update(is_used=True)
    
    # Generate secure token
    token = secrets.token_urlsafe(32)
    expires_at = timezone.now() + timedelta(hours=1)  # 1 hour expiry
    
    reset_token = PasswordResetToken.objects.create(
        user=user,
        token=token,
        expires_at=expires_at
    )
    
    return reset_token


def verify_password_reset_token(token: str) -> PasswordResetToken | None:
    """Verify a password reset token"""
    try:
        reset_token = PasswordResetToken.objects.get(
            token=token,
            is_used=False
        )
        
        if not reset_token.is_valid():
            return None
        
        return reset_token
    except PasswordResetToken.DoesNotExist:
        return None


def send_password_reset_email(user: User, reset_token: PasswordResetToken) -> bool:
    """Send password reset token via email using Celery task"""
    subject = os.getenv('PASSWORD_RESET_SUBJECT', 'Password Reset Token')
    site_name = os.getenv('SITE_NAME', 'Casino')
    
    context = {
        'user': user,
        'token': reset_token.token,
        'expiry_hours': getattr(settings, 'PASSWORD_RESET_TOKEN_EXPIRY_HOURS', 1),
        'site_name': site_name,
        'subject': subject
    }
    
    # Render email body
    try:
        html_message = render_to_string('emails/password_reset_email.html', context)
        plain_message = strip_tags(html_message)
    except Exception as e:
        plain_message = f"Your password reset token is {reset_token.token}"
        html_message = None
    
    # Send asynchronously
    try:
        from celery.exceptions import OperationalError
        import socket
        
        send_email_task.apply_async(
            kwargs={
                'subject': subject,
                'message': plain_message,
                'recipient_list': [user.email],
                'html_message': html_message
            },
            retry=True,
            retry_policy={
                'max_retries': 3,
                'interval_start': 0,
                'interval_step': 0.2,
                'interval_max': 0.2,
            }
        )
    except (OperationalError, socket.error, ConnectionRefusedError) as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.critical(f"CRITICAL: Redis/Celery connection failed. Cannot send password reset email to {user.email}.")
        logger.critical(f"  REDIS_URL from settings: {getattr(settings, 'REDIS_URL', 'NOT SET')}")
        logger.critical(f"  CELERY_BROKER_URL from settings: {getattr(settings, 'CELERY_BROKER_URL', 'NOT SET')}")
        logger.critical(f"  Error: {str(e)}")
        return False
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to queue password reset email for {user.email}: {str(e)}", exc_info=True)
        return False
    
    return True
