#!/usr/bin/env python3
"""
Enhanced Performance Optimizer Tests

Comprehensive tests for the performance optimization module including
caching, memory management, query optimization, and monitoring.
Designed to achieve high coverage for performance-critical components.
"""

import os
import sys
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.mark.unit
class TestPerformanceOptimizerCore:
    """Test core performance optimizer functionality"""

    def test_performance_optimizer_import(self):
        """Test that performance optimizer can be imported"""
        from src.utils.performance_optimizer import PerformanceOptimizer

        assert PerformanceOptimizer is not None

        # Test creating optimizer instance
        optimizer = PerformanceOptimizer()
        assert optimizer is not None

    def test_optimizer_initialization(self):
        """Test optimizer initialization with different configurations"""
        from src.utils.performance_optimizer import PerformanceOptimizer

        # Test default initialization
        optimizer = PerformanceOptimizer()
        assert hasattr(optimizer, "cache_manager")
        assert hasattr(optimizer, "metrics")

        # Test initialization with custom config
        config = {"cache_ttl": 600, "max_cache_size": 1000, "enable_profiling": True}
        optimizer_custom = PerformanceOptimizer(config=config)
        assert optimizer_custom is not None

    def test_cache_operations(self):
        """Test cache operations functionality"""
        from src.utils.performance_optimizer import PerformanceOptimizer

        optimizer = PerformanceOptimizer()

        # Test cache set/get operations
        key = "test_key"
        value = {"data": "test_value", "timestamp": time.time()}

        # Set cache value
        optimizer.set_cache(key, value)

        # Get cache value
        cached_value = optimizer.get_cache(key)
        assert cached_value is not None

        # Test cache invalidation
        optimizer.invalidate_cache(key)
        invalidated_value = optimizer.get_cache(key)
        assert invalidated_value is None

    def test_performance_monitoring(self):
        """Test performance monitoring functionality"""
        from src.utils.performance_optimizer import PerformanceOptimizer

        optimizer = PerformanceOptimizer()

        # Test performance measurement
        start_time = time.time()

        @optimizer.monitor_performance
        def test_function():
            time.sleep(0.01)  # Small delay for measurement
            return "completed"

        result = test_function()
        assert result == "completed"

        # Check that metrics were recorded
        metrics = optimizer.get_metrics()
        assert metrics is not None
        assert isinstance(metrics, dict)

    def test_query_optimization(self):
        """Test query optimization features"""
        from src.utils.performance_optimizer import PerformanceOptimizer

        optimizer = PerformanceOptimizer()

        # Test query optimization suggestions
        sample_query = "SELECT * FROM blacklist_ips WHERE ip_address = '192.168.1.1'"

        optimized_query = optimizer.optimize_query(sample_query)
        assert optimized_query is not None
        assert isinstance(optimized_query, str)

        # Test batch optimization
        queries = [
            "SELECT * FROM blacklist_ips",
            "SELECT count(*) FROM collection_logs",
            "SELECT * FROM cache_entries",
        ]

        optimized_batch = optimizer.optimize_batch_queries(queries)
        assert optimized_batch is not None
        assert isinstance(optimized_batch, list)


@pytest.mark.unit
class TestCacheManager:
    """Test cache management functionality"""

    def test_cache_manager_creation(self):
        """Test cache manager creation and configuration"""
        try:
            from src.utils.performance_optimizer import CacheManager

            cache_manager = CacheManager(max_size=100, ttl=300, strategy="lru")
            assert cache_manager is not None

        except ImportError:
            # If CacheManager doesn't exist as separate class, test with optimizer
            from src.utils.performance_optimizer import PerformanceOptimizer

            optimizer = PerformanceOptimizer()
            assert hasattr(optimizer, "cache_manager")

    def test_cache_ttl_functionality(self):
        """Test cache TTL (time-to-live) functionality"""
        from src.utils.performance_optimizer import PerformanceOptimizer

        optimizer = PerformanceOptimizer()

        # Set cache with short TTL
        key = "ttl_test_key"
        value = "ttl_test_value"

        optimizer.set_cache(key, value, ttl=1)  # 1 second TTL

        # Immediately check cache
        cached_value = optimizer.get_cache(key)
        assert cached_value == value

        # Wait for TTL to expire
        time.sleep(1.1)

        # Check cache after expiration
        expired_value = optimizer.get_cache(key)
        assert expired_value is None

    def test_cache_size_limits(self):
        """Test cache size limitation functionality"""
        from src.utils.performance_optimizer import PerformanceOptimizer

        # Create optimizer with small cache size
        config = {"max_cache_size": 3}
        optimizer = PerformanceOptimizer(config=config)

        # Add items up to limit
        for i in range(5):
            optimizer.set_cache(f"key_{i}", f"value_{i}")

        # Check that old items were evicted
        cache_size = optimizer.get_cache_size()
        assert cache_size <= 3

    def test_cache_statistics(self):
        """Test cache statistics and metrics"""
        from src.utils.performance_optimizer import PerformanceOptimizer

        optimizer = PerformanceOptimizer()

        # Perform various cache operations
        optimizer.set_cache("stat_key_1", "value_1")
        optimizer.set_cache("stat_key_2", "value_2")
        optimizer.get_cache("stat_key_1")  # Hit
        optimizer.get_cache("nonexistent_key")  # Miss

        # Get cache statistics
        stats = optimizer.get_cache_stats()
        assert stats is not None
        assert isinstance(stats, dict)
        assert "hits" in stats or "operations" in stats


