from django.core.cache import cache
from functools import wraps
from rest_framework.response import Response
import hashlib
import json


def cache_response(timeout=300):
    """
    Cache decorator for API responses
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Generate cache key
            cache_key_parts = [
                view_func.__module__,
                view_func.__name__,
                request.method,
                request.path,
                json.dumps(request.GET.dict(), sort_keys=True),
                request.user.id if request.user.is_authenticated else 'anon'
            ]
            cache_key = hashlib.md5('|'.join(str(p) for p in cache_key_parts).encode()).hexdigest()
            
            # Try to get from cache
            cached_response = cache.get(cache_key)
            if cached_response:
                return Response(cached_response)
            
            # Call view function
            response = view_func(request, *args, **kwargs)
            
            # Cache the response
            if response.status_code == 200:
                cache.set(cache_key, response.data, timeout)
            
            return response
        return _wrapped_view
    return decorator


def require_role(roles):
    """
    Decorator to require specific user role
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return Response({'error': 'Authentication required'}, status=401)
            
            if request.user.role not in roles:
                return Response({'error': 'Insufficient permissions'}, status=403)
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator