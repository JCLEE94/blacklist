#!/usr/bin/env python3
"""
Unit tests for performance optimizer core components

Tests PerformanceMetrics, QueryOptimizer, SmartCache, and MemoryOptimizer classes.
"""

import threading
import time
import unittest
from datetime import datetime
from datetime import timedelta
from unittest.mock import Mock
from unittest.mock import patch

import pytest

# Test imports
from src.utils.performance_optimizer import MemoryOptimizer
from src.utils.performance_optimizer import PerformanceMetrics
from src.utils.performance_optimizer import QueryOptimizer
from src.utils.performance_optimizer import SmartCache


class TestPerformanceMetrics:
    """Test PerformanceMetrics dataclass"""

    def test_default_initialization(self):
        """Test PerformanceMetrics initialization with defaults"""
        metrics = PerformanceMetrics()

        assert metrics.total_requests == 0
        assert metrics.avg_response_time == 0.0
        assert metrics.cache_hit_rate == 0.0
        assert metrics.memory_usage_mb == 0.0
        assert metrics.database_query_time == 0.0
        assert metrics.active_connections == 0
        assert metrics.error_rate == 0.0
        assert isinstance(metrics.timestamp, datetime)

    def test_custom_initialization(self):
        """Test PerformanceMetrics initialization with custom values"""
        custom_time = datetime(2023, 1, 1, 12, 0, 0)
        metrics = PerformanceMetrics(
            total_requests=100,
            avg_response_time=50.5,
            cache_hit_rate=85.2,
            memory_usage_mb=256.7,
            database_query_time=12.3,
            active_connections=15,
            error_rate=2.1,
            timestamp=custom_time,
        )

        assert metrics.total_requests == 100
        assert metrics.avg_response_time == 50.5
        assert metrics.cache_hit_rate == 85.2
        assert metrics.memory_usage_mb == 256.7
        assert metrics.database_query_time == 12.3
        assert metrics.active_connections == 15
        assert metrics.error_rate == 2.1
        assert metrics.timestamp == custom_time

    def test_post_init_timestamp(self):
        """Test that timestamp is set in __post_init__ when None"""
        before = datetime.now()
        metrics = PerformanceMetrics(timestamp=None)
        after = datetime.now()

        assert before <= metrics.timestamp <= after


class TestQueryOptimizer:
    """Test QueryOptimizer class"""

    def setup_method(self):
        """Setup test environment"""
        self.optimizer = QueryOptimizer()

    def test_initialization(self):
        """Test QueryOptimizer initialization"""
        assert isinstance(self.optimizer.query_cache, dict)
        assert isinstance(self.optimizer.query_stats, dict)
        assert isinstance(self.optimizer.cache_lock, threading.Lock)

    def test_measure_query_time_context_manager(self):
        """Test query time measurement context manager"""
        query_name = "test_query"

        with patch("time.perf_counter", side_effect=[0.0, 0.1]):  # Mock timing
            with self.optimizer.measure_query_time(query_name):
                pass  # Mock replaces sleep

        assert query_name in self.optimizer.query_stats
        stats = self.optimizer.query_stats[query_name]
        assert stats["count"] == 1
        assert stats["total_time"] >= 0.1
        assert stats["avg_time"] >= 0.1
        assert stats["max_time"] >= 0.1

    def test_record_query_stats_multiple_queries(self):
        """Test recording stats for multiple queries"""
        query_name = "repeated_query"

        # Record multiple executions (using mocked timing)
        with patch("time.perf_counter", side_effect=[0.0, 0.05, 0.05, 0.15, 0.15, 0.3]):
            with self.optimizer.measure_query_time(query_name):
                pass  # Mock replaces sleep

            with self.optimizer.measure_query_time(query_name):
                pass  # Mock replaces sleep

            with self.optimizer.measure_query_time(query_name):
                pass  # Mock replaces sleep

        stats = self.optimizer.query_stats[query_name]
        assert stats["count"] == 3
        assert stats["total_time"] >= 0.3
        assert stats["avg_time"] >= 0.1
        assert stats["max_time"] >= 0.15

    def test_get_slow_queries_default_threshold(self):
        """Test getting slow queries with default threshold"""
        # Add fast query
        self.optimizer._record_query_stats("fast_query", 0.5)

        # Add slow query
        self.optimizer._record_query_stats("slow_query", 1.5)

        slow_queries = self.optimizer.get_slow_queries()

        assert "slow_query" in slow_queries
        assert "fast_query" not in slow_queries

    def test_get_slow_queries_custom_threshold(self):
        """Test getting slow queries with custom threshold"""
        self.optimizer._record_query_stats("medium_query", 0.8)
        self.optimizer._record_query_stats("slow_query", 1.5)

        slow_queries = self.optimizer.get_slow_queries(threshold=0.5)

        assert "medium_query" in slow_queries
        assert "slow_query" in slow_queries

    def test_clear_stats(self):
        """Test clearing query statistics"""
        self.optimizer._record_query_stats("test_query", 1.0)
        assert len(self.optimizer.query_stats) > 0

        self.optimizer.clear_stats()
        assert len(self.optimizer.query_stats) == 0

    def test_thread_safety(self):
        """Test thread safety of query optimizer"""
        query_name = "concurrent_query"

        def run_queries():
            for _ in range(10):
                with patch("time.perf_counter", side_effect=[0.0, 0.01]):  # Mock timing
                    with self.optimizer.measure_query_time(query_name):
                        pass  # Mock replaces sleep

        # Run concurrent threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=run_queries)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have recorded all 50 queries
        stats = self.optimizer.query_stats[query_name]
        assert stats["count"] == 50


