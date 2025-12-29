from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    if response is not None:
        return response
    
    # Handle uncaught exceptions
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Return generic error response in production
    return Response(
        {
            'error': 'An unexpected error occurred',
            'detail': str(exc) if context['request'].user.is_staff else None
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


class CasinoException(Exception):
    """Base exception for casino application"""
    default_detail = 'An error occurred'
    default_code = 'error'
    
    def __init__(self, detail=None, code=None):
        self.detail = detail or self.default_detail
        self.code = code or self.default_code
        super().__init__(self.detail)


class InsufficientFundsException(CasinoException):
    default_detail = 'Insufficient funds'
    default_code = 'insufficient_funds'


class InvalidBetException(CasinoException):
    default_detail = 'Invalid bet'
    default_code = 'invalid_bet'


class FraudDetectedException(CasinoException):
    default_detail = 'Fraud detected'
    default_code = 'fraud_detected'
