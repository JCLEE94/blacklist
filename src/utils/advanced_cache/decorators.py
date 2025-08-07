#!/usr/bin/env python3
"""
Cache Decorators for Advanced Cache
"""

import functools
import hashlib
import inspect
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Global cache instance (set by application)
_cache_instance = None
_lock = threading.Lock()


def set_cache_instance(cache_instance):
    """Set the global cache instance for decorators"""
    global _cache_instance
    with _lock:
        _cache_instance = cache_instance


def get_cache_instance():
    """Get the global cache instance"""
    global _cache_instance
    with _lock:
        return _cache_instance


def cache_decorator(
    ttl: int = 300,
    key_prefix: str = None,
    tags: List[str] = None,
    include_args: bool = True,
    include_kwargs: bool = True,
    exclude_args: List[str] = None,
):
    """Cache decorator for functions with intelligent key generation"""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache_instance()
            if not cache:
                logger.warning("No cache instance available, executing function directly")
                return func(*args, **kwargs)
            
            # Generate cache key
            cache_key = _generate_cache_key(
                func, args, kwargs, key_prefix, include_args, include_kwargs, exclude_args
            )
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            try:
                result = func(*args, **kwargs)
                cache.set(cache_key, result, ttl=ttl, tags=tags)
                return result
                
            except Exception as e:
                logger.error(f"Error in cached function {func.__name__}: {e}")
                raise
        
        # Add cache management methods to the decorated function
        wrapper._cache_key_generator = lambda *args, **kwargs: _generate_cache_key(
            func, args, kwargs, key_prefix, include_args, include_kwargs, exclude_args
        )
        wrapper._cache_invalidate = lambda *args, **kwargs: _invalidate_cache_key(
            func, args, kwargs, key_prefix, include_args, include_kwargs, exclude_args
        )
        wrapper._original_func = func
        
        return wrapper
    
    return decorator


def cache_lock(lock_key: str, timeout: int = 30, retry_interval: float = 0.1):
    """Distributed lock decorator using cache backend"""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache_instance()
            if not cache:
                logger.warning("No cache instance available for locking, executing function directly")
                return func(*args, **kwargs)
            
            # Generate lock key
            full_lock_key = f"lock:{lock_key}:{func.__name__}"
            
            # Try to acquire lock
            acquired = False
            start_time = time.time()
            
            while not acquired and (time.time() - start_time) < timeout:
                # Try to set lock (will fail if key already exists)
                acquired = cache.set(full_lock_key, "locked", ttl=timeout)
                
                if not acquired:
                    time.sleep(retry_interval)
            
            if not acquired:
                raise TimeoutError(f"Could not acquire lock '{full_lock_key}' within {timeout} seconds")
            
            try:
                # Execute function with lock held
                return func(*args, **kwargs)
            finally:
                # Always release lock
                cache.delete(full_lock_key)
        
        return wrapper
    
    return decorator


def _generate_cache_key(
    func: Callable,
    args: tuple,
    kwargs: dict,
    key_prefix: str = None,
    include_args: bool = True,
    include_kwargs: bool = True,
    exclude_args: List[str] = None,
) -> str:
    """Generate a cache key for a function call"""
    key_parts = []
    
    # Add prefix
    if key_prefix:
        key_parts.append(key_prefix)
    
    # Add function name and module
    key_parts.append(f"{func.__module__}.{func.__name__}")
    
    # Add arguments
    if include_args and args:
        args_str = ":".join(str(arg) for arg in args)
        key_parts.append(f"args:{args_str}")
    
    # Add keyword arguments (excluding specified ones)
    if include_kwargs and kwargs:
        exclude_set = set(exclude_args or [])
        filtered_kwargs = {
            k: v for k, v in kwargs.items() 
            if k not in exclude_set
        }
        if filtered_kwargs:
            kwargs_str = ":".join(f"{k}={v}" for k, v in sorted(filtered_kwargs.items()))
            key_parts.append(f"kwargs:{kwargs_str}")
    
    # Create final key
    cache_key = ":".join(key_parts)
    
    # Hash if key is too long (Redis has a 512MB key limit, but shorter is better)
    if len(cache_key) > 200:
        cache_key_hash = hashlib.md5(cache_key.encode()).hexdigest()
        short_prefix = key_parts[0] if key_parts else "func"
        cache_key = f"{short_prefix}:hash:{cache_key_hash}"
    
    return cache_key


def _invalidate_cache_key(
    func: Callable,
    args: tuple,
    kwargs: dict,
    key_prefix: str = None,
    include_args: bool = True,
    include_kwargs: bool = True,
    exclude_args: List[str] = None,
) -> bool:
    """Invalidate cache key for a specific function call"""
    cache = get_cache_instance()
    if not cache:
        return False
    
    cache_key = _generate_cache_key(
        func, args, kwargs, key_prefix, include_args, include_kwargs, exclude_args
    )
    
    return cache.delete(cache_key)


# Convenience decorators with common configurations
def cache_short(ttl: int = 60, key_prefix: str = None):
    """Short-term cache (1 minute)"""
    return cache_decorator(ttl=ttl, key_prefix=key_prefix)


def cache_medium(ttl: int = 300, key_prefix: str = None):
    """Medium-term cache (5 minutes)"""
    return cache_decorator(ttl=ttl, key_prefix=key_prefix)


def cache_long(ttl: int = 3600, key_prefix: str = None):
    """Long-term cache (1 hour)"""
    return cache_decorator(ttl=ttl, key_prefix=key_prefix)


def cache_result_only(ttl: int = 300, key_prefix: str = None):
    """Cache only based on function name (ignore arguments)"""
    return cache_decorator(
        ttl=ttl, 
        key_prefix=key_prefix, 
        include_args=False, 
        include_kwargs=False
    )


# Cache management utilities
class CacheManager:
    """Utility class for cache management operations"""
    
    @staticmethod
    def invalidate_function_cache(func: Callable, *args, **kwargs) -> bool:
        """Invalidate cache for a specific function call"""
        if hasattr(func, '_cache_invalidate'):
            return func._cache_invalidate(*args, **kwargs)
        return False
    
    @staticmethod
    def invalidate_all_function_cache(func: Callable) -> int:
        """Invalidate all cached results for a function"""
        cache = get_cache_instance()
        if not cache:
            return 0
        
        # Create pattern to match all cache keys for this function
        pattern = f"*{func.__module__}.{func.__name__}*"
        return cache.delete_pattern(pattern)
    
    @staticmethod
    def warm_function_cache(func: Callable, calls: List[tuple]) -> int:
        """Warm cache for a function with multiple parameter combinations"""
        success_count = 0
        
        for call_args in calls:
            try:
                if isinstance(call_args, tuple):
                    args, kwargs = call_args if len(call_args) == 2 else (call_args, {})
                else:
                    args, kwargs = (call_args,), {}
                
                # Call function to populate cache
                func(*args, **kwargs)
                success_count += 1
                
            except Exception as e:
                logger.error(f"Error warming cache for {func.__name__}: {e}")
        
        return success_count
    
    @staticmethod
    def get_function_cache_stats(func: Callable) -> Dict[str, Any]:
        """Get cache statistics for a specific function"""
        cache = get_cache_instance()
        if not cache or not hasattr(func, '_cache_key_generator'):
            return {"error": "Function not cached or cache unavailable"}
        
        # This would require enhanced backend support to track per-function stats
        return {
            "function": f"{func.__module__}.{func.__name__}",
            "cached": True,
            "note": "Detailed per-function stats require backend enhancement"
        }
