from django.db import transaction
from django.utils import timezone
from django.core.cache import cache
from core.exceptions import InsufficientFundsException
from core.redis.locks import DistributedLock
from .models import Wallet, WalletTransaction, WalletLock
from .exceptions import WalletException
import uuid
from decimal import Decimal


class WalletService:
    """Service for wallet operations"""
    
    @staticmethod
    def get_or_create_wallet(user):
        """Get or create wallet for user"""
        wallet, created = Wallet.objects.get_or_create(user=user)
        return wallet
    
    @staticmethod
    def get_user_wallet(user):
        """Get user wallet"""
        try:
            return Wallet.objects.get(user=user)
        except Wallet.DoesNotExist:
            return WalletService.get_or_create_wallet(user)
    
    @staticmethod
    def place_bet(user, amount, game_round_id, idempotency_key):
        """
        Place a bet with atomic transaction
        """
        # Check idempotency first (fast path)
        cache_key = f"idempotency:{idempotency_key}"
        cached_response = cache.get(cache_key)
        if cached_response:
            return cached_response
        
        # Use distributed lock for this user's wallet
        with DistributedLock(f"wallet:{user.id}", ttl=5):
            with transaction.atomic():
                # Check idempotency again (in case of race condition)
                if WalletTransaction.objects.filter(idempotency_key=idempotency_key).exists():
                    existing_txn = WalletTransaction.objects.get(idempotency_key=idempotency_key)
                    cache.set(cache_key, existing_txn, 86400)  # Cache for 24h
                    return existing_txn
                
                # Get and lock wallet
                wallet = Wallet.objects.select_for_update().get(user=user)
                
                # Validate balance
                available_balance = wallet.balance - wallet.locked_balance
                if available_balance < amount:
                    raise InsufficientFundsException("Insufficient available balance")
                
                # Record transaction
                balance_before = wallet.balance
                wallet.balance -= amount
                wallet.locked_balance += amount
                wallet.version += 1
                wallet.save()
                
                # Create transaction record
                txn = WalletTransaction.objects.create(
                    wallet=wallet,
                    type='BET',
                    amount=-amount,
                    balance_before=balance_before,
                    balance_after=wallet.balance,
                    reference_type='game_round',
                    reference_id=game_round_id,
                    metadata={'game_round_id': str(game_round_id)},
                    idempotency_key=idempotency_key
                )
                
                # Create lock record
                WalletLock.objects.create(
                    wallet=wallet,
                    amount=amount,
                    lock_type='BET_PENDING',
                    reference_id=game_round_id,
                    expires_at=timezone.now() + timezone.timedelta(minutes=5)
                )
                
                # Cache the response for idempotency
                cache.set(cache_key, txn, 86400)  # 24 hours
                
                # Clear balance cache
                cache.delete(f"wallet_balance:{user.id}")
                
                return txn
    
    @staticmethod
    def settle_bet(game_round_id, win_amount):
        """
        Settle a bet: release lock and add winnings
        """
        with transaction.atomic():
            # Get and lock the bet lock
            lock = WalletLock.objects.select_for_update().get(
                reference_id=game_round_id,
                lock_type='BET_PENDING'
            )
            
            # Get and lock the wallet
            wallet = Wallet.objects.select_for_update().get(id=lock.wallet_id)
            
            # Release locked amount
            wallet.locked_balance -= lock.amount
            
            # Add winnings if any
            win_amount_decimal = Decimal(str(win_amount))
            if win_amount_decimal > 0:
                balance_before = wallet.balance
                wallet.balance += win_amount_decimal
                wallet.version += 1
                
                # Create win transaction
                WalletTransaction.objects.create(
                    wallet=wallet,
                    type='WIN',
                    amount=win_amount_decimal,
                    balance_before=balance_before,
                    balance_after=wallet.balance,
                    reference_type='game_round',
                    reference_id=game_round_id,
                    metadata={'game_round_id': str(game_round_id)},
                    idempotency_key=uuid.uuid4()
                )
            
            wallet.save()
            lock.delete()
            
            # Clear balance cache
            cache.delete(f"wallet_balance:{wallet.user.id}")
            
            return wallet
    
    @staticmethod
    def deposit(user, amount, payment_method, payment_reference, metadata=None):
        """
        Process deposit
        """
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=user)
            
            idempotency_key = uuid.uuid4()
            
            balance_before = wallet.balance
            wallet.balance += Decimal(str(amount))
            wallet.version += 1
            wallet.save()
            
            # Record transaction
            txn = WalletTransaction.objects.create(
                wallet=wallet,
                type='DEPOSIT',
                amount=amount,
                balance_before=balance_before,
                balance_after=wallet.balance,
                reference_type='deposit',
                reference_id=payment_reference if isinstance(payment_reference, uuid.UUID) else uuid.uuid4(),
                metadata={
                    'payment_method': payment_method,
                    'payment_reference': str(payment_reference),
                    **(metadata or {})
                },
                idempotency_key=idempotency_key
            )
            
            # Clear balance cache
            cache.delete(f"wallet_balance:{user.id}")
            
            return txn
    
    @staticmethod
    def initiate_withdrawal(user, amount, payment_method, payment_details):
        """
        Initiate withdrawal request
        """
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=user)
            
            # Check available balance
            available_balance = wallet.balance - wallet.locked_balance
            if available_balance < amount:
                raise InsufficientFundsException("Insufficient available balance")
            
            # Lock the amount
            wallet.locked_balance += amount
            wallet.version += 1
            wallet.save()
            
            # Create lock record
            lock = WalletLock.objects.create(
                wallet=wallet,
                amount=amount,
                lock_type='WITHDRAWAL_PENDING',
                reference_id=uuid.uuid4(),
                expires_at=timezone.now() + timezone.timedelta(hours=24)
            )
            
            # Clear balance cache
            cache.delete(f"wallet_balance:{user.id}")
            
            return lock
    
    @staticmethod
    def get_balance(user, use_cache=True):
        """
        Get user balance with optional caching
        """
        if use_cache:
            cache_key = f"wallet_balance:{user.id}"
            cached_balance = cache.get(cache_key)
            if cached_balance is not None:
                return Decimal(cached_balance)
        
        wallet = WalletService.get_user_wallet(user)
        
        if use_cache:
            cache.set(cache_key, str(wallet.balance), 60)  # Cache for 1 minute
        
        return wallet.balance
    
    @staticmethod
    def get_transaction_history(user, limit=100, offset=0):
        """
        Get user transaction history
        """
        wallet = WalletService.get_user_wallet(user)
        transactions = WalletTransaction.objects.filter(
            wallet=wallet
        ).select_related('wallet').order_by('-created_at')[offset:offset+limit]
        
        return transactions