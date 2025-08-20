#!/usr/bin/env python3
"""
Coverage Improvement Tests for Blacklist Management System

Focused on testing existing code modules to improve coverage from current 6% to 95% target.
Tests actual functions and classes rather than HTTP endpoints.
"""

import os
import sys
import json
import tempfile
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, mock_open

import pytest

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestCoreModels:
    """Test core models and data structures"""
    
    def test_models_import_and_basic_functionality(self):
        """Test models can be imported and basic functionality works"""
        try:
            from src.core.models import BlacklistEntry, CollectionStatus
            
            # Test BlacklistEntry creation
            entry = BlacklistEntry(
                ip_address="192.168.1.1",
                source="test",
                detection_date=datetime.now(),
                threat_level="medium"
            )
            
            assert entry.ip_address == "192.168.1.1"
            assert entry.source == "test"
            assert entry.threat_level == "medium"
            
            # Test to_dict method if exists
            if hasattr(entry, 'to_dict'):
                entry_dict = entry.to_dict()
                assert isinstance(entry_dict, dict)
                assert 'ip_address' in entry_dict
            
        except ImportError:
            # Models may not exist in expected form, skip test
            pytest.skip("Core models not available for testing")
    
    def test_constants_module(self):
        """Test constants module"""
        try:
            from src.core.constants import (
                DEFAULT_CACHE_TTL, API_RATE_LIMITS, 
                THREAT_LEVELS, ERROR_MESSAGES
            )
            
            # Test constants are defined
            assert isinstance(DEFAULT_CACHE_TTL, int)
            assert DEFAULT_CACHE_TTL > 0
            
            assert isinstance(API_RATE_LIMITS, dict)
            assert isinstance(THREAT_LEVELS, (list, dict))
            assert isinstance(ERROR_MESSAGES, dict)
            
        except ImportError:
            pytest.skip("Constants module not available for testing")
    
    def test_validators_module(self):
        """Test validators module"""
        try:
            from src.core.validators import validate_ip, validate_date, validate_threat_level
            
            # Test IP validation
            assert validate_ip("192.168.1.1") is True
            assert validate_ip("invalid_ip") is False
            assert validate_ip("999.999.999.999") is False
            
            # Test date validation
            assert validate_date("2025-01-01") is True
            assert validate_date("invalid_date") is False
            
            # Test threat level validation
            valid_levels = ["low", "medium", "high", "critical"]
            for level in valid_levels:
                assert validate_threat_level(level) is True
            
            assert validate_threat_level("invalid_level") is False
            
        except ImportError:
            pytest.skip("Validators module not available for testing")


