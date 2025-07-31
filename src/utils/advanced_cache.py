"""
Enhanced Advanced Cache Management System
Provides intelligent caching with TTL, compression, tagging, and Redis optimization
Features: Smart compression, tag-based invalidation, connection pooling, async support
"""

import asyncio
import gzip
import hashlib
import json
import logging
import pickle
import threading
import time
import weakref
from collections import defaultdict, deque
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Union

try:
    import redis
    from redis.connection import ConnectionPool

    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

try:
    import orjson

    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False

logger = logging.getLogger(__name__)


class EnhancedSmartCache:
    """Enhanced smart cache with advanced features and optimizations"""

    def __init__(
        self,
        redis_url: str = None,
        redis_client=None,
        default_ttl=300,
        max_memory_entries=10000,
        enable_compression=True,
        compression_threshold=1024,
    ):
        # Redis configuration with connection pooling
        if redis_client:
            self.redis_client = redis_client
        elif redis_url and HAS_REDIS:
            try:
                # Enhanced connection pool for Redis
                pool = ConnectionPool.from_url(
                    redis_url,
                    max_connections=20,
                    socket_keepalive=True,
                    socket_keepalive_options={},
                    health_check_interval=30,
                    retry_on_timeout=True,
                )
                self.redis_client = redis.Redis(connection_pool=pool)
                # Test connection
                self.redis_client.ping()
                logger.info("Redis connection established with optimized pool")
            except Exception as e:
                logger.warning(
                    f"Redis connection failed: {e}, falling back to memory cache"
                )
                self.redis_client = None
        else:
            self.redis_client = None

        # Configuration
        self.default_ttl = default_ttl
        self.max_memory_entries = max_memory_entries
        self.enable_compression = enable_compression
        self.compression_threshold = compression_threshold

        # Memory cache with LRU eviction
        self.memory_cache = {}
        self.access_order = deque()

        # Tag-based cache invalidation
        self.tag_cache = defaultdict(set)
        self.key_tags = defaultdict(set)

        # Enhanced statistics
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "compressions": 0,
            "decompressions": 0,
            "redis_errors": 0,
            "memory_evictions": 0,
            "tag_invalidations": 0,
        }

        # Performance monitoring
        self.operation_times = deque(maxlen=1000)
        self.redis_latency = deque(maxlen=100)

        # Thread safety
        self._lock = threading.RLock()

        # Weak references for cleanup
        self._cleanup_callbacks = []

    def get(self, key: str) -> Any:
        """Enhanced get with performance monitoring and LRU update"""
        start_time = time.time()

        try:
            with self._lock:
                # Try Redis first with latency monitoring
                if self.redis_client:
                    try:
                        redis_start = time.time()
                        value = self.redis_client.get(key)
                        redis_latency = time.time() - redis_start
                        self.redis_latency.append(redis_latency)

                        if value:
                            self.cache_stats["hits"] += 1
                            self._record_operation_time(start_time)
                            result = self._deserialize(value)
                            # Update memory cache for faster subsequent access
                            self._update_memory_cache(key, result, self.default_ttl)
                            return result
                    except Exception as e:
                        self.cache_stats["redis_errors"] += 1
                        logger.warning(f"Redis get failed for {key}: {e}")

                # Fallback to memory cache with LRU update
                if key in self.memory_cache:
                    entry = self.memory_cache[key]
                    if entry["expires"] > time.time():
                        self.cache_stats["hits"] += 1
                        self._update_access_order(key)
                        self._record_operation_time(start_time)
                        return entry["value"]
                    else:
                        self._remove_from_memory(key)

                self.cache_stats["misses"] += 1
                self._record_operation_time(start_time)
                return None

        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
            self.cache_stats["misses"] += 1
            self._record_operation_time(start_time)
            return None

    def set(
        self, key: str, value: Any, ttl: Optional[int] = None, tags: List[str] = None
    ) -> bool:
        """Enhanced set with tag support and LRU management"""
        start_time = time.time()

        try:
            with self._lock:
                ttl = ttl or self.default_ttl

                # Try Redis first with compression
                if self.redis_client:
                    try:
                        redis_start = time.time()
                        serialized = self._serialize(value)
                        self.redis_client.setex(key, ttl, serialized)

                        # Track Redis latency
                        redis_latency = time.time() - redis_start
                        self.redis_latency.append(redis_latency)

                        # Handle tags in Redis
                        if tags:
                            for tag in tags:
                                self.redis_client.sadd(f"tag:{tag}", key)
                                self.redis_client.expire(
                                    f"tag:{tag}", ttl + 60
                                )  # Tag TTL slightly longer

                        self.cache_stats["sets"] += 1
                        self._record_operation_time(start_time)

                        # Also update memory cache for faster subsequent access
                        self._update_memory_cache(key, value, ttl, tags)

                        return True
                    except Exception as e:
                        self.cache_stats["redis_errors"] += 1
                        logger.warning(f"Redis set failed for {key}: {e}")

                # Fallback to memory cache with LRU management
                self._update_memory_cache(key, value, ttl, tags)
                self.cache_stats["sets"] += 1
                self._record_operation_time(start_time)

                return True

        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
            self._record_operation_time(start_time)
            return False

    def delete(self, key: str) -> bool:
        """Enhanced delete with tag cleanup"""
        start_time = time.time()

        try:
            with self._lock:
                deleted = False

                # Try Redis first
                if self.redis_client:
                    try:
                        result = self.redis_client.delete(key)
                        deleted = result > 0

                        # Clean up tag associations in Redis
                        if deleted:
                            pipe = self.redis_client.pipeline()
                            # Remove key from all tag sets (this is expensive, consider optimization)
                            tag_keys = self.redis_client.keys("tag:*")
                            for tag_key in tag_keys:
                                pipe.srem(tag_key, key)
                            pipe.execute()

                    except Exception as e:
                        self.cache_stats["redis_errors"] += 1
                        logger.warning(f"Redis delete failed for {key}: {e}")

                # Delete from memory cache
                if key in self.memory_cache:
                    self._remove_from_memory(key)
                    deleted = True

                if deleted:
                    self.cache_stats["deletes"] += 1
                    self._record_operation_time(start_time)

                return deleted

        except Exception as e:
            logger.error(f"Cache delete error for {key}: {e}")
            self._record_operation_time(start_time)
            return False

    def clear(self) -> bool:
        """Enhanced clear with comprehensive cleanup"""
        start_time = time.time()

        try:
            with self._lock:
                # Clear Redis
                if self.redis_client:
                    try:
                        self.redis_client.flushdb()
                    except Exception as e:
                        self.cache_stats["redis_errors"] += 1
                        logger.warning(f"Redis clear failed: {e}")

                # Clear memory cache and related structures
                self.memory_cache.clear()
                self.access_order.clear()
                self.tag_cache.clear()
                self.key_tags.clear()

                # Reset stats but preserve error counts for monitoring
                error_counts = {
                    "redis_errors": self.cache_stats.get("redis_errors", 0),
                    "memory_evictions": self.cache_stats.get("memory_evictions", 0),
                    "tag_invalidations": self.cache_stats.get("tag_invalidations", 0),
                }

                self.cache_stats = {
                    "hits": 0,
                    "misses": 0,
                    "sets": 0,
                    "deletes": 0,
                    "compressions": 0,
                    "decompressions": 0,
                    **error_counts,
                }

                # Clear performance monitoring data
                self.operation_times.clear()
                self.redis_latency.clear()

                self._record_operation_time(start_time)
                return True

        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            self._record_operation_time(start_time)
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Enhanced cache statistics with performance metrics"""
        with self._lock:
            total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
            hit_rate = (
                (self.cache_stats["hits"] / total_requests * 100)
                if total_requests > 0
                else 0
            )

            # Calculate average operation times
            avg_operation_time = 0
            if self.operation_times:
                avg_operation_time = sum(self.operation_times) / len(
                    self.operation_times
                )

            # Calculate Redis performance metrics
            redis_metrics = {}
            if self.redis_latency:
                redis_metrics = {
                    "avg_latency": sum(self.redis_latency) / len(self.redis_latency),
                    "max_latency": max(self.redis_latency),
                    "min_latency": min(self.redis_latency),
                    "p95_latency": (
                        sorted(self.redis_latency)[int(len(self.redis_latency) * 0.95)]
                        if len(self.redis_latency) > 20
                        else max(self.redis_latency)
                        if self.redis_latency
                        else 0
                    ),
                }

            return {
                # Basic stats
                **self.cache_stats,
                "hit_rate": round(hit_rate, 2),
                "memory_entries": len(self.memory_cache),
                "redis_available": self.redis_client is not None,
                # Performance metrics
                "avg_operation_time": round(
                    avg_operation_time * 1000, 2
                ),  # Convert to ms
                "redis_metrics": redis_metrics,
                # LRU and tagging stats
                "access_order_length": len(self.access_order),
                "tag_count": len(self.tag_cache),
                "tagged_keys_count": len(self.key_tags),
                # Configuration
                "max_memory_entries": self.max_memory_entries,
                "default_ttl": self.default_ttl,
                "compression_enabled": self.enable_compression,
                "compression_threshold": self.compression_threshold,
            }

    def _serialize(self, value: Any) -> bytes:
        """Enhanced serialization with compression and statistics tracking"""
        try:
            # Try optimized JSON first for simple types
            if isinstance(value, (dict, list, str, int, float, bool, type(None))):
                if HAS_ORJSON:
                    json_data = orjson.dumps(value)
                else:
                    json_data = json.dumps(
                        value, ensure_ascii=False, separators=(",", ":")
                    ).encode("utf-8")

                # Compress if enabled and data is large enough
                if (
                    self.enable_compression
                    and len(json_data) > self.compression_threshold
                ):
                    self.cache_stats["compressions"] += 1
                    return b"gzip:" + gzip.compress(json_data)
                else:
                    return b"json:" + json_data
            else:
                # Use pickle for complex objects
                pickle_data = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)

                # Compress if enabled and data is large enough
                if (
                    self.enable_compression
                    and len(pickle_data) > self.compression_threshold
                ):
                    self.cache_stats["compressions"] += 1
                    return b"gzip_pickle:" + gzip.compress(pickle_data)
                else:
                    return b"pickle:" + pickle_data

        except Exception as e:
            logger.error(f"Serialization error: {e}")
            # Fallback to basic pickle
            return b"pickle:" + pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)

    def _deserialize(self, data: bytes) -> Any:
        """Enhanced deserialization with decompression and statistics tracking"""
        try:
            if data.startswith(b"gzip:"):
                self.cache_stats["decompressions"] += 1
                decompressed = gzip.decompress(data[5:])
                if HAS_ORJSON:
                    return orjson.loads(decompressed)
                else:
                    return json.loads(decompressed.decode("utf-8"))
            elif data.startswith(b"json:"):
                if HAS_ORJSON:
                    return orjson.loads(data[5:])
                else:
                    return json.loads(data[5:].decode("utf-8"))
            elif data.startswith(b"gzip_pickle:"):
                self.cache_stats["decompressions"] += 1
                decompressed = gzip.decompress(data[12:])
                return pickle.loads(decompressed)
            elif data.startswith(b"pickle:"):
                return pickle.loads(data[7:])
            else:
                # Legacy fallback
                try:
                    if HAS_ORJSON:
                        return orjson.loads(data)
                    else:
                        return json.loads(data.decode("utf-8"))
                except:
                    return pickle.loads(data)

        except Exception as e:
            logger.error(f"Deserialization error: {e}")
            raise

    # Helper methods for enhanced functionality

    def _update_memory_cache(
        self, key: str, value: Any, ttl: int, tags: List[str] = None
    ):
        """Update memory cache with LRU management and tag support"""
        expires = time.time() + ttl

        # Add to memory cache
        self.memory_cache[key] = {
            "value": value,
            "expires": expires,
            "tags": tags or [],
        }

        # Update access order for LRU
        self._update_access_order(key)

        # Update tag associations
        if tags:
            for tag in tags:
                self.tag_cache[tag].add(key)
                self.key_tags[key].add(tag)

        # Check if we need to evict entries
        self._enforce_memory_limit()

    def _update_access_order(self, key: str):
        """Update access order for LRU eviction"""
        # Remove key from current position if it exists
        try:
            self.access_order.remove(key)
        except ValueError:
            pass  # Key not in order yet

        # Add to the end (most recently used)
        self.access_order.append(key)

    def _remove_from_memory(self, key: str):
        """Remove key from memory cache and all related structures"""
        if key in self.memory_cache:
            # Get tags before deletion
            entry = self.memory_cache[key]
            tags = entry.get("tags", [])

            # Remove from memory cache
            del self.memory_cache[key]

            # Remove from access order
            try:
                self.access_order.remove(key)
            except ValueError:
                pass

            # Remove tag associations
            for tag in tags:
                self.tag_cache[tag].discard(key)
                if not self.tag_cache[tag]:  # Remove empty tag sets
                    del self.tag_cache[tag]

            if key in self.key_tags:
                del self.key_tags[key]

    def _enforce_memory_limit(self):
        """Enforce memory cache size limit using LRU eviction"""
        while len(self.memory_cache) > self.max_memory_entries:
            if not self.access_order:
                break

            # Remove least recently used item
            lru_key = self.access_order.popleft()
            if lru_key in self.memory_cache:
                self._remove_from_memory(lru_key)
                self.cache_stats["memory_evictions"] += 1

    def _record_operation_time(self, start_time: float):
        """Record operation time for performance monitoring"""
        duration = time.time() - start_time
        self.operation_times.append(duration)

    # Advanced cache operations

    def tag_set(
        self, key: str, value: Any, tags: List[str], ttl: Optional[int] = None
    ) -> bool:
        """Set value with tags for efficient invalidation"""
        return self.set(key, value, ttl=ttl, tags=tags)

    def invalidate_tags(self, tags: List[str]) -> int:
        """Invalidate all keys associated with given tags"""
        invalidated_count = 0

        try:
            with self._lock:
                keys_to_delete = set()

                # Collect keys from memory cache
                for tag in tags:
                    if tag in self.tag_cache:
                        keys_to_delete.update(self.tag_cache[tag])

                # Delete from Redis if available
                if self.redis_client:
                    try:
                        for tag in tags:
                            redis_keys = self.redis_client.smembers(f"tag:{tag}")
                            if redis_keys:
                                # Convert bytes to strings if needed
                                redis_keys = [
                                    k.decode() if isinstance(k, bytes) else k
                                    for k in redis_keys
                                ]
                                keys_to_delete.update(redis_keys)

                                # Delete keys and tag set
                                pipe = self.redis_client.pipeline()
                                pipe.delete(*redis_keys)
                                pipe.delete(f"tag:{tag}")
                                pipe.execute()
                    except Exception as e:
                        self.cache_stats["redis_errors"] += 1
                        logger.warning(f"Redis tag invalidation failed: {e}")

                # Delete from memory cache
                for key in keys_to_delete:
                    self._remove_from_memory(key)
                    invalidated_count += 1

                self.cache_stats["tag_invalidations"] += len(tags)

        except Exception as e:
            logger.error(f"Tag invalidation error: {e}")

        return invalidated_count

    def get_by_pattern(self, pattern: str) -> Dict[str, Any]:
        """Get all keys matching a pattern (memory cache only for now)"""
        import fnmatch

        results = {}

        with self._lock:
            for key, entry in self.memory_cache.items():
                if fnmatch.fnmatch(key, pattern):
                    if entry["expires"] > time.time():
                        results[key] = entry["value"]
                        self._update_access_order(key)
                    else:
                        # Schedule for removal
                        self._remove_from_memory(key)

        return results

    def warm_cache(self, data: Dict[str, Any], ttl: Optional[int] = None):
        """Warm cache with multiple key-value pairs"""
        ttl = ttl or self.default_ttl

        for key, value in data.items():
            self.set(key, value, ttl=ttl)

    async def async_get(self, key: str) -> Any:
        """Async version of get operation"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get, key)

    async def async_set(
        self, key: str, value: Any, ttl: Optional[int] = None, tags: List[str] = None
    ) -> bool:
        """Async version of set operation"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.set, key, value, ttl, tags)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        with self._lock:
            metrics = {
                "operation_count": len(self.operation_times),
                "avg_operation_time_ms": 0,
                "p95_operation_time_ms": 0,
                "p99_operation_time_ms": 0,
                "redis_connection_health": False,
                "memory_efficiency": 0,
                "compression_ratio": 0,
            }

            if self.operation_times:
                sorted_times = sorted(self.operation_times)
                metrics.update(
                    {
                        "avg_operation_time_ms": (sum(sorted_times) / len(sorted_times))
                        * 1000,
                        "p95_operation_time_ms": sorted_times[
                            int(len(sorted_times) * 0.95)
                        ]
                        * 1000,
                        "p99_operation_time_ms": sorted_times[
                            int(len(sorted_times) * 0.99)
                        ]
                        * 1000,
                    }
                )

            # Test Redis connection
            if self.redis_client:
                try:
                    self.redis_client.ping()
                    metrics["redis_connection_health"] = True
                except:
                    metrics["redis_connection_health"] = False

            # Calculate memory efficiency
            if self.max_memory_entries > 0:
                metrics["memory_efficiency"] = (
                    len(self.memory_cache) / self.max_memory_entries
                )

            # Calculate compression effectiveness
            total_compressions = self.cache_stats.get("compressions", 0)
            total_sets = self.cache_stats.get("sets", 0)
            if total_sets > 0:
                metrics["compression_ratio"] = total_compressions / total_sets

            return metrics


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


def cached_method(ttl: int = 300, key_prefix: str = ""):
    """Decorator for caching method results"""

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"

            # Try to get from cache
            if hasattr(self, "cache"):
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    return cached_result

            # Execute function and cache result
            result = func(self, *args, **kwargs)

            if hasattr(self, "cache") and self.cache is not None and result is not None:
                try:
                    self.cache.set(cache_key, result, ttl=ttl)
                except Exception as e:
                    logger.warning(f"Cache set failed: {e}")

            return result

        return wrapper

    return decorator


def invalidate_cache_pattern(cache, pattern: str):
    """Invalidate cache entries matching a pattern"""
    try:
        if hasattr(cache, "redis_client") and cache.redis_client:
            # Redis pattern matching
            keys = cache.redis_client.keys(pattern)
            if keys:
                cache.redis_client.delete(*keys)

        # Memory cache pattern matching
        keys_to_delete = [key for key in cache.memory_cache.keys() if pattern in key]
        for key in keys_to_delete:
            del cache.memory_cache[key]

        logger.info(f"Invalidated cache pattern: {pattern}")
        return True

    except Exception as e:
        logger.error(f"Cache pattern invalidation error: {e}")
        return False


def smart_cached(ttl: int = 300, key_prefix: str = "", tags: list = None):
    """Smart caching decorator with enhanced tag support"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"

            # Try to get cache from instance if this is a method
            cache = None
            if args and hasattr(args[0], "cache_service"):
                cache = args[0].cache_service
            elif args and hasattr(args[0], "cache"):
                cache = args[0].cache

            # Try to get from cache (handle None cache gracefully)
            if cache is not None:
                try:
                    cached_result = cache.get(cache_key)
                    if cached_result is not None:
                        return cached_result
                except Exception as e:
                    logger.warning(f"Cache get failed: {e}")
            else:
                logger.debug("Cache not available - executing function without cache")

            # Execute function and cache result
            result = func(*args, **kwargs)

            # Only cache if cache is available and result is not None
            if cache is not None and result is not None:
                try:
                    # Use enhanced set method with tag support
                    if hasattr(cache, "tag_set") and tags:
                        cache.tag_set(cache_key, result, tags, ttl=ttl)
                    else:
                        cache.set(cache_key, result, ttl=ttl)
                except Exception as e:
                    logger.warning(f"Cache set failed: {e}")
            elif cache is None:
                logger.debug("Cache not available - function executed without caching")

            return result

        return wrapper

    return decorator


