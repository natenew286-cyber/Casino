import valkey
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize Valkey (Redis-compatible) connection pool"""
        try:
            self.pool = valkey.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=50,
                decode_responses=True
            )
            self.connection = valkey.Redis(connection_pool=self.pool)
            logger.info("Valkey connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Valkey: {e}")
            raise
    
    def get_connection(self):
        """Get Redis connection from pool"""
        return self.connection
    
    def close(self):
        """Close all connections in pool"""
        self.pool.disconnect()


# Global Redis client instance
redis_client = RedisClient()