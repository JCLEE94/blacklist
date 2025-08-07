"""Modular Advanced Cache Management System package"""

from .cache_manager import EnhancedSmartCache
from .redis_backend import RedisBackend
from .memory_backend import MemoryBackend
from .serialization import SerializationManager
from .performance_tracker import PerformanceTracker
from .decorators import cache_decorator, cache_lock
from .factory import get_cache, get_smart_cache, cached

__all__ = [
    'EnhancedSmartCache',
    'RedisBackend',
    'MemoryBackend',
    'SerializationManager',
    'PerformanceTracker',
    'cache_decorator',
    'cache_lock',
    'get_cache',
    'get_smart_cache',
    'cached',
]