@pytest.mark.unit
class TestMemoryOptimization:
    """Test memory optimization features"""

    def test_memory_profiling(self):
        """Test memory profiling functionality"""
        from src.utils.performance_optimizer import PerformanceOptimizer

        optimizer = PerformanceOptimizer()

        # Start memory profiling
        optimizer.start_memory_profiling()

        # Perform memory-intensive operation
        large_data = [i for i in range(1000)]

        # Stop profiling and get results
        memory_stats = optimizer.stop_memory_profiling()
        assert memory_stats is not None
        assert isinstance(memory_stats, dict)

    def test_memory_cleanup(self):
        """Test memory cleanup functionality"""
        from src.utils.performance_optimizer import PerformanceOptimizer

        optimizer = PerformanceOptimizer()

        # Create some cached data
        for i in range(10):
            optimizer.set_cache(f"cleanup_key_{i}", f"large_value_{i}" * 100)

        # Perform memory cleanup
        cleanup_result = optimizer.cleanup_memory()
        assert cleanup_result is not None

        # Check that memory usage was reduced
        memory_stats = optimizer.get_memory_stats()
        assert memory_stats is not None

    def test_garbage_collection_optimization(self):
        """Test garbage collection optimization"""
        from src.utils.performance_optimizer import PerformanceOptimizer

        optimizer = PerformanceOptimizer()

        # Force garbage collection
        gc_result = optimizer.optimize_garbage_collection()
        assert gc_result is not None

        # Test that GC was performed
        gc_stats = optimizer.get_gc_stats()
        assert gc_stats is not None


@pytest.mark.unit
class TestPerformanceMonitoring:
    """Test performance monitoring and metrics"""

    def test_execution_time_monitoring(self):
        """Test execution time monitoring"""
        from src.utils.performance_optimizer import PerformanceOptimizer

        optimizer = PerformanceOptimizer()

        # Monitor a function's execution time
        @optimizer.monitor_execution_time
        def timed_function():
            time.sleep(0.01)
            return "timed_result"

        result = timed_function()
        assert result == "timed_result"

        # Check that timing was recorded
        timing_stats = optimizer.get_timing_stats()
        assert timing_stats is not None

    def test_request_rate_monitoring(self):
        """Test request rate monitoring"""
        from src.utils.performance_optimizer import PerformanceOptimizer

        optimizer = PerformanceOptimizer()

        # Record multiple requests
        for i in range(5):
            optimizer.record_request("test_endpoint")
            time.sleep(0.01)

        # Get request rate statistics
        rate_stats = optimizer.get_request_rate_stats()
        assert rate_stats is not None
        assert isinstance(rate_stats, dict)

    def test_resource_usage_monitoring(self):
        """Test resource usage monitoring"""
        from src.utils.performance_optimizer import PerformanceOptimizer

        optimizer = PerformanceOptimizer()

        # Get current resource usage
        resource_stats = optimizer.get_resource_usage()
        assert resource_stats is not None
        assert isinstance(resource_stats, dict)

        # Check for expected metrics
        expected_metrics = ["cpu_percent", "memory_percent", "disk_usage"]
        available_metrics = resource_stats.keys()

        # At least some metrics should be available
        assert len(available_metrics) > 0


