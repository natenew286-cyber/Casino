from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken as JwtRefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import logout
from django.conf import settings
from core.utils.responses import SuccessResponse, ErrorResponse
from .models import User, UserProfile, RefreshToken, LoginHistory
from .serializers import (
    UserSerializer, UserProfileSerializer, RegisterSerializer,
    LoginSerializer, RefreshTokenSerializer, ChangePasswordSerializer,
    KYCUploadSerializer, OTPVerificationSerializer, ResendOTPSerializer,
    PasswordResetRequestSerializer, PasswordResetSerializer
)
from .tokens import create_refresh_token, verify_refresh_token
from .services import (
    create_otp, verify_otp, send_otp_email,
    create_password_reset_token, verify_password_reset_token,
    send_password_reset_email
)
import uuid
import hashlib


class RegisterView(generics.CreateAPIView):
    """User registration with OTP"""
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check if email already exists
        email = serializer.validated_data['email']
        if User.objects.filter(email=email).exists():
            return ErrorResponse(
                message=f'The email address {email} is already registered. Please use a different email or try logging in instead.',
                status=status.HTTP_400_BAD_REQUEST,
                errors={'email': 'This email is already registered'}
            )
        
        # Create user in pending state (not verified)
        user = serializer.save()
        user.is_verified = False
        user.is_active = True  # Allow login but require verification
        user.save()
        
        # Generate and send OTP
        otp = create_otp(user, 'EMAIL_VERIFICATION', expiry_minutes=settings.OTP_EXPIRY_MINUTES)
        send_otp_email(user, otp.otp_code, 'EMAIL_VERIFICATION')
        
        return SuccessResponse(
            data={'user': UserSerializer(user).data},
        message=f'Registration successful! A verification OTP has been sent to {email}. Please check your inbox and verify your email address within {settings.OTP_EXPIRY_MINUTES} minutes to activate your account.',
            status=status.HTTP_201_CREATED
        )


class LoginView(APIView):
    """User login with JWT"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # Check if user exists in database
        if not User.objects.filter(email=user.email).exists():
            return ErrorResponse(
                message='Invalid credentials. The email address or password you entered is incorrect. Please check your credentials and try again.',
                status=status.HTTP_404_NOT_FOUND,
                errors={'email': 'User account not found'}
            )
        
        # Check if account is verified
        if not user.is_verified:
            return ErrorResponse(
                message=f'Your email address {user.email} has not been verified yet. Please check your inbox for the verification OTP or request a new one using the resend OTP endpoint.',
                status=status.HTTP_403_FORBIDDEN,
                errors={'verification': 'Email verification required', 'email': user.email}
            )
        
        # Generate tokens
        refresh = JwtRefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        
        # Create refresh token record
        device_id = request.META.get('HTTP_USER_AGENT', 'unknown')
        refresh_token_record = create_refresh_token(
            user=user,
            token=str(refresh),
            device_id=device_id,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Record login history
        LoginHistory.objects.create(
            user=user,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            device_fingerprint=device_id,
            success=True
        )
        
        return SuccessResponse(
            data={
                'access_token': access_token,
                'refresh_token': str(refresh),
                'user': UserSerializer(user).data,
                'token_info': {
                    'access_token_expires_in': settings.JWT_ACCESS_TOKEN_LIFETIME,
                    'refresh_token_expires_in': settings.JWT_REFRESH_TOKEN_LIFETIME
                }
            },
            message=f'Login successful! Welcome back, {user.get_full_name() or user.email}. Your access token is valid for {settings.JWT_ACCESS_TOKEN_LIFETIME} seconds.'
        )


class LogoutView(APIView):
    """User logout"""
    def post(self, request):
        # Blacklist refresh token if provided
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            try:
                token = JwtRefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass
        
        logout(request)
        return SuccessResponse(
            message='You have been successfully logged out. Your session has been terminated and all tokens have been invalidated. Please log in again to access your account.'
        )


class RefreshTokenView(TokenRefreshView):
    """Refresh JWT token"""
    serializer_class = RefreshTokenSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        refresh_token = serializer.validated_data['refresh_token']
        
        # Verify refresh token
        token_record = verify_refresh_token(refresh_token)
        if not token_record:
            return ErrorResponse(
                message='The refresh token provided is invalid or has expired. Please log in again to obtain new tokens.',
                status=status.HTTP_401_UNAUTHORIZED,
                errors={'refresh_token': 'Invalid or expired token'}
            )
        
        # Generate new tokens
        refresh = JwtRefreshToken.for_user(token_record.user)
        access_token = str(refresh.access_token)
        refresh_str = str(refresh)
        
        # Update refresh token
        token_record.token = hashlib.sha256(refresh_str.encode()).hexdigest()
        token_record.expires_at = timezone.now() + timedelta(days=7)
        token_record.save()
        
        return SuccessResponse(
            data={
                'access_token': access_token,
                'refresh_token': refresh_str,
                'token_info': {
                    'access_token_expires_in': settings.JWT_ACCESS_TOKEN_LIFETIME,
                    'refresh_token_expires_in': settings.JWT_REFRESH_TOKEN_LIFETIME
                }
            },
            message=f'Tokens refreshed successfully. Your new access token is valid for {settings.JWT_ACCESS_TOKEN_LIFETIME} seconds.'
        )


class ProfileView(generics.RetrieveUpdateAPIView):
    """User profile management"""
    serializer_class = UserProfileSerializer
    
    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        user_serializer = UserSerializer(request.user)
        
        return SuccessResponse(
            data={
                'user': user_serializer.data,
                'profile': serializer.data
            },
            message=f'Profile information retrieved successfully for {request.user.get_full_name() or request.user.email}.'
        )
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return SuccessResponse(
            data=serializer.data,
            message='Your profile has been updated successfully. The changes have been saved and are now active.'
        )


class ChangePasswordView(APIView):
    """Change user password"""
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return SuccessResponse(
            message='Your password has been changed successfully. Please use your new password for future logins. For security reasons, you may need to log in again with your new password.'
        )


class KYCUploadView(APIView):
    """Upload KYC documents"""
    def post(self, request):
        serializer = KYCUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.kyc_status = 'PENDING'
        user.save()
        
        # Update profile with KYC documents
        profile = user.profile
        profile.document_type = serializer.validated_data['document_type']
        profile.document_front = serializer.validated_data['document_front']
        
        if serializer.validated_data.get('document_back'):
            profile.document_back = serializer.validated_data['document_back']
        
        profile.selfie_with_document = serializer.validated_data['selfie_with_document']
        profile.save()
        
        return SuccessResponse(
            message='KYC documents have been uploaded successfully. Your documents are now under review. You will be notified once the verification process is complete, which typically takes 24-48 hours.',
            data={'kyc_status': 'PENDING', 'user_id': user.id}
        )


class OTPVerificationView(APIView):
    """Verify OTP for email verification"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        otp_code = serializer.validated_data['otp_code']
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return ErrorResponse(
                message=f'No user account found with the email address {email}. Please check the email address and try again, or register a new account.',
                status=status.HTTP_404_NOT_FOUND,
                errors={'email': 'User not found'}
            )
        
        # Verify OTP
        if verify_otp(user, otp_code, 'EMAIL_VERIFICATION'):
            user.is_verified = True
            user.save()
            return SuccessResponse(
                data={'user': UserSerializer(user).data},
                message=f'Email verification successful! Your email address {email} has been verified and your account is now active. You can now log in to access all features.'
            )
        else:
            return ErrorResponse(
                message=f'The OTP code you provided is invalid or has expired. OTP codes expire after {settings.OTP_EXPIRY_MINUTES} minutes. Please request a new OTP code and try again.',
                status=status.HTTP_400_BAD_REQUEST,
                errors={'otp_code': 'Invalid or expired OTP'}
            )


