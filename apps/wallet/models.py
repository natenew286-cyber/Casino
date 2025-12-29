from django.db import models
from django.conf import settings
import uuid
from decimal import Decimal


class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    locked_balance = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    currency = models.CharField(max_length=3, default='USD')
    version = models.IntegerField(default=0)  # For optimistic locking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.balance} {self.currency}"
    
    def available_balance(self):
        return self.balance - self.locked_balance


class WalletTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('BET', 'Bet'),
        ('WIN', 'Win'),
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
        ('BONUS', 'Bonus'),
        ('ADMIN_ADJUSTMENT', 'Admin Adjustment'),
        ('REFUND', 'Refund'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    balance_before = models.DecimalField(max_digits=20, decimal_places=8)
    balance_after = models.DecimalField(max_digits=20, decimal_places=8)
    reference_type = models.CharField(max_length=50, null=True, blank=True)
    reference_id = models.UUIDField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    idempotency_key = models.UUIDField(unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['wallet', '-created_at']),
            models.Index(fields=['idempotency_key']),
            models.Index(fields=['type', 'created_at']),
            models.Index(fields=['reference_type', 'reference_id']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.type} - {self.amount} - {self.created_at}"


class WalletLock(models.Model):
    LOCK_TYPES = (
        ('BET_PENDING', 'Bet Pending'),
        ('WITHDRAWAL_PENDING', 'Withdrawal Pending'),
        ('DISPUTE', 'Dispute'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='locks')
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    lock_type = models.CharField(max_length=20, choices=LOCK_TYPES)
    reference_id = models.UUIDField()
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['wallet']),
            models.Index(fields=['reference_id']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.lock_type} - {self.amount}"


class Deposit(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='deposits')
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    currency = models.CharField(max_length=3, default='USD')
    payment_method = models.CharField(max_length=50)
    payment_reference = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', 'created_at']),
        ]


class Withdrawal(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='withdrawals')
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    currency = models.CharField(max_length=3, default='USD')
    payment_method = models.CharField(max_length=50)
    payment_details = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    admin_notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', 'created_at']),
        ]