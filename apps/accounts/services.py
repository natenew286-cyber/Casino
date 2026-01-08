import random
import secrets
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import User, OTP, PasswordResetToken
from .tasks import send_email_task


def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    return str(random.randint(100000, 999999))


def create_otp(user: User, otp_type: str, expiry_minutes: int = None) -> OTP:
    """Create and store an OTP for a user"""
    # Deactivate previous OTPs of the same type
    OTP.objects.filter(
        user=user,
        otp_type=otp_type,
        is_used=False
    ).update(is_used=True)
    
    # Generate new OTP
    otp_code = generate_otp()
    if expiry_minutes is None:
        expiry_minutes = getattr(settings, 'OTP_EXPIRY_MINUTES', 10)
    expires_at = timezone.now() + timezone.timedelta(minutes=expiry_minutes)
    
    otp = OTP.objects.create(
        user=user,
        otp_code=otp_code,
        otp_type=otp_type,
        expires_at=expires_at
    )
    
    return otp


def verify_otp(user: User, otp_code: str, otp_type: str) -> bool:
    """Verify an OTP code"""
    try:
        otp = OTP.objects.get(
            user=user,
            otp_code=otp_code,
            otp_type=otp_type,
            is_used=False
        )
        
        if not otp.is_valid():
            return False
        
        # Mark OTP as used
        otp.is_used = True
        otp.save()
        
        return True
    except OTP.DoesNotExist:
        return False


def send_otp_email(user: User, otp_code: str, otp_type: str) -> bool:
    """Send OTP via email using Celery task"""
    if otp_type == 'EMAIL_VERIFICATION':
        subject = 'Email Verification Code'
        message = f'''
Hello {user.email},

Your email verification code is: {otp_code}

This code will expire in 10 minutes.

If you did not request this code, please ignore this email.

Best regards,
Casino Team
'''
    elif otp_type == 'PASSWORD_RESET':
        subject = 'Password Reset Code'
        message = f'''
Hello {user.email},

Your password reset code is: {otp_code}

This code will expire in 10 minutes.

If you did not request a password reset, please ignore this email.

Best regards,
Casino Team
'''
    # Send asynchronously
    try:
        # Check if Celery worker is available/Redis is connected
        # This is a basic check to fail fast if the broker is down
        from celery.exceptions import OperationalError
        import socket
        
        send_email_task.apply_async(
            kwargs={
                'subject': subject,
                'message': message,
                'recipient_list': [user.email]
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
        logger.critical(f"CRITICAL: Redis/Celery connection failed. Cannot send OTP email to {user.email}. Error: {str(e)}")
        # In a real production app, you might want to fallback to synchronous sending 
        # or a secondary provider here if critical.
        # For now, we return False to indicate failure.
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
    expires_at = timezone.now() + timezone.timedelta(hours=1)  # 1 hour expiry
    
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
    subject = 'Password Reset Token'
    message = f'''
Hello {user.email},

You requested to reset your password. Use the token below to reset it in the app:

{reset_token.token}

This token will expire in 1 hour.

If you did not request a password reset, please ignore this email.

Best regards,
Casino Team
'''
    
    # Send asynchronously
    try:
        from celery.exceptions import OperationalError
        import socket
        
        send_email_task.apply_async(
            kwargs={
                'subject': subject,
                'message': message,
                'recipient_list': [user.email]
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
        logger.critical(f"CRITICAL: Redis/Celery connection failed. Cannot send password reset email to {user.email}. Error: {str(e)}")
        return False
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to queue password reset email for {user.email}: {str(e)}", exc_info=True)
        return False
    
    return True