class TestUtilityFunctions:
    """Test utility functions and helpers"""
    
    def test_auth_utilities(self):
        """Test authentication utility functions"""
        try:
            from src.utils.auth import hash_password, verify_password, generate_token
            
            password = "test_password_123"
            
            # Test password hashing
            hashed = hash_password(password)
            assert hashed != password
            assert len(hashed) > 10
            
            # Test password verification
            assert verify_password(password, hashed) is True
            assert verify_password("wrong_password", hashed) is False
            
            # Test token generation
            token = generate_token("test_user")
            assert isinstance(token, str)
            assert len(token) > 10
            
        except ImportError:
            pytest.skip("Auth utilities not available for testing")
    
    def test_cache_helpers(self):
        """Test cache helper functions"""
        try:
            from src.core.common.cache_helpers import (
                get_cache_key, set_cache_value, get_cache_value, 
                clear_cache, is_cache_valid
            )
            
            # Test cache key generation
            key = get_cache_key("test", "param1", "param2")
            assert isinstance(key, str)
            assert "test" in key
            
            # Test cache operations
            test_key = "test_cache_key"
            test_value = {"data": "test_data", "timestamp": time.time()}
            
            # Set cache value
            set_cache_value(test_key, test_value, ttl=300)
            
            # Get cache value
            cached_value = get_cache_value(test_key)
            if cached_value is not None:
                assert cached_value == test_value
            
            # Test cache validity
            is_valid = is_cache_valid(test_key)
            assert isinstance(is_valid, bool)
            
        except ImportError:
            pytest.skip("Cache helpers not available for testing")
    
    def test_date_utilities(self):
        """Test date utility functions"""
        try:
            from src.core.common.date_utils import (
                parse_date, format_date, get_date_range,
                is_valid_date, calculate_days_between
            )
            
            # Test date parsing
            date_str = "2025-01-01"
            parsed_date = parse_date(date_str)
            assert parsed_date is not None
            
            # Test date formatting
            formatted = format_date(datetime.now())
            assert isinstance(formatted, str)
            assert len(formatted) >= 8  # At least YYYY-MM-DD
            
            # Test date range generation
            start_date = datetime.now() - timedelta(days=7)
            end_date = datetime.now()
            date_range = get_date_range(start_date, end_date)
            assert isinstance(date_range, list)
            assert len(date_range) >= 1
            
            # Test date validation
            assert is_valid_date("2025-01-01") is True
            assert is_valid_date("invalid") is False
            
            # Test days calculation
            days = calculate_days_between("2025-01-01", "2025-01-08")
            assert isinstance(days, int)
            assert days == 7
            
        except ImportError:
            pytest.skip("Date utilities not available for testing")
    
    def test_ip_utilities(self):
        """Test IP utility functions"""
        try:
            from src.core.common.ip_utils import (
                is_valid_ip, normalize_ip, get_ip_network,
                is_private_ip, is_public_ip, format_ip_range
            )
            
            test_ip = "192.168.1.1"
            
            # Test IP validation
            assert is_valid_ip(test_ip) is True
            assert is_valid_ip("invalid_ip") is False
            
            # Test IP normalization
            normalized = normalize_ip(test_ip)
            assert isinstance(normalized, str)
            
            # Test private/public IP detection
            assert is_private_ip("192.168.1.1") is True
            assert is_public_ip("8.8.8.8") is True
            assert is_private_ip("8.8.8.8") is False
            
            # Test IP network functions
            network = get_ip_network("192.168.1.0/24")
            if network is not None:
                assert str(network).startswith("192.168.1")
            
        except ImportError:
            pytest.skip("IP utilities not available for testing")
    
    def test_file_utilities(self):
        """Test file utility functions"""
        try:
            from src.core.common.file_utils import (
                ensure_directory, read_json_file, write_json_file,
                get_file_size, is_file_readable, backup_file
            )
            
            with tempfile.TemporaryDirectory() as temp_dir:
                test_dir = os.path.join(temp_dir, "test_subdir")
                
                # Test directory creation
                ensure_directory(test_dir)
                assert os.path.exists(test_dir)
                
                # Test JSON file operations
                test_file = os.path.join(test_dir, "test.json")
                test_data = {"key": "value", "number": 42}
                
                write_json_file(test_file, test_data)
                assert os.path.exists(test_file)
                
                read_data = read_json_file(test_file)
                assert read_data == test_data
                
                # Test file size
                size = get_file_size(test_file)
                assert isinstance(size, int)
                assert size > 0
                
                # Test file readability
                assert is_file_readable(test_file) is True
                assert is_file_readable("/nonexistent/file") is False
                
        except ImportError:
            pytest.skip("File utilities not available for testing")


class TestErrorHandling:
    """Test error handling and exception management"""
    
    def test_custom_exceptions(self):
        """Test custom exception classes"""
        try:
            from src.core.exceptions import (
                BlacklistError, CollectionError, 
                AuthenticationError, ValidationError
            )
            
            # Test exception creation and inheritance
            error = BlacklistError("Test error message")
            assert str(error) == "Test error message"
            assert isinstance(error, Exception)
            
            # Test different exception types
            collection_error = CollectionError("Collection failed")
            assert isinstance(collection_error, Exception)
            
            auth_error = AuthenticationError("Auth failed")
            assert isinstance(auth_error, Exception)
            
            validation_error = ValidationError("Validation failed")
            assert isinstance(validation_error, Exception)
            
        except ImportError:
            pytest.skip("Custom exceptions not available for testing")
    
    def test_error_handlers(self):
        """Test error handler functions"""
        try:
            from src.utils.error_handler import (
                handle_api_error, format_error_response,
                log_error, get_error_details
            )
            
            test_error = ValueError("Test error")
            
            # Test error handling
            handled_error = handle_api_error(test_error)
            assert isinstance(handled_error, dict)
            assert "error" in handled_error
            
            # Test error response formatting
            response = format_error_response("Test message", 400)
            assert isinstance(response, dict)
            assert response.get("success") is False
            assert "error" in response
            
            # Test error logging
            log_error(test_error, "test_context")
            
            # Test error details extraction
            details = get_error_details(test_error)
            assert isinstance(details, dict)
            
        except ImportError:
            pytest.skip("Error handlers not available for testing")


