"""Performance optimization module for production deployment."""

import os
import gc
import logging
from functools import lru_cache, wraps
from datetime import datetime, timedelta
from typing import Any, Callable
import redis
import json
import hashlib
import time

logger = logging.getLogger(__name__)


class CacheOptimizer:
    """Advanced caching system with multiple strategies."""

    def __init__(self, redis_host="localhost", redis_port=32544):
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                decode_responses=True,
                connection_pool=redis.ConnectionPool(
                    host=redis_host, port=redis_port, max_connections=50
                ),
            )
            self.redis_available = self.redis_client.ping()
        except:
            self.redis_available = False
            logger.warning("Redis not available, using memory cache")

        self.memory_cache = {}
        self.cache_stats = {"hits": 0, "misses": 0, "evictions": 0}

    def cache_with_strategy(
        self, ttl: int = 300, strategy: str = "lazy", key_prefix: str = ""
    ) -> Callable:
        """
        Decorator for caching with different strategies.

        Strategies:
        - lazy: Cache on first access
        - eager: Pre-cache if possible
        - adaptive: Adjust TTL based on access patterns
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                # Generate cache key
                cache_key = self._generate_cache_key(
                    func.__name__, args, kwargs, key_prefix
                )

                # Try to get from cache
                cached_result = self._get_from_cache(cache_key)
                if cached_result is not None:
                    self.cache_stats["hits"] += 1
                    if strategy == "adaptive":
                        # Extend TTL for frequently accessed items
                        self._extend_ttl(cache_key, ttl)
                    return cached_result

                self.cache_stats["misses"] += 1

                # Execute function
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                # Determine TTL based on strategy
                effective_ttl = ttl
                if strategy == "adaptive":
                    # Longer TTL for slower operations
                    if execution_time > 1.0:
                        effective_ttl = ttl * 2
                    elif execution_time < 0.1:
                        effective_ttl = ttl // 2

                # Cache the result
                self._set_to_cache(cache_key, result, effective_ttl)

                return result

            # Eager loading for eager strategy
            if strategy == "eager":
                self._eager_load(func, key_prefix)

            return wrapper

        return decorator

    def _generate_cache_key(
        self, func_name: str, args: tuple, kwargs: dict, prefix: str
    ) -> str:
        """Generate unique cache key."""
        key_data = {"func": func_name, "args": args, "kwargs": kwargs}
        key_hash = hashlib.md5(
            json.dumps(key_data, sort_keys=True).encode()
        ).hexdigest()
        return f"{prefix}:{func_name}:{key_hash}"

    def _get_from_cache(self, key: str) -> Any:
        """Get value from cache (Redis or memory)."""
        if self.redis_available:
            try:
                cached = self.redis_client.get(key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.error(f"Redis get error: {e}")

        # Fallback to memory cache
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            if entry["expires"] > datetime.now():
                return entry["value"]
            else:
                del self.memory_cache[key]
                self.cache_stats["evictions"] += 1

        return None

    def _set_to_cache(self, key: str, value: Any, ttl: int):
        """Set value to cache (Redis or memory)."""
        if self.redis_available:
            try:
                self.redis_client.setex(key, ttl, json.dumps(value))
                return
            except Exception as e:
                logger.error(f"Redis set error: {e}")

        # Fallback to memory cache
        self.memory_cache[key] = {
            "value": value,
            "expires": datetime.now() + timedelta(seconds=ttl),
        }

        # Limit memory cache size
        if len(self.memory_cache) > 1000:
            self._evict_old_entries()

    def _extend_ttl(self, key: str, ttl: int):
        """Extend TTL for adaptive caching."""
        if self.redis_available:
            try:
                self.redis_client.expire(key, ttl)
            except:
                pass

    def _evict_old_entries(self):
        """Evict oldest entries from memory cache."""
        now = datetime.now()
        expired_keys = [k for k, v in self.memory_cache.items() if v["expires"] < now]
        for key in expired_keys:
            del self.memory_cache[key]
            self.cache_stats["evictions"] += 1

    def _eager_load(self, func: Callable, prefix: str):
        """Pre-load cache for eager strategy."""
        # This would pre-load common queries
        pass

    def clear_cache(self, pattern: str = "*"):
        """Clear cache by pattern."""
        if self.redis_available:
            try:
                for key in self.redis_client.scan_iter(match=pattern):
                    self.redis_client.delete(key)
            except:
                pass

        # Clear memory cache
        if pattern == "*":
            self.memory_cache.clear()
        else:
            keys_to_delete = [k for k in self.memory_cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self.memory_cache[key]

    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (self.cache_stats["hits"] / total * 100) if total > 0 else 0

        return {
            "hits": self.cache_stats["hits"],
            "misses": self.cache_stats["misses"],
            "evictions": self.cache_stats["evictions"],
            "hit_rate": round(hit_rate, 2),
            "memory_cache_size": len(self.memory_cache),
            "redis_available": self.redis_available,
        }


class QueryOptimizer:
    """Database query optimization."""

    @staticmethod
    def optimize_query(query: str) -> str:
        """Optimize SQL query."""
        optimized = query

        # Add LIMIT if not present for SELECT
        if "SELECT" in query.upper() and "LIMIT" not in query.upper():
            optimized += " LIMIT 1000"

        # Use indexes
        optimized = optimized.replace("WHERE ip_address =", "WHERE ip_address::inet =")

        return optimized

    @staticmethod
    def batch_query(queries: list) -> str:
        """Batch multiple queries."""
        return ";\n".join(queries)

    @staticmethod
    def create_indexes(conn):
        """Create database indexes for performance."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_blacklist_ip ON blacklist_entries(ip_address)",
            "CREATE INDEX IF NOT EXISTS idx_blacklist_created ON blacklist_entries(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_blacklist_source ON blacklist_entries(source)",
            "CREATE INDEX IF NOT EXISTS idx_blacklist_threat ON blacklist_entries(threat_level)",
        ]

        cursor = conn.cursor()
        for index in indexes:
            try:
                cursor.execute(index)
            except Exception as e:
                logger.warning(f"Index creation failed: {e}")
        conn.commit()
        cursor.close()