def enhanced_cached(
    ttl: int = 300,
    key_prefix: str = "",
    tags: List[str] = None,
    compression: bool = True,
):
    """Enhanced caching decorator with full feature support"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Try to get cache from instance if this is a method
            cache = None
            if args and hasattr(args[0], "cache"):
                cache = args[0].cache
            elif hasattr(func, "__globals__") and "cache" in func.__globals__:
                cache = func.__globals__["cache"]
            else:
                # Fallback to global cache
                cache = get_smart_cache()

            # Generate cache key with better collision resistance
            func_sig = f"{func.__module__}.{func.__qualname__}"
            args_hash = hashlib.md5(
                str(args[1:] if args and hasattr(args[0], "cache") else args).encode()
            ).hexdigest()
            kwargs_hash = hashlib.md5(str(sorted(kwargs.items())).encode()).hexdigest()
            cache_key = f"{key_prefix}:{func_sig}:{args_hash}:{kwargs_hash}"

            # Try to get from cache (handle None cache gracefully)
            if cache is not None:
                try:
                    cached_result = cache.get(cache_key)
                    if cached_result is not None:
                        return cached_result
                except Exception as e:
                    logger.warning(f"Cache get failed: {e}")
            else:
                logger.warning("Cache is None - executing function without cache")

            # Execute function
            result = func(*args, **kwargs)

            # Cache result with enhanced features
            if result is not None and cache is not None:
                try:
                    if hasattr(cache, "tag_set"):
                        # Dynamic tag generation based on function and args
                        dynamic_tags = tags or []
                        dynamic_tags.append(f"func:{func.__name__}")

                        # Add argument-based tags if applicable
                        if args and hasattr(args[0], "__class__"):
                            dynamic_tags.append(f"class:{args[0].__class__.__name__}")

                        cache.tag_set(cache_key, result, dynamic_tags, ttl=ttl)
                    else:
                        cache.set(cache_key, result, ttl=ttl)
                except Exception as e:
                    logger.warning(f"Cache set failed: {e}")

            return result

        return wrapper

    return decorator


# Global enhanced cache instance
_global_enhanced_cache = None


def get_global_cache() -> EnhancedSmartCache:
    """Get global enhanced cache instance"""
    global _global_enhanced_cache
    if _global_enhanced_cache is None:
        _global_enhanced_cache = get_smart_cache()
    return _global_enhanced_cache


def cache_warm_up(data: Dict[str, Any], ttl: int = 300, tags: List[str] = None):
    """Warm up cache with initial data"""
    cache = get_global_cache()

    for key, value in data.items():
        if cache is not None:
            try:
                if tags:
                    cache.tag_set(key, value, tags, ttl=ttl)
                else:
                    cache.set(key, value, ttl=ttl)
            except Exception as e:
                logger.warning(f"Cache warm up failed for key {key}: {e}")

    logger.info(f"Cache warmed up with {len(data)} entries")
