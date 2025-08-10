"""Modular Advanced Cache Management System package"""

from .cache_manager import EnhancedSmartCache
from .decorators import cache_decorator
from .decorators import cache_lock
from .factory import cached
from .factory import get_cache
from .factory import get_smart_cache
from .memory_backend import MemoryBackend
from .performance_tracker import PerformanceTracker
from .redis_backend import RedisBackend
from .serialization import SerializationManager

__all__ = [
    "EnhancedSmartCache",
    "RedisBackend",
    "MemoryBackend",
    "SerializationManager",
    "PerformanceTracker",
    "cache_decorator",
    "cache_lock",
    "get_cache",
    "get_smart_cache",
    "cached",
]
