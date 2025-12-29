"""
Custom middleware to handle API routes properly and prevent unwanted redirects
"""
from django.http import JsonResponse, Http404
from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve, Resolver404
from django.middleware.common import CommonMiddleware
from django.conf import settings
from core.utils.responses import ErrorResponse
from rest_framework import status


class APICommonMiddleware(CommonMiddleware):
    """
    Custom CommonMiddleware that completely disables APPEND_SLASH redirect for API routes
    """
    def process_response(self, request, response):
        # For API routes, convert redirects to 404 JSON responses
        if request.path.startswith('/api/'):
            if response.status_code in [301, 302]:
                # CommonMiddleware tried to redirect - convert to JSON 404
                location = response.get('Location', '')
                original_path = request.path
                
                # Check if the location path actually exists
                try:
                    resolve(location)
                    # Path exists with trailing slash
                    return JsonResponse({
                        'success': False,
                        'message': f'The API endpoint "{original_path}" requires a trailing slash. Please use "{location}" instead.',
                        'errors': {
                            'path': original_path,
                            'correct_path': location,
                            'method': request.method,
                            'suggestion': f'Use: {location}'
                        }
                    }, status=status.HTTP_404_NOT_FOUND)
                except Resolver404:
                    # Path doesn't exist even with trailing slash
                    return JsonResponse({
                        'success': False,
                        'message': f'The API endpoint "{original_path}" was not found. Please check the URL and ensure you are using the correct HTTP method (GET, POST, PUT, PATCH, DELETE). Visit /swagger/ for API documentation.',
                        'errors': {
                            'path': original_path,
                            'method': request.method,
                            'suggestion': 'Check API documentation at /swagger/ or /redoc/'
                        }
                    }, status=status.HTTP_404_NOT_FOUND)
            return response
        # For non-API routes, use the default CommonMiddleware behavior
        return super().process_response(request, response)


class APIMiddleware(MiddlewareMixin):
    """
    Middleware to handle API routes and ensure JSON responses
    """
    
    def process_response(self, request, response):
        """
        Intercept redirects and HTML responses for API routes and return JSON instead
        """
        # Only process API routes
        if not request.path.startswith('/api/'):
            return response
        
        # If we still got a redirect (shouldn't happen with APICommonMiddleware, but just in case)
        if response.status_code in [301, 302]:
            location = response.get('Location', '')
            original_path = request.path
            
            # Try to resolve the path with trailing slash to see if it exists
            path_with_slash = original_path if original_path.endswith('/') else original_path + '/'
            path_without_slash = original_path.rstrip('/')
            
            # Try both paths
            path_exists = False
            correct_path = None
            try:
                resolve(path_with_slash)
                path_exists = True
                correct_path = path_with_slash
            except Resolver404:
                try:
                    resolve(path_without_slash)
                    path_exists = True
                    correct_path = path_without_slash
                except Resolver404:
                    pass
            
            if path_exists and correct_path:
                return JsonResponse({
                    'success': False,
                    'message': f'The API endpoint "{original_path}" was not found. Did you mean "{correct_path}"? Please check the URL and ensure you are using the correct HTTP method (GET, POST, PUT, PATCH, DELETE). Visit /swagger/ for API documentation.',
                    'errors': {
                        'path': original_path,
                        'suggested_path': correct_path,
                        'method': request.method,
                        'suggestion': f'Try: {correct_path}',
                        'documentation': '/swagger/ or /redoc/'
                    }
                }, status=status.HTTP_404_NOT_FOUND)
            else:
                # Path doesn't exist at all
                return JsonResponse({
                    'success': False,
                    'message': f'The API endpoint "{original_path}" was not found. Please check the URL and ensure you are using the correct HTTP method (GET, POST, PUT, PATCH, DELETE). Visit /swagger/ for API documentation.',
                    'errors': {
                        'path': original_path,
                        'method': request.method,
                        'suggestion': 'Check API documentation at /swagger/ or /redoc/'
                    }
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Ensure all API responses are JSON (not HTML)
        content_type = response.get('Content-Type', '')
        if content_type.startswith('text/html') and response.status_code >= 400:
            # If we got HTML error for an API route, return JSON error
            return JsonResponse({
                'success': False,
                'message': f'An error occurred while processing the API request to "{request.path}".',
                'errors': {
                    'path': request.path,
                    'method': request.method,
                    'original_status': response.status_code
                }
            }, status=response.status_code if response.status_code >= 400 else status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return response
