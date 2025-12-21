from django.urls import path
from .views import (
    RegisterView, LoginView, LogoutView, RefreshTokenView,
    ProfileView, ChangePasswordView, KYCUploadView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('refresh/', RefreshTokenView.as_view(), name='refresh'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('kyc-upload/', KYCUploadView.as_view(), name='kyc-upload'),
]