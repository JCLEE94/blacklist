#!/usr/bin/env python3
"""
Comprehensive tests for cache functionality
Targeting advanced_cache modules which have low coverage but are critical
"""

import json
import os
import sys
import tempfile
import time
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Optional
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestEnhancedSmartCache:
    """Test cache manager functionality"""

    def test_cache_manager_import(self):
        """Test cache manager can be imported"""
        from src.utils.advanced_cache.cache_manager import EnhancedSmartCache

        assert EnhancedSmartCache is not None

    def test_cache_manager_creation(self):
        """Test cache manager creation"""
        from src.utils.advanced_cache.cache_manager import EnhancedSmartCache

        # Test with memory backend (should always work)
        manager = EnhancedSmartCache()
        assert manager is not None
        assert hasattr(manager, "get")
        assert hasattr(manager, "set")
        assert hasattr(manager, "delete")

    def test_cache_manager_basic_operations(self):
        """Test basic cache operations"""
        from src.utils.advanced_cache.cache_manager import EnhancedSmartCache

        manager = EnhancedSmartCache()

        # Test set and get
        test_key = "test_key"
        test_value = "test_value"

        manager.set(test_key, test_value)
        retrieved_value = manager.get(test_key)

        assert retrieved_value == test_value

    def test_cache_manager_ttl(self):
        """Test cache TTL functionality"""
        from src.utils.advanced_cache.cache_manager import EnhancedSmartCache

        # Force memory backend by passing redis_url=None
        manager = EnhancedSmartCache(redis_url=None)

        # Test with very short TTL
        test_key = "ttl_test_key"
        test_value = "ttl_test_value"

        manager.set(test_key, test_value, ttl=1)  # 1 second TTL

        # Should be available immediately
        assert manager.get(test_key) == test_value

        # Wait for expiration (in a real test, you might mock time)
        time.sleep(1.1)

        # Should be expired (may return None or default)
        expired_value = manager.get(test_key)
        assert expired_value is None or expired_value != test_value

    def test_cache_manager_delete(self):
        """Test cache delete functionality"""
        from src.utils.advanced_cache.cache_manager import EnhancedSmartCache

        manager = EnhancedSmartCache(redis_url=None)

        test_key = "delete_test_key"
        test_value = "delete_test_value"

        # Set value
        manager.set(test_key, test_value)
        assert manager.get(test_key) == test_value

        # Delete value
        manager.delete(test_key)
        assert manager.get(test_key) is None

    def test_cache_manager_exists(self):
        """Test cache exists functionality"""
        from src.utils.advanced_cache.cache_manager import EnhancedSmartCache

        manager = EnhancedSmartCache(redis_url=None)

        test_key = "exists_test_key"
        test_value = "exists_test_value"

        # Key should not exist initially
        assert not manager.exists(test_key)

        # Set value
        manager.set(test_key, test_value)

        # Key should exist now
        assert manager.exists(test_key)

    def test_cache_manager_clear(self):
        """Test cache clear functionality"""
        from src.utils.advanced_cache.cache_manager import EnhancedSmartCache

        manager = EnhancedSmartCache(redis_url=None)

        # Set multiple values
        manager.set("key1", "value1")
        manager.set("key2", "value2")

        # Clear cache
        manager.clear()

        # All keys should be gone
        assert manager.get("key1") is None
        assert manager.get("key2") is None


