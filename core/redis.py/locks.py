import uuid
import time
from .client import redis_client


class DistributedLock:
    """
    Distributed lock using Redis
    """
    def __init__(self, key, ttl=5):
        self.key = f"lock:{key}"
        self.ttl = ttl
        self.identifier = str(uuid.uuid4())
    
    def acquire(self, blocking=True, timeout=10):
        """
        Acquire the lock
        """
        connection = redis_client.get_connection()
        end_time = time.time() + timeout
        
        while True:
            # Try to acquire lock
            if connection.set(self.key, self.identifier, nx=True, ex=self.ttl):
                return True
            
            # If not blocking or timeout reached
            if not blocking or time.time() > end_time:
                return False
            
            # Wait before retrying
            time.sleep(0.01)
    
    def release(self):
        """
        Release the lock atomically
        """
        connection = redis_client.get_connection()
        
        # Lua script for atomic check-and-delete
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        return connection.eval(lua_script, 1, self.key, self.identifier)
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()