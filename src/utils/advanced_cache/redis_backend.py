#!/usr/bin/env python3
"""
Redis Backend for Advanced Cache
"""

import logging
import time
from typing import Any, Dict, List, Optional

try:
    import redis
    from redis.connection import ConnectionPool

    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

logger = logging.getLogger(__name__)


class RedisBackend:
    """Redis backend for cache operations"""

    def __init__(self, redis_url: str = None, redis_client=None, **redis_kwargs):
        self.redis = None
        self.connection_pool = None
        self.is_available = False

        if not HAS_REDIS:
            logger.warning("Redis library not available, using memory-only cache")
            return

        try:
            if redis_client:
                self.redis = redis_client
            elif redis_url:
                # Create connection pool for better performance
                self.connection_pool = ConnectionPool.from_url(
                    redis_url,
                    decode_responses=False,  # We handle bytes directly
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    **redis_kwargs,
                )
                self.redis = redis.Redis(connection_pool=self.connection_pool)
            else:
                # Default Redis connection
                self.redis = redis.Redis(
                    host="localhost",
                    port=6379,
                    db=0,
                    decode_responses=False,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    **redis_kwargs,
                )

            # Test connection
            self.redis.ping()
            self.is_available = True
            logger.info("Redis backend initialized successfully")

        except Exception as e:
            logger.warning(
                "Redis connection failed: {e}. Falling back to memory cache."
            )
            self.redis = None
            self.is_available = False

    def get(self, key: str) -> Optional[bytes]:
        """Get value from Redis"""
        if not self.is_available:
            return None

        try:
            return self.redis.get(key)
        except Exception as e:
            logger.error(f"Redis GET error for key '{key}': {e}")
            return None

    def set(self, key: str, value: bytes, ttl: Optional[int] = None) -> bool:
        """Set value in Redis with optional TTL"""
        if not self.is_available:
            return False

        try:
            if ttl is not None:
                return bool(self.redis.setex(key, ttl, value))
            else:
                return bool(self.redis.set(key, value))
        except Exception as e:
            logger.error(f"Redis SET error for key '{key}': {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if not self.is_available:
            return False

        try:
            return bool(self.redis.delete(key))
        except Exception as e:
            logger.error(f"Redis DELETE error for key '{key}': {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern"""
        if not self.is_available:
            return 0

        try:
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis DELETE PATTERN error for pattern '{pattern}': {e}")
            return 0

    def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        if not self.is_available:
            return False

        try:
            return bool(self.redis.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error for key '{key}': {e}")
            return False

    def clear_all(self) -> bool:
        """Clear all keys from Redis database"""
        if not self.is_available:
            return False

        try:
            self.redis.flushdb()
            return True
        except Exception as e:
            logger.error(f"Redis FLUSHDB error: {e}")
            return False

    def get_keys_by_pattern(self, pattern: str) -> List[str]:
        """Get all keys matching pattern"""
        if not self.is_available:
            return []

        try:
            keys = self.redis.keys(pattern)
            return [
                key.decode("utf-8") if isinstance(key, bytes) else key for key in keys
            ]
        except Exception as e:
            logger.error(f"Redis KEYS error for pattern '{pattern}': {e}")
            return []

    def set_expiry(self, key: str, ttl: int) -> bool:
        """Set expiry for existing key"""
        if not self.is_available:
            return False

        try:
            return bool(self.redis.expire(key, ttl))
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key '{key}': {e}")
            return False

    def get_ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL for key"""
        if not self.is_available:
            return None

        try:
            ttl = self.redis.ttl(key)
            return ttl if ttl >= 0 else None
        except Exception as e:
            logger.error(f"Redis TTL error for key '{key}': {e}")
            return None

    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter key"""
        if not self.is_available:
            return None

        try:
            return self.redis.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis INCRBY error for key '{key}': {e}")
            return None

    def get_info(self) -> Dict[str, Any]:
        """Get Redis server information"""
        if not self.is_available:
            return {"status": "unavailable", "error": "Redis not connected"}

        try:
            info = self.redis.info()
            return {
                "status": "connected",
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory"),
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "uptime_in_seconds": info.get("uptime_in_seconds"),
            }
        except Exception as e:
            logger.error(f"Redis INFO error: {e}")
            return {"status": "error", "error": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """Get Redis statistics"""
        info = self.get_info()

        if info["status"] != "connected":
            return info

        # Calculate hit rate
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total_requests = hits + misses
        hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "backend": "redis",
            "status": info["status"],
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total_requests,
            "memory_usage": info.get("used_memory_human", "unknown"),
            "connected_clients": info.get("connected_clients", 0),
            "uptime_seconds": info.get("uptime_in_seconds", 0),
            "redis_version": info.get("redis_version", "unknown"),
        }

    def health_check(self) -> Dict[str, Any]:
        """Perform Redis health check"""
        if not self.is_available:
            return {
                "status": "unhealthy",
                "available": False,
                "error": "Redis not available",
            }

        try:
            start_time = time.time()
            self.redis.ping()
            response_time = (time.time() - start_time) * 1000  # Convert to ms

            info = self.redis.info()

            return {
                "status": "healthy",
                "available": True,
                "response_time_ms": round(response_time, 2),
                "redis_version": info.get("redis_version"),
                "memory_usage_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
                "connected_clients": info.get("connected_clients"),
            }

        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {"status": "unhealthy", "available": False, "error": str(e)}

    def pipeline_operations(self, operations: List[Dict[str, Any]]) -> List[Any]:
        """Execute multiple operations in a Redis pipeline"""
        if not self.is_available or not operations:
            return []

        try:
            pipe = self.redis.pipeline()

            for op in operations:
                cmd = op.get("command")
                args = op.get("args", [])
                kwargs = op.get("kwargs", {})

                if hasattr(pipe, cmd):
                    getattr(pipe, cmd)(*args, **kwargs)
                else:
                    logger.warning(f"Unknown Redis command: {cmd}")

            return pipe.execute()

        except Exception as e:
            logger.error(f"Redis pipeline error: {e}")
            return []

    def __del__(self):
        """Cleanup Redis connection"""
        if self.connection_pool:
            try:
                self.connection_pool.disconnect()
            except Exception as e:
                pass  # Ignore cleanup errors
