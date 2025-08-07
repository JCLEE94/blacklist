#!/usr/bin/env python3
"""
Cache Factory Functions
Provides factory methods for creating cache instances with backward compatibility
"""

import hashlib
import logging
import os
from functools import wraps

from .cache_manager import EnhancedSmartCache

logger = logging.getLogger(__name__)


def get_smart_cache(
    redis_url: str = None,
    redis_client=None,
    default_ttl=300,
    max_memory_entries=10000,
    enable_compression=True,
):
    """Factory function to create EnhancedSmartCache instance"""
    return EnhancedSmartCache(
        redis_url=redis_url,
        redis_client=redis_client,
        default_ttl=default_ttl,
        max_memory_entries=max_memory_entries,
        enable_compression=enable_compression,
    )


def get_cache(redis_url: str = None):
    """Factory function for backward compatibility with cache.py"""
    redis_url = redis_url or os.getenv("REDIS_URL")
    return get_smart_cache(redis_url=redis_url)


def cached(cache, ttl=300, key_prefix=""):
    """Simple caching decorator for backward compatibility"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            args_str = str(args) if args else ""
            kwargs_str = str(sorted(kwargs.items())) if kwargs else ""
            cache_key = f"{key_prefix}:{func.__name__}:{hash(args_str + kwargs_str)}"

            # Try to get from cache
            if cache:
                try:
                    cached_result = cache.get(cache_key)
                    if cached_result is not None:
                        return cached_result
                except Exception as e:
                    logger.warning(f"Cache get failed: {e}")

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            if cache and result is not None:
                try:
                    cache.set(cache_key, result, ttl=ttl)
                except Exception as e:
                    logger.warning(f"Cache set failed: {e}")

            return result

        return wrapper

    return decorator
