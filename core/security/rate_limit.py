from django.core.cache import cache
from rest_framework.throttling import SimpleRateThrottle
import time


class RedisRateThrottle(SimpleRateThrottle):
    """
    Rate limiting using Redis for distributed environments
    """
    cache_format = 'throttle_%(scope)s_%(ident)s'
    
    def __init__(self):
        super().__init__()
    
    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident = request.user.id
        else:
            ident = self.get_ident(request)
        
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }
    
    def throttle_failure(self):
        """
        Called when a request is throttled
        """
        key = self.key
        history = cache.get(key, [])
        now = time.time()
        
        # Remove expired entries
        while history and history[-1] <= now - self.duration:
            history.pop()
        
        # Calculate wait time
        if history:
            wait = self.duration - (now - history[-1])
        else:
            wait = self.duration
        
        return wait


class UserRateThrottle(RedisRateThrottle):
    scope = 'user'
    
    def get_rate(self):
        return '100/minute'


class AnonRateThrottle(RedisRateThrottle):
    scope = 'anon'
    
    def get_rate(self):
        return '10/minute'