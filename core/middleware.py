"""
Custom middleware to handle API routes properly and prevent unwanted redirects
"""
from django.http import JsonResponse, Http404
from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve, Resolver404
from core.utils.responses import ErrorResponse
from rest_framework import status


class APIMiddleware(MiddlewareMixin):
    """
    Middleware to handle API routes and prevent trailing slash redirects
    Returns JSON responses for API routes instead of HTML redirects
    """
    
    def process_response(self, request, response):
        """
        Intercept redirects and HTML responses for API routes and return JSON instead
        """
        # Only process API routes
        if not request.path.startswith('/api/'):
            return response
        
        # If CommonMiddleware redirected (301/302) for API routes, return JSON 404 instead
        if response.status_code in [301, 302]:
            # Check if it's a trailing slash redirect
            location = response.get('Location', '')
            original_path = request.path
            
            # Check if redirecting to add trailing slash
            if location.endswith('/') and not original_path.endswith('/'):
                # Try to resolve the path with trailing slash
                try:
                    resolve(location)
                    # Path exists with trailing slash - return helpful JSON message
                    return ErrorResponse(
                        message=f'The API endpoint "{original_path}" requires a trailing slash. Please use "{location}" instead. API endpoints should include trailing slashes (e.g., /api/auth/login/).',
                        status=status.HTTP_404_NOT_FOUND,
                        errors={
                            'path': original_path,
                            'correct_path': location,
                            'method': request.method,
                            'suggestion': f'Use the correct path: {location}',
                            'note': 'API endpoints require trailing slashes'
                        }
                    )
                except Resolver404:
                    # Path doesn't exist even with trailing slash
                    return ErrorResponse(
                        message=f'The API endpoint "{original_path}" was not found. Please check the URL and ensure you are using the correct HTTP method (GET, POST, PUT, PATCH, DELETE). Visit /swagger/ for API documentation.',
                        status=status.HTTP_404_NOT_FOUND,
                        errors={
                            'path': original_path,
                            'method': request.method,
                            'suggestion': 'Check API documentation at /swagger/ or /redoc/'
                        }
                    )
            else:
                # Some other redirect - return JSON 404
                return ErrorResponse(
                    message=f'The API endpoint "{original_path}" was not found. Please check the URL and ensure you are using the correct HTTP method (GET, POST, PUT, PATCH, DELETE). Visit /swagger/ for API documentation.',
                    status=status.HTTP_404_NOT_FOUND,
                    errors={
                        'path': original_path,
                        'method': request.method,
                        'suggestion': 'Check API documentation at /swagger/ or /redoc/'
                    }
                )
        
        # Ensure all API responses are JSON (not HTML)
        content_type = response.get('Content-Type', '')
        if content_type.startswith('text/html') and response.status_code >= 400:
            # If we got HTML error for an API route, return JSON error
            return ErrorResponse(
                message=f'An error occurred while processing the API request to "{request.path}".',
                status=response.status_code if response.status_code >= 400 else status.HTTP_500_INTERNAL_SERVER_ERROR,
                errors={
                    'path': request.path,
                    'method': request.method,
                    'original_status': response.status_code
                }
            )
        
        return response