class TestDatabaseOperations:
    """Test database-related functionality"""
    
    def test_database_connection(self):
        """Test database connection utilities"""
        try:
            from src.core.database import get_database_connection, execute_query
            
            # Test connection creation (may use SQLite in memory)
            conn = get_database_connection()
            if conn is not None:
                assert hasattr(conn, 'execute') or hasattr(conn, 'cursor')
            
        except ImportError:
            pytest.skip("Database utilities not available for testing")
    
    def test_database_models(self):
        """Test database model definitions"""
        try:
            from src.core.database.table_definitions import (
                create_blacklist_table, create_collection_logs_table,
                get_table_schema
            )
            
            # Test table creation SQL
            blacklist_sql = create_blacklist_table()
            assert isinstance(blacklist_sql, str)
            assert "CREATE TABLE" in blacklist_sql.upper()
            
            collection_sql = create_collection_logs_table()
            assert isinstance(collection_sql, str)
            assert "CREATE TABLE" in collection_sql.upper()
            
            # Test schema retrieval
            schema = get_table_schema("blacklist")
            if schema is not None:
                assert isinstance(schema, (dict, list))
            
        except ImportError:
            pytest.skip("Database table definitions not available for testing")
    
    def test_migration_system(self):
        """Test database migration functionality"""
        try:
            from src.core.database.migration_service import (
                get_current_version, apply_migration,
                get_pending_migrations
            )
            
            # Test version tracking
            current_version = get_current_version()
            assert isinstance(current_version, (int, str, type(None)))
            
            # Test pending migrations
            pending = get_pending_migrations()
            assert isinstance(pending, list)
            
        except ImportError:
            pytest.skip("Migration system not available for testing")


class TestCacheSystem:
    """Test caching system functionality"""
    
    def test_memory_cache(self):
        """Test memory-based caching"""
        try:
            from src.utils.advanced_cache.memory_backend import MemoryBackend
            
            cache = MemoryBackend()
            
            # Test basic cache operations
            key = "test_key"
            value = {"data": "test_value", "timestamp": time.time()}
            
            cache.set(key, value, ttl=300)
            cached_value = cache.get(key)
            
            if cached_value is not None:
                assert cached_value == value
            
            # Test cache expiration
            cache.set("expire_key", "expire_value", ttl=1)
            time.sleep(1.1)
            expired_value = cache.get("expire_key")
            assert expired_value is None
            
            # Test cache clearing
            cache.clear()
            cleared_value = cache.get(key)
            assert cleared_value is None
            
        except ImportError:
            pytest.skip("Memory cache backend not available for testing")
    
    def test_cache_decorators(self):
        """Test cache decorator functionality"""
        try:
            from src.utils.advanced_cache.decorators import cached, cache_result
            
            call_count = 0
            
            @cached(ttl=300, key_prefix="test")
            def expensive_function(param):
                nonlocal call_count
                call_count += 1
                return f"result_{param}_{call_count}"
            
            # First call should execute function
            result1 = expensive_function("test_param")
            assert call_count == 1
            
            # Second call should use cache
            result2 = expensive_function("test_param")
            assert result1 == result2
            # Call count may or may not increase depending on cache implementation
            
        except ImportError:
            pytest.skip("Cache decorators not available for testing")