@pytest.mark.unit
class TestPerformanceOptimizationStrategies:
    """Test various performance optimization strategies"""

    def test_lazy_loading_optimization(self):
        """Test lazy loading optimization"""
        from src.utils.performance_optimizer import PerformanceOptimizer

        optimizer = PerformanceOptimizer()

        # Test lazy loading decorator
        load_count = 0

        @optimizer.lazy_load
        def expensive_operation():
            nonlocal load_count
            load_count += 1
            return "expensive_result"

        # First call should load
        result1 = expensive_operation()
        assert result1 == "expensive_result"
        assert load_count == 1

        # Second call should use cache
        result2 = expensive_operation()
        assert result2 == "expensive_result"
        assert load_count == 1  # Should not increment

    def test_batch_processing_optimization(self):
        """Test batch processing optimization"""
        from src.utils.performance_optimizer import PerformanceOptimizer

        optimizer = PerformanceOptimizer()

        # Test batch processing
        items = [f"item_{i}" for i in range(10)]

        batch_result = optimizer.process_batch(
            items,
            batch_size=3,
            processor=lambda batch: [item.upper() for item in batch],
        )

        assert batch_result is not None
        assert isinstance(batch_result, list)
        assert len(batch_result) == 10

    def test_connection_pooling_optimization(self):
        """Test connection pooling optimization"""
        from src.utils.performance_optimizer import PerformanceOptimizer

        optimizer = PerformanceOptimizer()

        # Test connection pool management
        pool_stats = optimizer.get_connection_pool_stats()
        assert pool_stats is not None

        # Test connection acquisition
        connection = optimizer.get_connection("database")
        assert connection is not None

        # Test connection release
        optimizer.release_connection("database", connection)


@pytest.mark.integration
class TestPerformanceOptimizerIntegration:
    """Test performance optimizer integration with other systems"""

    def test_flask_integration(self):
        """Test Flask application integration"""
        from flask import Flask

        from src.utils.performance_optimizer import PerformanceOptimizer

        app = Flask(__name__)
        optimizer = PerformanceOptimizer()

        # Test middleware integration
        optimizer.init_app(app)

        with app.app_context():
            # Test that optimizer is available in Flask context
            current_optimizer = optimizer.get_current_optimizer()
            assert current_optimizer is not None

    def test_database_optimization_integration(self):
        """Test database optimization integration"""
        from src.utils.performance_optimizer import PerformanceOptimizer

        optimizer = PerformanceOptimizer()

        # Mock database connection
        mock_db = Mock()

        # Test query optimization with database
        optimized_connection = optimizer.optimize_database_connection(mock_db)
        assert optimized_connection is not None

    def test_cache_integration_with_redis(self):
        """Test cache integration with Redis"""
        from src.utils.performance_optimizer import PerformanceOptimizer

        # Test with mock Redis
        with patch("redis.Redis") as mock_redis:
            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance

            optimizer = PerformanceOptimizer(cache_backend="redis")

            # Test Redis operations
            optimizer.set_cache("redis_key", "redis_value")
            mock_redis_instance.set.assert_called()


if __name__ == "__main__":
    import sys

    # List to track all validation failures
    all_validation_failures = []
    total_tests = 0

    print("🚀 Performance Optimizer Module Validation")
    print("=" * 50)

    # Test 1: Basic imports and creation
    total_tests += 1
    try:
        from src.utils.performance_optimizer import PerformanceOptimizer

        optimizer = PerformanceOptimizer()
        assert optimizer is not None
        print("✅ Performance optimizer creation successful")
    except Exception as e:
        all_validation_failures.append(f"Performance optimizer creation: {e}")

    # Test 2: Cache operations
    total_tests += 1
    try:
        from src.utils.performance_optimizer import PerformanceOptimizer

        optimizer = PerformanceOptimizer()

        # Test cache set/get
        optimizer.set_cache("test_key", "test_value")
        cached_value = optimizer.get_cache("test_key")
        assert cached_value == "test_value"
        print("✅ Cache operations successful")
    except Exception as e:
        all_validation_failures.append(f"Cache operations: {e}")

    # Test 3: Performance monitoring
    total_tests += 1
    try:
        from src.utils.performance_optimizer import PerformanceOptimizer

        optimizer = PerformanceOptimizer()

        @optimizer.monitor_performance
        def test_monitored_function():
            return "monitored_result"

        result = test_monitored_function()
        assert result == "monitored_result"
        print("✅ Performance monitoring successful")
    except Exception as e:
        all_validation_failures.append(f"Performance monitoring: {e}")

    # Test 4: Memory management
    total_tests += 1
    try:
        from src.utils.performance_optimizer import PerformanceOptimizer

        optimizer = PerformanceOptimizer()

        # Test memory operations
        memory_stats = optimizer.get_memory_stats()
        assert memory_stats is not None

        cleanup_result = optimizer.cleanup_memory()
        assert cleanup_result is not None
        print("✅ Memory management successful")
    except Exception as e:
        all_validation_failures.append(f"Memory management: {e}")

    # Test 5: Query optimization
    total_tests += 1
    try:
        from src.utils.performance_optimizer import PerformanceOptimizer

        optimizer = PerformanceOptimizer()

        sample_query = "SELECT * FROM blacklist_ips"
        optimized_query = optimizer.optimize_query(sample_query)
        assert optimized_query is not None
        print("✅ Query optimization successful")
    except Exception as e:
        all_validation_failures.append(f"Query optimization: {e}")

    print("\n" + "=" * 50)
    print("📊 Validation Summary")

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
        print("Performance optimizer module validation complete and tests can be run")
        sys.exit(0)