class TestSmartCache:
    """Test SmartCache class"""

    def setup_method(self):
        """Setup test environment"""
        self.cache = SmartCache(max_size=5, ttl_seconds=2)

    def test_initialization(self):
        """Test SmartCache initialization"""
        assert self.cache.max_size == 5
        assert self.cache.ttl_seconds == 2
        assert isinstance(self.cache.cache, dict)
        assert isinstance(self.cache.access_times, dict)
        assert self.cache.hit_count == 0
        assert self.cache.miss_count == 0

    def test_set_and_get_basic(self):
        """Test basic cache set and get operations"""
        key = "test_key"
        value = "test_value"

        # Should be miss initially
        result = self.cache.get(key)
        assert result is None
        assert self.cache.miss_count == 1

        # Set value
        self.cache.set(key, value)

        # Should be hit now
        result = self.cache.get(key)
        assert result == value
        assert self.cache.hit_count == 1

    def test_ttl_expiration(self):
        """Test TTL-based cache expiration"""
        key = "expiring_key"
        value = "expiring_value"

        self.cache.set(key, value)

        # Should be available immediately
        result = self.cache.get(key)
        assert result == value

        # Mock time to simulate TTL expiration
        with patch("time.time", return_value=time.time() + 3.0):
            # Should be expired now
            result = self.cache.get(key)
            assert result is None
            assert key not in self.cache.cache

    def test_lru_eviction(self):
        """Test LRU-based cache eviction"""
        # Fill cache to max capacity
        for i in range(5):
            self.cache.set(f"key_{i}", f"value_{i}")

        # Access keys to establish LRU order
        self.cache.get("key_0")  # Make key_0 most recently used
        self.cache.get("key_4")  # Make key_4 second most recently used

        # Add one more item, should evict least recently used
        self.cache.set("new_key", "new_value")

        # key_0 and key_4 should still be there (most recently used)
        assert self.cache.get("key_0") == "value_0"
        assert self.cache.get("key_4") == "value_4"
        assert self.cache.get("new_key") == "new_value"

        # Some other key should be evicted
        assert len(self.cache.cache) == 5

    def test_clear_expired(self):
        """Test clearing expired cache entries"""
        # Add items with different timestamps
        self.cache.set("fresh_key", "fresh_value")

        # Manually set an expired entry
        current_time = time.time()
        self.cache.cache["expired_key"] = {
            "value": "expired_value",
            "timestamp": current_time - 10,  # 10 seconds ago
        }
        self.cache.access_times["expired_key"] = current_time - 10

        # Clear expired items
        expired_count = self.cache.clear_expired()

        assert expired_count == 1
        assert "fresh_key" in self.cache.cache
        assert "expired_key" not in self.cache.cache

    def test_get_stats(self):
        """Test cache statistics"""
        # Perform some operations
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        self.cache.get("key1")  # hit
        self.cache.get("key3")  # miss

        stats = self.cache.get_stats()

        assert stats["size"] == 2
        assert stats["max_size"] == 5
        assert stats["hit_count"] == 1
        assert stats["miss_count"] == 1
        assert stats["hit_rate"] == 50.0
        assert stats["ttl_seconds"] == 2

    def test_thread_safety(self):
        """Test thread safety of smart cache"""

        def cache_operations():
            for i in range(100):
                self.cache.set(f"thread_key_{i}", f"value_{i}")
                self.cache.get(f"thread_key_{i}")

        # Run concurrent threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=cache_operations)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Cache should handle concurrent access gracefully
        stats = self.cache.get_stats()
        assert stats["hit_count"] > 0
        assert stats["miss_count"] >= 0