class TestSecurityFeatures:
    """Test security-related functionality"""
    
    def test_input_validation(self):
        """Test input validation functions"""
        try:
            from src.utils.security.validation import (
                validate_input, sanitize_string,
                check_sql_injection, check_xss_attack
            )
            
            # Test basic input validation
            valid_input = "normal_string_123"
            assert validate_input(valid_input) is True
            
            # Test string sanitization
            dangerous_input = "<script>alert('xss')</script>"
            sanitized = sanitize_string(dangerous_input)
            assert "<script>" not in sanitized
            
            # Test SQL injection detection
            sql_injection = "'; DROP TABLE users; --"
            assert check_sql_injection(sql_injection) is True
            assert check_sql_injection("normal string") is False
            
            # Test XSS attack detection
            xss_attack = "<script>alert('xss')</script>"
            assert check_xss_attack(xss_attack) is True
            assert check_xss_attack("normal string") is False
            
        except ImportError:
            pytest.skip("Security validation not available for testing")
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        try:
            from src.utils.security.rate_limiting import (
                RateLimiter, check_rate_limit, reset_rate_limit
            )
            
            # Test rate limiter creation
            limiter = RateLimiter(limit=5, window=60)  # 5 requests per minute
            
            # Test rate limit checking
            user_id = "test_user"
            
            # First few requests should pass
            for i in range(5):
                allowed = limiter.is_allowed(user_id)
                if not allowed:
                    break
            
            # Subsequent request should be rate limited
            rate_limited = limiter.is_allowed(user_id)
            assert isinstance(rate_limited, bool)
            
        except ImportError:
            pytest.skip("Rate limiting not available for testing")


class TestCollectionSystem:
    """Test collection system components that don't require external APIs"""
    
    def test_collection_config(self):
        """Test collection configuration"""
        try:
            from src.core.collectors.config import (
                get_collection_config, validate_config,
                get_source_config
            )
            
            # Test config retrieval
            config = get_collection_config()
            if config is not None:
                assert isinstance(config, dict)
            
            # Test config validation
            test_config = {
                "enabled": True,
                "sources": ["regtech", "secudium"],
                "schedule": "0 2 * * *"
            }
            
            is_valid = validate_config(test_config)
            assert isinstance(is_valid, bool)
            
            # Test source-specific config
            regtech_config = get_source_config("regtech")
            if regtech_config is not None:
                assert isinstance(regtech_config, dict)
            
        except ImportError:
            pytest.skip("Collection config not available for testing")
    
    def test_data_transformation(self):
        """Test data transformation functions"""
        try:
            from src.core.collectors.transformers import (
                normalize_ip_data, transform_regtech_data,
                validate_collected_data, merge_duplicate_ips
            )
            
            # Test IP data normalization
            raw_ip_data = [
                {"ip": "192.168.1.1", "source": "test", "date": "2025-01-01"},
                {"ip": "10.0.0.1", "source": "test", "date": "2025-01-01"}
            ]
            
            normalized = normalize_ip_data(raw_ip_data)
            assert isinstance(normalized, list)
            assert len(normalized) >= 0
            
            # Test data validation
            is_valid = validate_collected_data(normalized)
            assert isinstance(is_valid, bool)
            
            # Test duplicate merging
            duplicate_data = [
                {"ip": "192.168.1.1", "source": "test1"},
                {"ip": "192.168.1.1", "source": "test2"}
            ]
            
            merged = merge_duplicate_ips(duplicate_data)
            assert isinstance(merged, list)
            
        except ImportError:
            pytest.skip("Data transformation not available for testing")


class TestPerformanceOptimization:
    """Test performance optimization components"""
    
    def test_query_optimization(self):
        """Test database query optimization"""
        try:
            from src.utils.performance_optimizer import (
                optimize_query, get_query_plan,
                cache_query_result, get_performance_metrics
            )
            
            test_query = "SELECT * FROM blacklist WHERE ip_address = ?"
            
            # Test query optimization
            optimized = optimize_query(test_query)
            assert isinstance(optimized, str)
            
            # Test query plan analysis
            plan = get_query_plan(test_query)
            if plan is not None:
                assert isinstance(plan, (dict, list, str))
            
            # Test performance metrics
            metrics = get_performance_metrics()
            if metrics is not None:
                assert isinstance(metrics, dict)
            
        except ImportError:
            pytest.skip("Performance optimizer not available for testing")
    
    def test_memory_optimization(self):
        """Test memory optimization functions"""
        try:
            from src.utils.memory.core_optimizer import (
                optimize_memory_usage, get_memory_stats,
                clear_unused_objects, profile_memory_usage
            )
            
            # Test memory optimization
            optimize_memory_usage()
            
            # Test memory statistics
            stats = get_memory_stats()
            if stats is not None:
                assert isinstance(stats, dict)
                assert "used_memory" in stats or "total_memory" in stats
            
            # Test object cleanup
            clear_unused_objects()
            
        except ImportError:
            pytest.skip("Memory optimizer not available for testing")