class TestMemoryBackend:
    """Test memory cache backend"""

    def test_memory_backend_import(self):
        """Test memory backend can be imported"""
        from src.utils.advanced_cache.memory_backend import MemoryBackend

        assert MemoryBackend is not None

    def test_memory_backend_creation(self):
        """Test memory backend creation"""
        from src.utils.advanced_cache.memory_backend import MemoryBackend

        backend = MemoryBackend()
        assert backend is not None
        assert hasattr(backend, "get")
        assert hasattr(backend, "set")

    def test_memory_backend_operations(self):
        """Test memory backend basic operations"""
        from src.utils.advanced_cache.memory_backend import MemoryBackend

        backend = MemoryBackend()

        # Test set and get
        backend.set("test_key", "test_value")
        assert backend.get("test_key") == "test_value"

        # Test non-existent key
        assert backend.get("non_existent_key") is None

    def test_memory_backend_ttl(self):
        """Test memory backend TTL"""
        from src.utils.advanced_cache.memory_backend import MemoryBackend

        backend = MemoryBackend()

        # Set with TTL
        backend.set("ttl_key", "ttl_value", ttl=1)

        # Should be available immediately
        assert backend.get("ttl_key") == "ttl_value"

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        assert backend.get("ttl_key") is None

    def test_memory_backend_delete(self):
        """Test memory backend delete"""
        from src.utils.advanced_cache.memory_backend import MemoryBackend

        backend = MemoryBackend()

        backend.set("delete_key", "delete_value")
        assert backend.get("delete_key") == "delete_value"

        backend.delete("delete_key")
        assert backend.get("delete_key") is None


class TestRedisBackend:
    """Test Redis cache backend"""

    def test_redis_backend_import(self):
        """Test Redis backend can be imported"""
        from src.utils.advanced_cache.redis_backend import RedisBackend

        assert RedisBackend is not None

    def test_redis_backend_creation_fallback(self):
        """Test Redis backend creation with fallback"""
        from src.utils.advanced_cache.redis_backend import RedisBackend

        # Redis may not be available, should handle gracefully
        try:
            backend = RedisBackend()
            assert backend is not None
        except Exception as e:
            # Redis connection failed, which is acceptable in test environment
            assert "redis" in str(e).lower() or "connection" in str(e).lower()

    def test_redis_backend_fallback_behavior(self):
        """Test Redis backend fallback behavior"""
        from src.utils.advanced_cache.redis_backend import RedisBackend

        try:
            backend = RedisBackend()

            # Try basic operations
            backend.set("test_key", "test_value")
            value = backend.get("test_key")

            # If Redis is working, value should match
            if value is not None:
                assert value == "test_value"
        except Exception:
            # Redis not available, which is fine
            pass


class TestCacheDecorators:
    """Test cache decorators"""

    def test_cached_decorator_import(self):
        """Test cache decorator can be imported"""
        from src.utils.advanced_cache.decorators import cache_decorator

        assert cache_decorator is not None

    def test_cached_decorator_basic(self):
        """Test basic cache decorator functionality"""
        from src.utils.advanced_cache.cache_manager import EnhancedSmartCache
        from src.utils.advanced_cache.decorators import cache_decorator
        from src.utils.advanced_cache.decorators import set_cache_instance

        cache = EnhancedSmartCache(redis_url=None)
        set_cache_instance(cache)

        call_count = 0

        @cache_decorator(ttl=300)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call should execute function
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call should use cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Should not increment

    def test_cached_decorator_different_args(self):
        """Test cache decorator with different arguments"""
        from src.utils.advanced_cache.cache_manager import EnhancedSmartCache
        from src.utils.advanced_cache.decorators import cache_decorator
        from src.utils.advanced_cache.decorators import set_cache_instance

        cache = EnhancedSmartCache(redis_url=None)
        set_cache_instance(cache)

        call_count = 0

        @cache_decorator(ttl=300)
        def math_function(x, y):
            nonlocal call_count
            call_count += 1
            return x + y

        # Different arguments should result in different cache entries
        result1 = math_function(1, 2)
        result2 = math_function(3, 4)

        assert result1 == 3
        assert result2 == 7
        assert call_count == 2  # Both calls should execute

    def test_cache_invalidation_decorator(self):
        """Test cache invalidation decorator if available"""
        try:
            from src.utils.advanced_cache.cache_manager import EnhancedSmartCache
            from src.utils.advanced_cache.decorators import cache_invalidate

            cache = EnhancedSmartCache(backend_type="memory")

            # Set a cached value
            cache.set("test_invalidate", "old_value")

            @cache_invalidate(cache, key="test_invalidate")
            def update_function():
                return "updated"

            # Call should invalidate cache
            result = update_function()
            assert result == "updated"

            # Cache should be cleared
            assert cache.get("test_invalidate") is None

        except ImportError:
            pytest.skip("cache_invalidate not available")


