from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.utils import timezone
from django.contrib.auth import logout
from core.utils.responses import SuccessResponse, ErrorResponse
from .models import User, UserProfile, RefreshToken, LoginHistory
from .serializers import (
    UserSerializer, UserProfileSerializer, RegisterSerializer,
    LoginSerializer, RefreshTokenSerializer, ChangePasswordSerializer,
    KYCUploadSerializer
)
from .tokens import create_refresh_token, verify_refresh_token
import uuid


class RegisterView(generics.CreateAPIView):
    """User registration"""
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return SuccessResponse(
            data={'user': UserSerializer(user).data},
            message='Registration successful',
            status=status.HTTP_201_CREATED
        )


class LoginView(APIView):
    """User login with JWT"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
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