class MemoryOptimizer:
    """Memory optimization utilities."""

    @staticmethod
    def optimize_memory():
        """Run memory optimization."""
        # Force garbage collection
        gc.collect()

        # Clear unnecessary caches
        for cache in gc.get_objects():
            if isinstance(cache, dict) and len(cache) > 10000:
                cache.clear()

        # Run full collection
        gc.collect(2)

    @staticmethod
    def monitor_memory_usage():
        """Monitor memory usage."""
        import psutil

        process = psutil.Process()

        return {
            "rss_mb": process.memory_info().rss / 1024 / 1024,
            "vms_mb": process.memory_info().vms / 1024 / 1024,
            "percent": process.memory_percent(),
            "available_mb": psutil.virtual_memory().available / 1024 / 1024,
        }

    @staticmethod
    @lru_cache(maxsize=128)
    def cached_computation(key: str) -> Any:
        """LRU cached computation."""
        # This would cache expensive computations
        return f"computed_{key}"


class ConnectionPoolManager:
    """Connection pool management."""

    def __init__(self):
        self.pools = {}

    def get_redis_pool(self, max_connections=50):
        """Get Redis connection pool."""
        if "redis" not in self.pools:
            self.pools["redis"] = redis.ConnectionPool(
                host="localhost",
                port=32544,
                max_connections=max_connections,
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 1,  # TCP_KEEPINTVL
                    3: 5,  # TCP_KEEPCNT
                },
            )
        return self.pools["redis"]

    def get_db_pool(self):
        """Get database connection pool."""
        from psycopg2 import pool

        if "postgres" not in self.pools:
            self.pools["postgres"] = pool.SimpleConnectionPool(
                1,
                20,
                host="localhost",
                port=32543,
                database="blacklist",
                user="postgres",
                password="postgres",
            )
        return self.pools["postgres"]


class PerformanceMonitor:
    """Monitor and optimize performance."""

    def __init__(self):
        self.metrics = []

    def measure_performance(self, name: str = "operation"):
        """Decorator to measure function performance."""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                start_time = time.time()

                try:
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time

                    self.metrics.append(
                        {
                            "name": name,
                            "function": func.__name__,
                            "execution_time": execution_time,
                            "timestamp": datetime.now().isoformat(),
                            "success": True,
                        }
                    )

                    # Log slow operations
                    if execution_time > 1.0:
                        logger.warning(
                            f"Slow operation: {name} took {execution_time:.2f}s"
                        )

                    return result

                except Exception as e:
                    execution_time = time.time() - start_time
                    self.metrics.append(
                        {
                            "name": name,
                            "function": func.__name__,
                            "execution_time": execution_time,
                            "timestamp": datetime.now().isoformat(),
                            "success": False,
                            "error": str(e),
                        }
                    )
                    raise

            return wrapper

        return decorator

    def get_performance_stats(self) -> dict:
        """Get performance statistics."""
        if not self.metrics:
            return {}

        recent = self.metrics[-100:]
        successful = [m for m in recent if m.get("success", False)]

        if not successful:
            return {"error": "No successful operations"}

        avg_time = sum(m["execution_time"] for m in successful) / len(successful)
        max_time = max(m["execution_time"] for m in successful)
        min_time = min(m["execution_time"] for m in successful)

        return {
            "average_time": round(avg_time, 3),
            "max_time": round(max_time, 3),
            "min_time": round(min_time, 3),
            "total_operations": len(recent),
            "success_rate": len(successful) / len(recent) * 100,
            "slow_operations": [m for m in recent if m["execution_time"] > 1.0][:10],
        }


# Global instances
cache_optimizer = CacheOptimizer()
query_optimizer = QueryOptimizer()
memory_optimizer = MemoryOptimizer()
pool_manager = ConnectionPoolManager()
performance_monitor = PerformanceMonitor()
