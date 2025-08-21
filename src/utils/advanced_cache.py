#!/usr/bin/env python3
"""
Backward compatibility wrapper for modularized Advanced Cache

This file maintains backward compatibility while the actual implementation
has been modularized into the advanced_cache/ package.
"""

# Import everything from the modular package
from .advanced_cache import (
    EnhancedSmartCache,
    MemoryBackend,
    PerformanceTracker,
    RedisBackend,
    SerializationManager,
    cache_decorator,
    cache_lock,
)

# Import decorator utilities
from .advanced_cache.decorators import (
    CacheManager,
    cache_long,
    cache_medium,
    cache_result_only,
    cache_short,
    get_cache_instance,
    set_cache_instance,
)

# Re-export for backward compatibility
__all__ = [
    "EnhancedSmartCache",
    "RedisBackend",
    "MemoryBackend",
    "SerializationManager",
    "PerformanceTracker",
    "cache_decorator",
    "cache_lock",
    "cache_short",
    "cache_medium",
    "cache_long",
    "cache_result_only",
    "CacheManager",
    "set_cache_instance",
    "get_cache_instance",
]
