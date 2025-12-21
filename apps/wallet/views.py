from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from core.utils.responses import SuccessResponse, ErrorResponse
from core.utils.decorators import cache_response
from .models import Wallet, Deposit, Withdrawal
from .services import WalletService
from .selectors import WalletQueries
from .serializers import (
    WalletSerializer, DepositSerializer, WithdrawalSerializer,
    TransactionSerializer, DepositRequestSerializer, WithdrawalRequestSerializer
)
import uuid


class WalletView(generics.RetrieveAPIView):
    """Get wallet balance and info"""
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return WalletService.get_user_wallet(self.request.user)
    
    @cache_response(timeout=30)
    def retrieve(self, request, *args, **kwargs):
        wallet = self.get_object()
        serializer = self.get_serializer(wallet)
        
        return SuccessResponse(data=serializer.data)


class TransactionHistoryView(generics.ListAPIView):
    """Get transaction history"""
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return WalletService.get_transaction_history(self.request.user)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return SuccessResponse(data=serializer.data)


class DepositView(generics.CreateAPIView):
    """Create deposit request"""
    serializer_class = DepositRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Process deposit
        transaction = WalletService.deposit(
            user=request.user,
            amount=data['amount'],
            payment_method=data['payment_method'],
            payment_reference=data.get('payment_reference', str(uuid.uuid4())),
            metadata=data.get('metadata', {})
        )
        
        # Create deposit record
        deposit = Deposit.objects.create(
            user=request.user,
            amount=data['amount'],
            payment_method=data['payment_method'],
            payment_reference=data.get('payment_reference', str(uuid.uuid4())),
            status='COMPLETED',
            metadata=data.get('metadata', {}),
            completed_at=timezone.now()
        )
        
        return SuccessResponse(
            data={
                'transaction': TransactionSerializer(transaction).data,
                'deposit': DepositSerializer(deposit).data
            },
            message='Deposit successful',
            status=status.HTTP_201_CREATED
        )


class WithdrawalView(generics.CreateAPIView):
    """Create withdrawal request"""
    serializer_class = WithdrawalRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        # Check KYC status
        if request.user.kyc_status != 'VERIFIED':
            return ErrorResponse(
                message='KYC verification required for withdrawals',
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check 2FA if enabled
        if request.user.two_factor_enabled:
            # TODO: Implement 2FA verification
            pass
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Initiate withdrawal
        lock = WalletService.initiate_withdrawal(
            user=request.user,
            amount=data['amount'],
            payment_method=data['payment_method'],
            payment_details=data['payment_details']
        )
        
        # Create withdrawal record
        withdrawal = Withdrawal.objects.create(
            user=request.user,
            amount=data['amount'],
            payment_method=data['payment_method'],
            payment_details=data['payment_details'],
            status='PENDING',
            metadata=data.get('metadata', {})
        )
        
        return SuccessResponse(
            data={
                'withdrawal': WithdrawalSerializer(withdrawal).data
            },
            message='Withdrawal request submitted',
            status=status.HTTP_201_CREATED
        )