class ResendOTPView(APIView):
    """Resend OTP for email verification"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return ErrorResponse(
                message=f'No user account found with the email address {email}. Please check the email address and try again, or register a new account.',
                status=status.HTTP_404_NOT_FOUND,
                errors={'email': 'User not found'}
            )
        
        # Check if already verified
        if user.is_verified:
            return ErrorResponse(
                message=f'Your email address {email} is already verified. No further action is required. You can proceed to log in.',
                status=status.HTTP_400_BAD_REQUEST,
                errors={'verification': 'Email already verified'}
            )
        
        # Generate and send new OTP
        otp = create_otp(user, 'EMAIL_VERIFICATION', expiry_minutes=settings.OTP_EXPIRY_MINUTES)
        send_otp_email(user, otp.otp_code, 'EMAIL_VERIFICATION')
        return SuccessResponse(
            message=f'A new verification OTP has been sent to {email}. Please check your inbox (and spam folder) for the code. The OTP will expire in {settings.OTP_EXPIRY_MINUTES} minutes.'
        )


class PasswordResetRequestView(APIView):
    """Request password reset"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal if email exists for security
            return SuccessResponse(
                message='If an account with this email address exists, a password reset link has been sent. Please check your inbox and follow the instructions to reset your password. The link will expire in 1 hour.'
            )
        
        # Create password reset token
        reset_token = create_password_reset_token(user)
        send_password_reset_email(user, reset_token)
        
        return SuccessResponse(
            message=f'A password reset link has been sent to {email}. Please check your inbox (and spam folder) and click the link to reset your password. The link will expire in {settings.PASSWORD_RESET_TOKEN_EXPIRY_HOURS} hour(s).'
        )


class PasswordResetView(APIView):
    """Reset password using token"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        
        # Verify token
        reset_token = verify_password_reset_token(token)
        if not reset_token:
            return ErrorResponse(
                message='The password reset token is invalid or has expired. Password reset links expire after 1 hour. Please request a new password reset link and try again.',
                status=status.HTTP_400_BAD_REQUEST,
                errors={'token': 'Invalid or expired reset token'}
            )
        
        # Update password
        user = reset_token.user
        user.set_password(new_password)
        user.save()
        
        # Mark token as used
        reset_token.is_used = True
        reset_token.save()
        
        return SuccessResponse(
            message=f'Password reset successful! Your password has been changed for the account {user.email}. You can now log in with your new password.'
        )