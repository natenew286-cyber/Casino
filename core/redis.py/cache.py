from django.core.cache import cache as django_cache
from .client import redis_client


class RedisCache:
    """
    Enhanced Redis cache operations
    """
    
    @staticmethod
    def set_with_ttl(key, value, ttl=3600):
        """Set value with TTL"""
        django_cache.set(key, value, ttl)
    
    @staticmethod
    def increment(key, amount=1, ttl=None):
        """Increment counter"""
        connection = redis_client.get_connection()
        result = connection.incrby(key, amount)
        if ttl:
            connection.expire(key, ttl)
        return result
    
    @staticmethod
    def get_or_set(key, default_func, ttl=3600):
        """Get or set value with function"""
        value = django_cache.get(key)
        if value is None:
            value = default_func()
            django_cache.set(key, value, ttl)
        return value
    
    @staticmethod
    def delete_pattern(pattern):
        """Delete keys matching pattern"""
        connection = redis_client.get_connection()
        keys = connection.keys(pattern)
        if keys:
            connection.delete(*keys)
    
    @staticmethod
    def add_to_sorted_set(key, member, score):
        """Add to sorted set (for leaderboards)"""
        connection = redis_client.get_connection()
        return connection.zadd(key, {member: score})
    
    @staticmethod
    def get_leaderboard(key, start=0, end=-1, desc=True):
        """Get leaderboard from sorted set"""
        connection = redis_client.get_connection()
        if desc:
            return connection.zrevrange(key, start, end, withscores=True)
        return connection.zrange(key, start, end, withscores=True)