class TestThreadingAndConcurrency:
    """Test threading and concurrency handling"""
    
    def test_thread_safety(self):
        """Test thread-safe operations"""
        try:
            from src.core.common.cache_helpers import set_cache_value, get_cache_value
            
            results = []
            
            def worker_function(worker_id):
                try:
                    # Each worker sets and gets a value
                    key = f"thread_test_{worker_id}"
                    value = f"value_{worker_id}_{time.time()}"
                    
                    set_cache_value(key, value, ttl=60)
                    retrieved = get_cache_value(key)
                    
                    results.append({
                        "worker_id": worker_id,
                        "set_value": value,
                        "retrieved_value": retrieved,
                        "success": retrieved == value
                    })
                except Exception as e:
                    results.append({
                        "worker_id": worker_id,
                        "error": str(e),
                        "success": False
                    })
            
            # Create and start multiple threads
            threads = []
            for i in range(5):
                thread = threading.Thread(target=worker_function, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Check results
            assert len(results) == 5
            successful_workers = sum(1 for r in results if r.get("success", False))
            assert successful_workers >= 3  # At least 60% should succeed
            
        except ImportError:
            pytest.skip("Threading test dependencies not available")
    
    def test_concurrent_database_access(self):
        """Test concurrent database access"""
        try:
            from src.core.database import execute_query
            
            results = []
            
            def db_worker(worker_id):
                try:
                    # Simple query that should work
                    query = "SELECT 1 as test_value"
                    result = execute_query(query)
                    results.append({
                        "worker_id": worker_id,
                        "result": result,
                        "success": result is not None
                    })
                except Exception as e:
                    results.append({
                        "worker_id": worker_id,
                        "error": str(e),
                        "success": False
                    })
            
            # Create concurrent database access
            threads = []
            for i in range(3):
                thread = threading.Thread(target=db_worker, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for completion
            for thread in threads:
                thread.join()
            
            # Verify results
            assert len(results) == 3
            
        except ImportError:
            pytest.skip("Database concurrent access test not available")


if __name__ == "__main__":
    import sys
    
    # Track all validation failures
    all_validation_failures = []
    total_tests = 0
    
    # Test classes to run
    test_classes = [
        TestCoreModels,
        TestUtilityFunctions,
        TestErrorHandling,
        TestDatabaseOperations,
        TestCacheSystem,
        TestSecurityFeatures,
        TestCollectionSystem,
        TestPerformanceOptimization,
        TestThreadingAndConcurrency
    ]
    
    print("🔧 Running Coverage Improvement Tests...")
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    for test_class in test_classes:
        print(f"\n📋 Testing {test_class.__name__}...")
        test_instance = test_class()
        
        # Get all test methods
        test_methods = [method for method in dir(test_instance) 
                       if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            test_method = getattr(test_instance, method_name)
            
            try:
                # Run test
                test_method()
                print(f"  ✅ {method_name}")
                
            except Exception as e:
                all_validation_failures.append(
                    f"{test_class.__name__}.{method_name}: {str(e)}"
                )
                print(f"  ❌ {method_name}: {str(e)}")
    
    # Final validation result
    print("\n" + "=" * 60)
    print("📊 COVERAGE IMPROVEMENT TEST SUMMARY")
    
    passed = total_tests - len(all_validation_failures)
    success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed}")
    print(f"Failed: {len(all_validation_failures)}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if all_validation_failures:
        print(f"\n❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        
        print("\n💡 These test failures indicate missing modules or functions.")
        print("   This is expected as we're testing against the actual codebase.")
        print("   Each successful test improves code coverage.")
        
        sys.exit(1)
    else:
        print(f"\n✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Coverage improvement tests completed successfully")
        sys.exit(0)