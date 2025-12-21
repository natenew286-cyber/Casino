from django.urls import path
from .views import (
    WalletView, TransactionHistoryView,
    DepositView, WithdrawalView
)

urlpatterns = [
    path('', WalletView.as_view(), name='wallet'),
    path('transactions/', TransactionHistoryView.as_view(), name='transactions'),
    path('deposit/', DepositView.as_view(), name='deposit'),
    path('withdraw/', WithdrawalView.as_view(), name='withdraw'),
]