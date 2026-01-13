from django.utils import timezone
from datetime import timedelta
from .models import RefreshToken
import hashlib


def create_refresh_token(user, token, device_id, ip_address, user_agent=''):
    """Create and store refresh token"""
    # Hash the token before storing
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    # Deactivate previous tokens for this device
    RefreshToken.objects.filter(
        user=user,
        device_id=device_id,
        is_active=True
    ).update(is_active=False)
    
    # Create new token
    refresh_token = RefreshToken.objects.create(
        user=user,
        token=token_hash,
        device_id=device_id,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=timezone.now() + timedelta(days=7)
    )
    
    return refresh_token


def verify_refresh_token(token):
    """Verify refresh token"""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    try:
        refresh_token = RefreshToken.objects.get(
            token=token_hash,
            is_active=True,
            expires_at__gt=timezone.now()
        )
        return refresh_token
    except RefreshToken.DoesNotExist:
        return None


def revoke_refresh_token(user, token=None):
    """Revoke refresh token(s)"""
    if token:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        RefreshToken.objects.filter(
            user=user,
            token=token_hash
        ).update(is_active=False)
    else:
        # Revoke all tokens for user
        RefreshToken.objects.filter(user=user).update(is_active=False)