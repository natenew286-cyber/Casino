"""
Custom error handlers for API routes to ensure JSON responses
"""
from django.http import JsonResponse
from core.utils.responses import ErrorResponse
from rest_framework import status


def handler404(request, exception):
    """
    Custom 404 handler that returns JSON for API routes
    """
    if request.path.startswith('/api/'):
        return ErrorResponse(
            message=f'The API endpoint "{request.path}" was not found. Please check the URL and ensure you are using the correct HTTP method (GET, POST, PUT, PATCH, DELETE). Visit /swagger/ for API documentation.',
            status=status.HTTP_404_NOT_FOUND,
            errors={
                'path': request.path,
                'method': request.method,
                'suggestion': 'Check API documentation at /swagger/ or /redoc/'
            }
        )
    # For non-API routes, return default Django 404
    from django.http import HttpResponseNotFound
    return HttpResponseNotFound()


def handler500(request):
    """
    Custom 500 handler that returns JSON for API routes
    """
    if request.path.startswith('/api/'):
        return ErrorResponse(
            message='An internal server error occurred while processing your request. Our team has been notified and is working to resolve the issue. Please try again later or contact support if the problem persists.',
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            errors={
                'path': request.path,
                'method': request.method,
                'support': 'If this error persists, please contact support with the request details.'
            }
        )
    # For non-API routes, return default Django 500
    from django.http import HttpResponseServerError
    return HttpResponseServerError()
