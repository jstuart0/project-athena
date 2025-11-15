"""Redis caching for Project Athena"""

import os
import json
import redis.asyncio as redis
from typing import Optional, Any
from functools import wraps


class CacheClient:
    """Redis cache client with async support"""
    
    def __init__(self, url: Optional[str] = None):
        self.url = url or os.getenv("REDIS_URL", "redis://192.168.10.181:6379/0")
        self.client = redis.from_url(self.url, decode_responses=True)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        value = await self.client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache with optional TTL (seconds)"""
        serialized = json.dumps(value) if not isinstance(value, str) else value
        if ttl:
            await self.client.setex(key, ttl, serialized)
        else:
            await self.client.set(key, serialized)
    
    async def delete(self, key: str):
        """Delete key from cache"""
        await self.client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        return await self.client.exists(key) > 0
    
    async def connect(self):
        """Connect to Redis (no-op for compatibility with RAG services)"""
        # Connection is established in __init__, this is for compatibility
        pass

    async def disconnect(self):
        """Disconnect from Redis (alias for close)"""
        await self.close()

    async def close(self):
        """Close Redis connection"""
        await self.client.aclose()


# Global cache client singleton
_global_cache_client: Optional[CacheClient] = None


def get_cache_client() -> CacheClient:
    """Get or create global cache client singleton."""
    global _global_cache_client
    if _global_cache_client is None:
        _global_cache_client = CacheClient()
    return _global_cache_client


def cached(ttl: int = 3600, key_prefix: str = "athena"):
    """Decorator to cache async function results
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache keys
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and args
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"

            # OPTIMIZATION: Reuse global cache client
            cache = get_cache_client()

            try:
                # Try to get from cache
                cached_result = await cache.get(cache_key)

                if cached_result is not None:
                    return cached_result
            except Exception:
                # Cache read error, continue to function call
                pass

            # Call function and cache result
            result = await func(*args, **kwargs)

            try:
                await cache.set(cache_key, result, ttl)
            except Exception:
                # Cache write error, return result anyway
                pass

            return result
        return wrapper
    return decorator
