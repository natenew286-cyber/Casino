from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ParseError
from core.utils.responses import ErrorResponse
import logging

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF - ensures all errors return JSON in consistent format
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    if response is not None:
        # Handle JSON parse errors specifically
        if isinstance(exc, ParseError):
            return ErrorResponse(
                message='Invalid JSON format provided. Please check your request body.',
                status=response.status_code,
                errors={'detail': response.data.get('detail', str(exc))}
            )

        # Handle validation errors (from serializers)
        if isinstance(response.data, dict):
            # Check if it's a validation error with field-specific errors
            if any(isinstance(v, (list, dict)) for v in response.data.values() if v):
                # This is likely a ValidationError with field errors
                errors = {}
                message = 'Validation error'
                
                # Extract field errors
                for key, value in response.data.items():
                    if isinstance(value, list):
                        errors[key] = value
                        if value:
                            message = f"Validation error: {value[0]}"
                    elif isinstance(value, dict):
                        errors[key] = value
                    elif key == 'detail':
                        message = str(value) if value else 'An error occurred'
                    elif key == 'non_field_errors':
                        errors['non_field_errors'] = value
                        if value:
                            message = f"Validation error: {value[0] if isinstance(value, list) else value}"
                
                return ErrorResponse(
                    message=message,
                    status=response.status_code,
                    errors=errors if errors else {}
                )
            else:
                # Simple error with detail
                error_detail = response.data.get('detail', 'An error occurred')
                errors = response.data.copy()
                if 'detail' in errors:
                    del errors['detail']
                
                return ErrorResponse(
                    message=str(error_detail) if error_detail else 'An error occurred',
                    status=response.status_code,
                    errors=errors if errors else {}
                )
        else:
            # Non-dict response data
            return ErrorResponse(
                message=str(response.data) if response.data else 'An error occurred',
                status=response.status_code,
                errors={}
            )
    
    # Handle uncaught exceptions
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Return generic error response in standard format
    request = context.get('request')
    is_staff = request.user.is_staff if request and hasattr(request, 'user') and request.user.is_authenticated else False
    
    return ErrorResponse(
        message='An unexpected error occurred',
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        errors={'detail': str(exc)} if is_staff else {}
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
