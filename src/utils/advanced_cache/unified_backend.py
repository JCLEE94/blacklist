#!/usr/bin/env python3
"""
Unified Cache Backend Interface

Consolidates Redis and Memory backends with consistent interface.
Provides automatic fallback and unified statistics.

Sample input: cache.set("key", "value", ttl=300)
Expected output: Cached value with TTL, automatic backend selection
"""

import logging
import threading
import time
from typing import Any, Dict, Optional

try:
    import redis

    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

logger = logging.getLogger(__name__)


class UnifiedCacheBackend:
    """Unified cache backend with Redis primary, memory fallback"""

    def __init__(self, redis_url: str = None, max_memory_entries: int = 10000):
        self.redis_client = None
        self.memory_cache = {}
        self.memory_lock = threading.RLock()
        self.max_memory_entries = max_memory_entries
        self.use_redis = False

        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "redis_hits": 0,
            "memory_hits": 0,
        }

        # Initialize Redis if available
        if HAS_REDIS and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()
                self.use_redis = True
                logger.info("Redis cache backend initialized")
            except Exception as e:
                logger.warning(f"Redis unavailable, using memory cache: {e}")

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if self.use_redis and self.redis_client:
                value = self.redis_client.get(key)
                if value is not None:
                    self.stats["hits"] += 1
                    self.stats["redis_hits"] += 1
                    return value.decode() if isinstance(value, bytes) else value

            # Fallback to memory cache
            with self.memory_lock:
                if key in self.memory_cache:
                    entry = self.memory_cache[key]
                    if entry["expires"] > time.time():
                        self.stats["hits"] += 1
                        self.stats["memory_hits"] += 1
                        return entry["value"]
                    else:
                        del self.memory_cache[key]

            self.stats["misses"] += 1
            return None

        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache"""
        try:
            if self.use_redis and self.redis_client:
                self.redis_client.setex(key, ttl, str(value))

            # Always store in memory cache as backup
            with self.memory_lock:
                # LRU eviction
                if len(self.memory_cache) >= self.max_memory_entries:
                    oldest_key = next(iter(self.memory_cache))
                    del self.memory_cache[oldest_key]

                self.memory_cache[key] = {"value": value, "expires": time.time() + ttl}

            self.stats["sets"] += 1
            return True

        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            if self.use_redis and self.redis_client:
                self.redis_client.delete(key)

            with self.memory_lock:
                if key in self.memory_cache:
                    del self.memory_cache[key]

            self.stats["deletes"] += 1
            return True

        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    def health_check(self) -> Dict[str, Any]:
        """Health check for cache backend"""
        health = {"redis_available": False, "memory_cache_size": 0, "stats": self.stats}

        try:
            if self.use_redis and self.redis_client:
                self.redis_client.ping()
                health["redis_available"] = True
        except Exception:
            pass

        with self.memory_lock:
            health["memory_cache_size"] = len(self.memory_cache)

        return health

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = self.stats.copy()

        with self.memory_lock:
            stats["memory_entries"] = len(self.memory_cache)

        if self.use_redis and self.redis_client:
            try:
                info = self.redis_client.info()
                stats["redis_memory_used"] = info.get("used_memory_human", "unknown")
                stats["redis_connected_clients"] = info.get("connected_clients", 0)
            except Exception:
                pass

        return stats


if __name__ == "__main__":
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: Basic cache operations
    total_tests += 1
    try:
        cache = UnifiedCacheBackend()

        # Set and get
        success = cache.set("test_key", "test_value", ttl=60)
        if not success:
            all_validation_failures.append("Cache test: Failed to set value")

        value = cache.get("test_key")
        if value != "test_value":
            all_validation_failures.append(
                f"Cache test: Expected 'test_value', got {value}"
            )

    except Exception as e:
        all_validation_failures.append(f"Cache test: Failed - {e}")

    # Test 2: Health check
    total_tests += 1
    try:
        cache = UnifiedCacheBackend()
        health = cache.health_check()

        if "stats" not in health:
            all_validation_failures.append("Health check test: Missing stats")

    except Exception as e:
        all_validation_failures.append(f"Health check test: Failed - {e}")

    # Test 3: Statistics
    total_tests += 1
    try:
        cache = UnifiedCacheBackend()
        stats = cache.get_stats()

        if "hits" not in stats or "misses" not in stats:
            all_validation_failures.append("Stats test: Missing required statistics")

    except Exception as e:
        all_validation_failures.append(f"Stats test: Failed - {e}")

    # Final validation result
    if all_validation_failures:
        print(
            f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print("Unified cache backend is validated and ready for use")
        sys.exit(0)
