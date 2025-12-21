from core.exceptions import CasinoException


class WalletException(CasinoException):
    """Base wallet exception"""
    pass


class TransactionNotFoundException(WalletException):
    default_detail = 'Transaction not found'
    default_code = 'transaction_not_found'


class DuplicateTransactionException(WalletException):
    default_detail = 'Duplicate transaction detected'
    default_code = 'duplicate_transaction'


class InvalidAmountException(WalletException):
    default_detail = 'Invalid amount'
    default_code = 'invalid_amount'


class WithdrawalLimitExceededException(WalletException):
    default_detail = 'Withdrawal limit exceeded'
    default_code = 'withdrawal_limit_exceeded'