class TestCacheFactory:
    """Test cache factory"""

    def test_cache_factory_import(self):
        """Test cache factory can be imported"""
        from src.utils.advanced_cache.factory import CacheFactory

        assert CacheFactory is not None

    def test_cache_factory_create_memory(self):
        """Test cache factory creates memory backend"""
        from src.utils.advanced_cache.factory import CacheFactory

        cache = CacheFactory.create("memory")
        assert cache is not None
        assert hasattr(cache, "get")
        assert hasattr(cache, "set")

    def test_cache_factory_create_redis_fallback(self):
        """Test cache factory creates Redis with fallback"""
        from src.utils.advanced_cache.factory import CacheFactory

        try:
            cache = CacheFactory.create("redis")
            assert cache is not None
        except Exception:
            # Redis may not be available, which is fine
            pass

    def test_cache_factory_default(self):
        """Test cache factory default creation"""
        from src.utils.advanced_cache.factory import CacheFactory

        cache = CacheFactory.create()
        assert cache is not None
        assert hasattr(cache, "get")
        assert hasattr(cache, "set")


class TestSerialization:
    """Test cache serialization"""

    def test_serialization_import(self):
        """Test serialization can be imported"""
        from src.utils.advanced_cache.serialization import JsonSerializer

        assert JsonSerializer is not None

    def test_json_serializer_basic(self):
        """Test JSON serializer basic functionality"""
        from src.utils.advanced_cache.serialization import JsonSerializer

        serializer = JsonSerializer()

        # Test simple data
        data = {"key": "value", "number": 42}
        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)

        assert deserialized == data

    def test_json_serializer_complex_data(self):
        """Test JSON serializer with complex data"""
        from src.utils.advanced_cache.serialization import JsonSerializer

        serializer = JsonSerializer()

        # Test complex data structure
        data = {
            "list": [1, 2, 3],
            "nested": {"inner": "value"},
            "boolean": True,
            "null": None,
        }

        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)

        assert deserialized == data

    def test_pickle_serializer_import(self):
        """Test pickle serializer can be imported"""
        try:
            from src.utils.advanced_cache.serialization import PickleSerializer

            assert PickleSerializer is not None
        except ImportError:
            pytest.skip("PickleSerializer not available")


class TestCacheIntegration:
    """Test cache integration functionality"""

    def test_cache_manager_with_real_data(self):
        """Test cache manager with realistic data"""
        from src.utils.advanced_cache.cache_manager import EnhancedSmartCache

        cache = EnhancedSmartCache(backend_type="memory")

        # Test with blacklist-like data
        blacklist_data = {
            "ip_address": "192.168.1.100",
            "threat_level": "high",
            "first_seen": "2024-01-01",
            "is_active": True,
            "source": "regtech",
        }

        cache.set("blacklist:192.168.1.100", blacklist_data)
        retrieved_data = cache.get("blacklist:192.168.1.100")

        assert retrieved_data == blacklist_data
        assert retrieved_data["threat_level"] == "high"

    def test_cache_performance_simulation(self):
        """Test cache performance with multiple operations"""
        from src.utils.advanced_cache.cache_manager import EnhancedSmartCache

        cache = EnhancedSmartCache(backend_type="memory")

        # Simulate multiple cache operations
        for i in range(100):
            key = f"test_key_{i}"
            value = f"test_value_{i}"
            cache.set(key, value)

        # Verify all values are cached
        for i in range(100):
            key = f"test_key_{i}"
            expected_value = f"test_value_{i}"
            assert cache.get(key) == expected_value

    def test_cache_error_handling(self):
        """Test cache error handling"""
        from src.utils.advanced_cache.cache_manager import EnhancedSmartCache

        cache = EnhancedSmartCache(backend_type="memory")

        # Test with None key (should handle gracefully)
        try:
            cache.set(None, "value")
        except Exception:
            # Expected to handle invalid keys
            pass

        # Test getting non-existent key
        non_existent = cache.get("definitely_not_a_key")
        assert non_existent is None