class TestMemoryOptimizer:
    """Test MemoryOptimizer class"""

    def setup_method(self):
        """Setup test environment"""
        self.optimizer = MemoryOptimizer()

    def test_initialization(self):
        """Test MemoryOptimizer initialization"""
        assert hasattr(self.optimizer, "weak_references")
        assert isinstance(self.optimizer.object_pools, dict)

    def test_create_object_pool(self):
        """Test object pool creation"""
        pool_name = "test_pool"
        factory = lambda: {"initialized": True}
        max_size = 5

        self.optimizer.create_object_pool(pool_name, factory, max_size)

        assert pool_name in self.optimizer.object_pools
        pool_info = self.optimizer.object_pools[pool_name]
        assert pool_info["factory"] == factory
        assert pool_info["max_size"] == max_size
        assert isinstance(pool_info["pool"], list)
        assert isinstance(pool_info["lock"], threading.Lock)

    def test_get_from_pool_new_object(self):
        """Test getting object from empty pool (creates new)"""
        pool_name = "test_pool"
        factory = lambda: {"counter": 1}

        self.optimizer.create_object_pool(pool_name, factory, 5)

        obj = self.optimizer.get_from_pool(pool_name)
        assert obj["counter"] == 1

    def test_get_from_pool_reused_object(self):
        """Test getting object from pool with available objects"""
        pool_name = "test_pool"
        factory = lambda: {"reused": True}

        self.optimizer.create_object_pool(pool_name, factory, 5)

        # Create and return object to pool
        obj1 = self.optimizer.get_from_pool(pool_name)
        obj1["modified"] = True
        self.optimizer.return_to_pool(pool_name, obj1)

        # Get object again - should be the same instance
        obj2 = self.optimizer.get_from_pool(pool_name)
        assert obj2 is obj1
        assert obj2["modified"] is True

    def test_get_from_pool_unknown_pool(self):
        """Test getting object from non-existent pool"""
        with pytest.raises(ValueError):
            self.optimizer.get_from_pool("unknown_pool")

    def test_return_to_pool_with_reset(self):
        """Test returning object to pool with reset method"""

        class ResettableObject:
            def __init__(self):
                self.data = "initial"

            def reset(self):
                self.data = "reset"

        pool_name = "resettable_pool"
        self.optimizer.create_object_pool(pool_name, ResettableObject, 5)

        obj = self.optimizer.get_from_pool(pool_name)
        obj.data = "modified"

        self.optimizer.return_to_pool(pool_name, obj)

        # Get object again - should be reset
        obj2 = self.optimizer.get_from_pool(pool_name)
        assert obj2 is obj
        assert obj2.data == "reset"

    def test_return_to_pool_max_size_limit(self):
        """Test pool max size enforcement"""
        pool_name = "limited_pool"
        factory = lambda: {"id": id(object())}
        max_size = 2

        self.optimizer.create_object_pool(pool_name, factory, max_size)

        # Create more objects than pool can hold
        objects = []
        for i in range(5):
            obj = self.optimizer.get_from_pool(pool_name)
            obj["index"] = i
            objects.append(obj)

        # Return all objects
        for obj in objects:
            self.optimizer.return_to_pool(pool_name, obj)

        # Pool should only hold max_size objects
        pool_info = self.optimizer.object_pools[pool_name]
        assert len(pool_info["pool"]) == max_size

    def test_optimize_large_list(self):
        """Test large list optimization"""
        large_list = list(range(2500))
        chunk_size = 1000

        chunks = self.optimizer.optimize_large_list(large_list, chunk_size)

        assert len(chunks) == 3  # 2500 / 1000 = 3 chunks
        assert len(chunks[0]) == 1000
        assert len(chunks[1]) == 1000
        assert len(chunks[2]) == 500

        # Verify all data is preserved
        flattened = [item for chunk in chunks for item in chunk]
        assert flattened == large_list

    def test_optimize_small_list(self):
        """Test small list optimization (no chunking)"""
        small_list = list(range(100))
        chunk_size = 1000

        chunks = self.optimizer.optimize_large_list(small_list, chunk_size)

        assert len(chunks) == 1
        assert chunks[0] == small_list

    def test_memory_efficient_join_small_list(self):
        """Test memory efficient join with small list"""
        items = ["a", "b", "c", "d"]
        separator = ","

        result = self.optimizer.memory_efficient_join(items, separator)
        assert result == "a,b,c,d"

    def test_memory_efficient_join_large_list(self):
        """Test memory efficient join with large list"""
        items = [str(i) for i in range(2500)]
        separator = ","

        result = self.optimizer.memory_efficient_join(items, separator)

        # Should produce same result as regular join
        expected = ",".join(items)
        assert result == expected

    def test_memory_efficient_join_empty_separator(self):
        """Test memory efficient join with empty separator"""
        items = ["hello", "world", "test"]
        result = self.optimizer.memory_efficient_join(items)
        assert result == "helloworldtest"


if __name__ == "__main__":
    pytest.main([__file__])
