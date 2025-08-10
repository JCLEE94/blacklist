"""
Cache Decorators - Unified caching functionality
"""

import hashlib
import logging
from functools import wraps
from typing import Callable, Optional

from flask import g, request

from .registry import get_registry

logger = logging.getLogger(__name__)


def unified_cache(
    ttl: int = 300,
    key_func: Optional[Callable] = None,
    key_prefix: str = "",
    cache_unless: Optional[Callable] = None,
    per_user: bool = False,
):
    """
    Unified caching decorator that works with multiple cache backends
    Consolidates all caching logic into a single, configurable decorator

    Args:
        ttl: Time to live in seconds
        key_func: Custom function to generate cache key
        key_prefix: Prefix for cache key
        cache_unless: Function that returns True to skip caching
        per_user: Whether to include user context in cache key
    """

    def cache_decorator(func):
        @wraps(func)
        def cache_wrapper(*args, **kwargs):
            # Skip caching if condition is met
            if cache_unless and cache_unless():
                return func(*args, **kwargs)

            registry = get_registry()

            # Generate cache key
            if key_func:
                cache_key = key_func()
            else:
                # Default key generation
                key_parts = [
                    func.__name__,
                    str(hash(str(args))),
                    str(hash(str(sorted(kwargs.items())))),
                ]

                # Add user context if requested
                if per_user and hasattr(g, "user_id"):
                    key_parts.append(f"user_{g.user_id}")

                # Add request context for routes
                try:
                    if hasattr(request, "endpoint") and request.endpoint:
                        key_parts.extend(
                            [request.endpoint, str(sorted(request.args.items()))]
                        )
                except RuntimeError:
                    # Outside of request context, which is fine for tests
                    pass

                prefix = f"unified:{key_prefix}:" if key_prefix else "unified:"
                cache_key = (
                    prefix + hashlib.md5(":".join(key_parts).encode()).hexdigest()
                )

            # Try to get from cache
            if registry.cache is not None:
                try:
                    cached_result = registry.cache.get(cache_key)
                    if cached_result is not None:
                        logger.debug(f"Cache hit for key: {cache_key}")
                        return cached_result
                except Exception as e:
                    logger.warning(f"Cache get error: {e}")

            # Execute function and cache result
            result = func(*args, **kwargs)

            if registry.cache is not None and hasattr(registry.cache, "set"):
                try:
                    registry.cache.set(cache_key, result, ttl=ttl)
                    logger.debug(f"Cached result for key: {cache_key}")
                except Exception as e:
                    logger.warning(f"Cache set error: {e}")
            else:
                logger.debug(
                    f"Cache not available, skipping cache set for key: {cache_key}"
                )

            return result

        return cache_wrapper

    return cache_decorator