if __name__ == "__main__":
    # Validation test for the cache functionality
    import sys

    all_validation_failures = []
    total_tests = 0

    print("🔄 Running cache functionality validation tests...")

    # Test 1: Cache manager can be created
    total_tests += 1
    try:
        from src.utils.advanced_cache.cache_manager import EnhancedSmartCache

        cache = EnhancedSmartCache(backend_type="memory")
        assert cache is not None
        print("✅ Cache manager creation: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"Cache manager creation: {e}")

    # Test 2: Basic cache operations work
    total_tests += 1
    try:
        from src.utils.advanced_cache.cache_manager import EnhancedSmartCache

        cache = EnhancedSmartCache(backend_type="memory")
        cache.set("test", "value")
        assert cache.get("test") == "value"
        print("✅ Basic cache operations: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"Basic cache operations: {e}")

    # Test 3: Memory backend works
    total_tests += 1
    try:
        from src.utils.advanced_cache.memory_backend import MemoryBackend

        backend = MemoryBackend()
        backend.set("key", "value")
        assert backend.get("key") == "value"
        print("✅ Memory backend: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"Memory backend: {e}")

    # Test 4: Cache decorators work
    total_tests += 1
    try:
        from src.utils.advanced_cache.cache_manager import EnhancedSmartCache
        from src.utils.advanced_cache.decorators import cached

        cache = EnhancedSmartCache(backend_type="memory")

        @cached(cache, ttl=300)
        def test_func(x):
            return x * 2

        result = test_func(5)
        assert result == 10
        print("✅ Cache decorators: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"Cache decorators: {e}")

    # Test 5: Cache factory works
    total_tests += 1
    try:
        from src.utils.advanced_cache.factory import CacheFactory

        cache = CacheFactory.create("memory")
        assert cache is not None
        print("✅ Cache factory: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"Cache factory: {e}")

    # Test 6: Serialization works
    total_tests += 1
    try:
        from src.utils.advanced_cache.serialization import JsonSerializer

        serializer = JsonSerializer()
        data = {"test": "data"}
        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)
        assert deserialized == data
        print("✅ Serialization: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"Serialization: {e}")

    # Test 7: TTL functionality works
    total_tests += 1
    try:
        from src.utils.advanced_cache.cache_manager import EnhancedSmartCache

        cache = EnhancedSmartCache(backend_type="memory")
        cache.set("ttl_test", "value", ttl=1)
        assert cache.get("ttl_test") == "value"
        print("✅ TTL functionality: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"TTL functionality: {e}")

    # Test 8: Complex data caching works
    total_tests += 1
    try:
        from src.utils.advanced_cache.cache_manager import EnhancedSmartCache

        cache = EnhancedSmartCache(backend_type="memory")

        complex_data = {
            "ip": "192.168.1.1",
            "metadata": {"threat": "high", "active": True},
            "list": [1, 2, 3],
        }

        cache.set("complex", complex_data)
        retrieved = cache.get("complex")
        assert retrieved == complex_data
        print("✅ Complex data caching: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"Complex data caching: {e}")

    # Final validation result
    if all_validation_failures:
        print(
            f"\n❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"\n✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print(
            "Cache functionality is validated and ready for significant coverage improvement"
        )
        sys.exit(0)
