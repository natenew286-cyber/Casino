from rest_framework import serializers
from decimal import Decimal
from .models import Wallet, WalletTransaction, Deposit, Withdrawal


class WalletSerializer(serializers.ModelSerializer):
    """Serializer for wallet information"""
    available_balance = serializers.SerializerMethodField()
    
    class Meta:
        model = Wallet
        fields = [
            'id', 'balance', 'locked_balance', 'available_balance',
            'currency', 'created_at', 'updated_at'
        ]
        read_only_fields = fields
    
    def get_available_balance(self, obj):
        """Calculate available balance (balance - locked_balance)"""
        return str(obj.available_balance())


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for wallet transactions"""
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    amount = serializers.DecimalField(max_digits=20, decimal_places=8, coerce_to_string=True)
    balance_before = serializers.DecimalField(max_digits=20, decimal_places=8, coerce_to_string=True)
    balance_after = serializers.DecimalField(max_digits=20, decimal_places=8, coerce_to_string=True)
    
    class Meta:
        model = WalletTransaction
        fields = [
            'id', 'type', 'type_display', 'amount', 'balance_before',
            'balance_after', 'reference_type', 'reference_id', 'metadata',
            'created_at'
        ]
        read_only_fields = fields


class DepositSerializer(serializers.ModelSerializer):
    """Serializer for deposit records"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    amount = serializers.DecimalField(max_digits=20, decimal_places=8, coerce_to_string=True)
    
    class Meta:
        model = Deposit
        fields = [
            'id', 'amount', 'currency', 'payment_method', 'payment_reference',
            'status', 'status_display', 'metadata', 'created_at', 'completed_at'
        ]
        read_only_fields = fields


class WithdrawalSerializer(serializers.ModelSerializer):
    """Serializer for withdrawal records"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    amount = serializers.DecimalField(max_digits=20, decimal_places=8, coerce_to_string=True)
    
    class Meta:
        model = Withdrawal
        fields = [
            'id', 'amount', 'currency', 'payment_method', 'payment_details',
            'status', 'status_display', 'admin_notes', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields


class DepositRequestSerializer(serializers.Serializer):
    """Serializer for deposit request creation"""
    amount = serializers.DecimalField(
        max_digits=20,
        decimal_places=8,
        min_value=Decimal('0.01'),
        required=True,
        help_text="Deposit amount (minimum 0.01)"
    )
    payment_method = serializers.CharField(
        max_length=50,
        required=True,
        help_text="Payment method (e.g., 'CREDIT_CARD', 'BANK_TRANSFER', 'CRYPTO')"
    )
    payment_reference = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="External payment reference ID"
    )
    metadata = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Additional metadata for the deposit"
    )
    
    def validate_amount(self, value):
        """Validate deposit amount"""
        if value <= 0:
            raise serializers.ValidationError("Deposit amount must be greater than zero")
        return value
    
    def validate_payment_method(self, value):
        """Validate payment method"""
        allowed_methods = ['CREDIT_CARD', 'DEBIT_CARD', 'BANK_TRANSFER', 'CRYPTO', 'EWALLET']
        if value.upper() not in allowed_methods:
            raise serializers.ValidationError(
                f"Payment method must be one of: {', '.join(allowed_methods)}"
            )
        return value.upper()


class WithdrawalRequestSerializer(serializers.Serializer):
    """Serializer for withdrawal request creation"""
    amount = serializers.DecimalField(
        max_digits=20,
        decimal_places=8,
        min_value=Decimal('0.01'),
        required=True,
        help_text="Withdrawal amount (minimum 0.01)"
    )
    payment_method = serializers.CharField(
        max_length=50,
        required=True,
        help_text="Payment method (e.g., 'BANK_TRANSFER', 'CRYPTO', 'EWALLET')"
    )
    payment_details = serializers.JSONField(
        required=True,
        help_text="Payment details (e.g., bank account, crypto address, etc.)"
    )
    metadata = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Additional metadata for the withdrawal"
    )
    
    def validate_amount(self, value):
        """Validate withdrawal amount"""
        if value <= 0:
            raise serializers.ValidationError("Withdrawal amount must be greater than zero")
        
        # Minimum withdrawal amount check
        min_withdrawal = Decimal('10.00')
        if value < min_withdrawal:
            raise serializers.ValidationError(
                f"Minimum withdrawal amount is {min_withdrawal}"
            )
        return value
    
    def validate_payment_method(self, value):
        """Validate payment method"""
        allowed_methods = ['BANK_TRANSFER', 'CRYPTO', 'EWALLET']
        if value.upper() not in allowed_methods:
            raise serializers.ValidationError(
                f"Payment method must be one of: {', '.join(allowed_methods)}"
            )
        return value.upper()
    
    def validate_payment_details(self, value):
        """Validate payment details structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Payment details must be a JSON object")
        
        payment_method = self.initial_data.get('payment_method', '').upper()
        
        if payment_method == 'BANK_TRANSFER':
            required_fields = ['account_number', 'routing_number', 'account_name']
            for field in required_fields:
                if field not in value:
                    raise serializers.ValidationError(
                        f"Bank transfer requires '{field}' in payment_details"
                    )
        
        elif payment_method == 'CRYPTO':
            required_fields = ['address', 'network']
            for field in required_fields:
                if field not in value:
                    raise serializers.ValidationError(
                        f"Crypto withdrawal requires '{field}' in payment_details"
                    )
        
        elif payment_method == 'EWALLET':
            required_fields = ['wallet_id', 'wallet_type']
            for field in required_fields:
                if field not in value:
                    raise serializers.ValidationError(
                        f"E-wallet withdrawal requires '{field}' in payment_details"
                    )
        
        return value
