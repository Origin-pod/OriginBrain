"""
Cache decorator for easy API endpoint caching.
"""

import json
import hashlib
from functools import wraps
from typing import Any, Optional

def cache_result(prefix: str, ttl: int = 300, cache_obj=None):
    """
    Decorator to cache function results.

    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        cache_obj: CacheService instance (optional)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Try to get from cache first
            if cache_obj:
                # Create cache key from function name and arguments
                key_data = {
                    'func': func.__name__,
                    'args': args,
                    'kwargs': sorted(kwargs.items())
                }
                key_hash = hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
                cache_key = f"{prefix}:{key_hash}"

                # Try to get from cache
                cached_result = cache_obj.get('api_cache', cache_key)
                if cached_result is not None:
                    return cached_result

            # Execute function
            result = func(*args, **kwargs)

            # Cache the result
            if cache_obj and result is not None:
                cache_obj.set('api_cache', cache_key, result, ttl)

            return result
        return wrapper
    return decorator