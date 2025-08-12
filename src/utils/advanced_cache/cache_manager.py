#!/usr/bin/env python3
"""
Main Cache Manager - Enhanced Smart Cache Implementation
"""

import logging
import threading
import time
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from .memory_backend import MemoryBackend

# Performance tracking disabled
from .redis_backend import RedisBackend
from .serialization import SerializationManager

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
        self.default_ttl = default_ttl
        self.lock = threading.RLock()

        # Initialize serialization manager
        self.serialization = SerializationManager(
            enable_compression=enable_compression,
            compression_threshold=compression_threshold,
        )

        # Performance tracking disabled
        self.performance = None

        # Initialize backends
        self.redis_backend = RedisBackend(redis_url, redis_client)
        self.memory_backend = MemoryBackend(max_memory_entries)

        # Use Redis if available, otherwise fall back to memory
        self.primary_backend = (
            self.redis_backend
            if self.redis_backend.is_available
            else self.memory_backend
        )

        logger.info(
            f"EnhancedSmartCache initialized with {self.primary_backend.__class__.__name__} backend"
        )

    def get(self, key: str) -> Any:
        """Get value from cache"""
        start_time = time.time()

        try:
            # Get raw data from backend
            raw_data = self.primary_backend.get(key)

            if raw_data is None:
                # Performance tracking disabled
                if self.performance:
                    if self.performance:
                        self.performance.record_cache_result(hit=False)
                    if self.performance:
                        self.performance.record_operation(
                            "get", time.time() - start_time, success=True
                        )
                return None

            # Deserialize the data
            value = self.serialization.deserialize(raw_data)

            if self.performance:
                self.performance.record_cache_result(hit=True)
            if self.performance:
                self.performance.record_operation(
                    "get", time.time() - start_time, success=True
                )

            return value

        except Exception as e:
            logger.error(f"Cache GET error for key '{key}': {e}")
            if self.performance:
                self.performance.record_operation(
                    "get", time.time() - start_time, success=False
                )
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """Set value in cache with optional TTL and tags"""
        start_time = time.time()

        try:
            # Use default TTL if not specified
            if ttl is None:
                ttl = self.default_ttl

            # Serialize the value
            serialized_data = self.serialization.serialize(value)

            # Store in primary backend
            success = self.primary_backend.set(key, serialized_data, ttl)

            # Handle tags if provided (Redis only feature)
            if (
                success
                and tags
                and hasattr(self.primary_backend, "is_available")
                and self.primary_backend.is_available
            ):
                self._handle_tags(key, tags)

            if self.performance:
                self.performance.record_operation(
                    "set", time.time() - start_time, success=success
                )
            return success

        except Exception as e:
            logger.error(f"Cache SET error for key '{key}': {e}")
            if self.performance:
                self.performance.record_operation(
                    "set", time.time() - start_time, success=False
                )
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        start_time = time.time()

        try:
            success = self.primary_backend.delete(key)
            if self.performance:
                self.performance.record_operation(
                    "delete", time.time() - start_time, success=success
                )
            return success

        except Exception as e:
            logger.error(f"Cache DELETE error for key '{key}': {e}")
            if self.performance:
                self.performance.record_operation(
                    "delete", time.time() - start_time, success=False
                )
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern"""
        start_time = time.time()

        try:
            deleted_count = self.primary_backend.delete_pattern(pattern)
            if self.performance:
                self.performance.record_operation(
                    "delete_pattern", time.time() - start_time, success=True
                )
            return deleted_count

        except Exception as e:
            logger.error(f"Cache DELETE PATTERN error for pattern '{pattern}': {e}")
            if self.performance:
                self.performance.record_operation(
                    "delete_pattern", time.time() - start_time, success=False
                )
            return 0

    def clear(self) -> bool:
        """Clear all cache entries"""
        start_time = time.time()

        try:
            success = self.primary_backend.clear_all()
            if self.performance:
                self.performance.record_operation(
                    "clear", time.time() - start_time, success=success
                )
            return success

        except Exception as e:
            logger.error(f"Cache CLEAR error: {e}")
            if self.performance:
                self.performance.record_operation(
                    "clear", time.time() - start_time, success=False
                )
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        start_time = time.time()

        try:
            exists = self.primary_backend.exists(key)
            if self.performance:
                self.performance.record_operation(
                    "exists", time.time() - start_time, success=True
                )
            return exists

        except Exception as e:
            logger.error(f"Cache EXISTS error for key '{key}': {e}")
            if self.performance:
                self.performance.record_operation(
                    "exists", time.time() - start_time, success=False
                )
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        backend_stats = self.primary_backend.get_stats()
        performance_stats = (
            self.performance.get_performance_summary() if self.performance else {}
        )
        serialization_stats = self.serialization.get_stats()

        return {
            "cache_stats": {
                **backend_stats,
                "default_ttl": self.default_ttl,
                "backend_type": backend_stats.get("backend", "unknown"),
            },
            "performance_stats": performance_stats,
            "serialization_stats": serialization_stats,
            "timestamp": time.time(),
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        return {
            "performance_summary": self.performance.get_performance_summary()
            if self.performance
            else {},
            "trend_analysis": self.performance.get_trend_analysis()
            if self.performance
            else {},
            "backend_health": self.primary_backend.health_check(),
        }

    def warm_cache(self, data: Dict[str, Any], ttl: Optional[int] = None):
        """Warm cache with multiple key-value pairs"""
        start_time = time.time()
        success_count = 0

        for key, value in data.items():
            if self.set(key, value, ttl):
                success_count += 1

        if self.performance:
            self.performance.record_operation(
                "warm_cache", time.time() - start_time, success=success_count > 0
            )

        logger.info(f"Cache warmed with {success_count}/{len(data)} entries")

    def _handle_tags(self, key: str, tags: List[str]):
        """Handle tag-based invalidation (Redis only)"""
        if (
            hasattr(self.redis_backend, "is_available")
            and self.redis_backend.is_available
        ):
            try:
                # Store tag associations for future invalidation
                for tag in tags:
                    tag_key = f"tag:{tag}"
                    # Add key to tag set
                    self.redis_backend.redis.sadd(tag_key, key)
            except Exception as e:
                logger.warning(f"Tag handling error for key '{key}': {e}")

    def invalidate_tags(self, tags: List[str]) -> int:
        """Invalidate all cache entries with given tags"""
        if not (
            hasattr(self.redis_backend, "is_available")
            and self.redis_backend.is_available
        ):
            logger.warning("Tag invalidation only supported with Redis backend")
            return 0

        try:
            total_deleted = 0
            for tag in tags:
                tag_key = f"tag:{tag}"
                # Get all keys with this tag
                tagged_keys = self.redis_backend.redis.smembers(tag_key)

                if tagged_keys:
                    # Delete all keys with this tag
                    deleted = self.redis_backend.redis.delete(*tagged_keys)
                    total_deleted += deleted

                    # Clean up the tag set
                    self.redis_backend.redis.delete(tag_key)

            return total_deleted

        except Exception as e:
            logger.error(f"Tag invalidation error: {e}")
            return 0

    def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        backend_health = self.primary_backend.health_check()
        performance_summary = (
            self.performance.get_performance_summary() if self.performance else {}
        )

        # Determine overall health
        is_healthy = (
            backend_health.get("status") == "healthy"
            and performance_summary.get("error_rate_percent", 0) < 5
        )

        return {
            "status": "healthy" if is_healthy else "degraded",
            "backend": backend_health,
            "performance": {
                "hit_rate_percent": performance_summary.get("hit_rate_percent", 0),
                "average_response_time_ms": performance_summary.get(
                    "average_operation_time_ms", 0
                ),
                "error_rate_percent": performance_summary.get("error_rate_percent", 0),
                "operations_per_second": performance_summary.get(
                    "recent_ops_per_second", 0
                ),
            },
            "uptime_seconds": performance_summary.get("uptime_seconds", 0),
        }

    def cleanup_expired(self) -> int:
        """Clean up expired entries (memory backend only)"""
        if isinstance(self.primary_backend, MemoryBackend):
            return self.primary_backend.cleanup_expired()
        return 0

    def reset_stats(self):
        """Reset all statistics"""
        if self.performance:
            self.performance.reset_metrics()
        self.serialization.reset_stats()
        logger.info("Cache statistics reset")
