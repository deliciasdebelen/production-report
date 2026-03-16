"""
cache_utils.py - Redis caching utilities for the application.
Provides a cache_response decorator that caches endpoint results in Redis.
If Redis is unavailable, the endpoint executes normally without caching.
"""
import json
import functools
import os
from typing import Optional, Callable, Any

try:
    import redis as redis_lib
    _redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    _redis_client = redis_lib.from_url(_redis_url, decode_responses=True, socket_connect_timeout=2)
    _redis_client.ping()
    _REDIS_AVAILABLE = True
except Exception:
    _redis_client = None
    _REDIS_AVAILABLE = False


def cache_response(ttl: int = 300, key_prefix: str = "cache"):
    """
    Decorator that caches the return value of an async or sync function in Redis.
    
    Args:
        ttl: Time-to-live in seconds (default: 300 = 5 minutes)
        key_prefix: Prefix for the Redis key (default: "cache")
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            if not _REDIS_AVAILABLE:
                return await func(*args, **kwargs)
            
            # Build cache key from prefix + function name + stringified kwargs
            cache_key = f"{key_prefix}:{func.__name__}:{json.dumps(kwargs, default=str, sort_keys=True)}"
            
            try:
                cached = _redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass
            
            result = await func(*args, **kwargs)
            
            try:
                _redis_client.setex(cache_key, ttl, json.dumps(result, default=str))
            except Exception:
                pass
            
            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            if not _REDIS_AVAILABLE:
                return func(*args, **kwargs)
            
            cache_key = f"{key_prefix}:{func.__name__}:{json.dumps(kwargs, default=str, sort_keys=True)}"
            
            try:
                cached = _redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass
            
            result = func(*args, **kwargs)
            
            try:
                _redis_client.setex(cache_key, ttl, json.dumps(result, default=str))
            except Exception:
                pass
            
            return result

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def invalidate_cache(key_prefix: str) -> None:
    """Delete all cache keys matching the given prefix."""
    if not _REDIS_AVAILABLE:
        return
    try:
        keys = _redis_client.keys(f"{key_prefix}:*")
        if keys:
            _redis_client.delete(*keys)
    except Exception:
        pass
