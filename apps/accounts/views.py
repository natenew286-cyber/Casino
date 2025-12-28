from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.utils import timezone
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
                message='Email already registered',
                status=status.HTTP_400_BAD_REQUEST
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
            message='Registration successful. Please verify your email with the OTP sent to your inbox.',
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
                message='User does not exist',
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if account is verified
        if not user.is_verified:
            return ErrorResponse(
                message='Please verify your email before logging in',
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
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
        
        return SuccessResponse(data={
            'access_token': access_token,
            'refresh_token': refresh_token_record.token,
            'user': UserSerializer(user).data
        }, message='Login successful')


class LogoutView(APIView):
    """User logout"""
    def post(self, request):
        # Blacklist refresh token if provided
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass
        
        logout(request)
        return SuccessResponse(message='Logout successful')


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
                message='Invalid or expired refresh token',
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Generate new tokens
        refresh = RefreshToken.for_user(token_record.user)
        access_token = str(refresh.access_token)
        
        # Update refresh token
        token_record.token = str(refresh)
        token_record.expires_at = timezone.now() + timezone.timedelta(days=7)
        token_record.save()
        
        return SuccessResponse(data={
            'access_token': access_token,
            'refresh_token': token_record.token
        }, message='Token refreshed')


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
        
        return SuccessResponse(data={
            'user': user_serializer.data,
            'profile': serializer.data
        })
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return SuccessResponse(data=serializer.data, message='Profile updated')


class ChangePasswordView(APIView):
    """Change user password"""
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return SuccessResponse(message='Password changed successfully')


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
        
        return SuccessResponse(message='KYC documents uploaded successfully')


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
                message='User not found',
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify OTP
        if verify_otp(user, otp_code, 'EMAIL_VERIFICATION'):
            user.is_verified = True
            user.save()
            return SuccessResponse(
                data={'user': UserSerializer(user).data},
                message='Email verified successfully'
            )
        else:
            return ErrorResponse(
                message='Invalid or expired OTP',
                status=status.HTTP_400_BAD_REQUEST
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
                message='User not found',
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already verified
        if user.is_verified:
            return ErrorResponse(
                message='Email already verified',
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate and send new OTP
        otp = create_otp(user, 'EMAIL_VERIFICATION', expiry_minutes=settings.OTP_EXPIRY_MINUTES)
        send_otp_email(user, otp.otp_code, 'EMAIL_VERIFICATION')
        
        return SuccessResponse(
            message='OTP sent successfully. Please check your email.'
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
                message='If the email exists, a password reset link has been sent.'
            )
        
        # Create password reset token
        reset_token = create_password_reset_token(user)
        send_password_reset_email(user, reset_token)
        
        return SuccessResponse(
            message='Password reset link sent to your email.'
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
                message='Invalid or expired reset token',
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update password
        user = reset_token.user
        user.set_password(new_password)
        user.save()
        
        # Mark token as used
        reset_token.is_used = True
        reset_token.save()
        
        return SuccessResponse(
            message='Password reset successfully'
        )