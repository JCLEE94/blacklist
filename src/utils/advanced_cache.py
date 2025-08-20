#!/usr/bin/env python3
"""
Backward compatibility wrapper for modularized Advanced Cache

This file maintains backward compatibility while the actual implementation
has been modularized into the advanced_cache/ package.
"""

# Import everything from the modular package
from .advanced_cache import EnhancedSmartCache
from .advanced_cache import MemoryBackend
from .advanced_cache import PerformanceTracker
from .advanced_cache import RedisBackend
from .advanced_cache import SerializationManager
from .advanced_cache import cache_decorator
from .advanced_cache import cache_lock

# Import decorator utilities
from .advanced_cache.decorators import CacheManager
from .advanced_cache.decorators import cache_long
from .advanced_cache.decorators import cache_medium
from .advanced_cache.decorators import cache_result_only
from .advanced_cache.decorators import cache_short
from .advanced_cache.decorators import get_cache_instance
from .advanced_cache.decorators import set_cache_instance

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

# Preserve the original class name and functionality
# All imports and usage patterns remain the same
