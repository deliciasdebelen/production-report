import functools
import hashlib
import json
import os
import redis
import asyncio
from fastapi.encoders import jsonable_encoder

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
try:
    redis_client = redis.Redis.from_url(redis_url, decode_responses=False)
except Exception as e:
    print(f"Redis initialization failed: {e}")
    redis_client = None

def cache_response(ttl=300):
    """
    Decorator to cache FastAPI endpoint JSON responses using Redis.
    ttl is in seconds (default 300s = 5mins).
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # If no Redis connection, bypass cache
            if not redis_client:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
                
            # Build cache key based on function name and safe kwargs
            safe_kwargs = {}
            for k, v in kwargs.items():
                if k not in ['db', 'user', 'current_user', 'external_db', 'request', 'background_tasks', 'db_a', 'db_m']:
                    safe_kwargs[k] = str(v)
            
            # Create MD5 hash for consistent key length
            key_str = f"{func.__module__}.{func.__name__}:{json.dumps(safe_kwargs, sort_keys=True)}"
            key_hash = hashlib.md5(key_str.encode()).hexdigest()
            cache_key = f"cache:{func.__name__}:{key_hash}"
            
            # 1. Try to fetch from Redis
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    return json.loads(cached.decode('utf-8'))
            except Exception as e:
                print(f"Redis GET error on {cache_key}: {e}")
                
            # 2. Execute original function if cache miss
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # 3. Store in Redis
            try:
                # jsonable_encoder converts complex types (e.g. datetime, Decimal, SQLAlchemy models)
                # to primitive dicts / lists before caching
                json_compatible_data = jsonable_encoder(result)
                redis_client.setex(cache_key, ttl, json.dumps(json_compatible_data))
            except Exception as e:
                print(f"Redis SET error on {cache_key}: {e}")
                
            return result
        return wrapper
    return decorator
