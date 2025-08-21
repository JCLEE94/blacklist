#!/usr/bin/env python3
"""
Comprehensive Core Constants and Utilities Test Suite

This test file is designed to achieve comprehensive coverage of core functionality
including constants, utility functions, configuration validation, and common patterns.
Tests are focused on improving overall coverage toward 95% target.
"""

import os
import re
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.constants import (
    API_VERSION,
    DEFAULT_CACHE_TTL,
    ERROR_MESSAGES,
    HTTP_STATUS_CODES,
    IP_PATTERNS,
    SUCCESS_MESSAGES,
    SUPPORTED_IP_FORMATS,
    SYSTEM_NAME,
    TEST_CONFIG,
    get_api_endpoint,
    get_cache_key,
    get_error_message,
    get_success_message,
    get_web_route,
    is_valid_port,
    is_valid_ttl,
)


class TestConstants(unittest.TestCase):
    """Test core constants and their values"""

    def test_version_information(self):
        """Test version and system information constants"""
        self.assertIsInstance(API_VERSION, str)
        self.assertTrue(len(API_VERSION) > 0)
        self.assertIn("-", API_VERSION)

        self.assertIsInstance(SYSTEM_NAME, str)
        self.assertTrue(len(SYSTEM_NAME) > 0)

    def test_cache_configuration(self):
        """Test cache-related constants"""
        self.assertIsInstance(DEFAULT_CACHE_TTL, int)
        self.assertGreater(DEFAULT_CACHE_TTL, 0)
        self.assertLessEqual(DEFAULT_CACHE_TTL, 86400)  # Max 24 hours

    def test_ip_format_support(self):
        """Test IP format constants"""
        expected_formats = ["ipv4", "ipv6", "cidr_v4", "cidr_v6"]
        self.assertEqual(SUPPORTED_IP_FORMATS, expected_formats)

    def test_ip_patterns_validity(self):
        """Test IP pattern regular expressions"""
        self.assertIn("ipv4", IP_PATTERNS)
        self.assertIn("ipv6", IP_PATTERNS)
        self.assertIn("cidr_v4", IP_PATTERNS)
        self.assertIn("cidr_v6", IP_PATTERNS)

        # Test that patterns are compilable
        for pattern_name, pattern in IP_PATTERNS.items():
            try:
                re.compile(pattern)
            except re.error:
                self.fail(f"Invalid regex pattern for {pattern_name}: {pattern}")

    def test_http_status_codes(self):
        """Test HTTP status code constants"""
        # Check common codes exist
        required_codes = [
            "OK",
            "BAD_REQUEST",
            "UNAUTHORIZED",
            "NOT_FOUND",
            "INTERNAL_SERVER_ERROR",
        ]
        for code in required_codes:
            self.assertIn(code, HTTP_STATUS_CODES)
            self.assertIsInstance(HTTP_STATUS_CODES[code], int)
            self.assertGreaterEqual(HTTP_STATUS_CODES[code], 200)
            self.assertLessEqual(HTTP_STATUS_CODES[code], 599)

    def test_error_messages(self):
        """Test error message constants"""
        # Check key error messages exist
        required_errors = ["invalid_ip", "auth_required", "rate_limit_exceeded"]
        for error in required_errors:
            self.assertIn(error, ERROR_MESSAGES)
            self.assertIsInstance(ERROR_MESSAGES[error], str)
            self.assertTrue(len(ERROR_MESSAGES[error]) > 0)

    def test_success_messages(self):
        """Test success message constants"""
        # Check key success messages exist
        required_success = ["auth_successful", "health_check_passed"]
        for success in required_success:
            self.assertIn(success, SUCCESS_MESSAGES)
            self.assertIsInstance(SUCCESS_MESSAGES[success], str)
            self.assertTrue(len(SUCCESS_MESSAGES[success]) > 0)

    def test_test_configuration(self):
        """Test test configuration constants"""
        self.assertIn("sample_ips", TEST_CONFIG)
        self.assertIn("invalid_ips", TEST_CONFIG)
        self.assertIsInstance(TEST_CONFIG["sample_ips"], list)
        self.assertIsInstance(TEST_CONFIG["invalid_ips"], list)
        self.assertGreater(len(TEST_CONFIG["sample_ips"]), 0)
        self.assertGreater(len(TEST_CONFIG["invalid_ips"]), 0)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions from constants module"""

    def test_get_api_endpoint(self):
        """Test API endpoint getter function"""
        # Test valid endpoint
        health_endpoint = get_api_endpoint("health")
        self.assertEqual(health_endpoint, "/health")

        # Test invalid endpoint
        invalid_endpoint = get_api_endpoint("nonexistent")
        self.assertEqual(invalid_endpoint, "")

    def test_get_web_route(self):
        """Test web route getter function"""
        # Test valid route
        dashboard_route = get_web_route("dashboard")
        self.assertEqual(dashboard_route, "/")

        # Test invalid route
        invalid_route = get_web_route("nonexistent")
        self.assertEqual(invalid_route, "")

    def test_get_error_message(self):
        """Test error message getter function"""
        # Test valid error key
        error_msg = get_error_message("invalid_ip")
        self.assertIn("유효하지 않은", error_msg)

        # Test invalid error key
        default_msg = get_error_message("nonexistent")
        self.assertIn("알 수 없는", default_msg)

    def test_get_success_message(self):
        """Test success message getter function"""
        # Test valid success key
        success_msg = get_success_message("auth_successful")
        self.assertIn("성공", success_msg)

        # Test invalid success key
        default_msg = get_success_message("nonexistent")
        self.assertIn("성공적으로 완료", default_msg)

    def test_get_cache_key(self):
        """Test cache key generation function"""
        # Test basic cache key
        key = get_cache_key("prefix", "arg1", "arg2")
        self.assertEqual(key, "prefix:arg1:arg2")

        # Test with different types
        key = get_cache_key("test", 123, True, "string")
        self.assertEqual(key, "test:123:True:string")

        # Test with no additional args
        key = get_cache_key("prefix")
        self.assertEqual(key, "prefix")

    def test_is_valid_ttl(self):
        """Test TTL validation function"""
        # Test valid TTLs
        self.assertTrue(is_valid_ttl(300))
        self.assertTrue(is_valid_ttl(3600))
        self.assertTrue(is_valid_ttl(10))

        # Test invalid TTLs
        self.assertFalse(is_valid_ttl(5))  # Too low
        self.assertFalse(is_valid_ttl(86401))  # Too high
        self.assertFalse(is_valid_ttl(0))
        self.assertFalse(is_valid_ttl(-1))

    def test_is_valid_port(self):
        """Test port validation function"""
        # Test valid ports
        self.assertTrue(is_valid_port(8080))
        self.assertTrue(is_valid_port(1024))
        self.assertTrue(is_valid_port(65535))

        # Test invalid ports
        self.assertFalse(is_valid_port(80))  # Below minimum
        self.assertFalse(is_valid_port(65536))  # Above maximum
        self.assertFalse(is_valid_port(0))
        self.assertFalse(is_valid_port(-1))


class TestIPPatternValidation(unittest.TestCase):
    """Test IP pattern regex validation with actual IPs"""

    def test_ipv4_pattern(self):
        """Test IPv4 pattern with valid and invalid IPs"""
        ipv4_pattern = re.compile(IP_PATTERNS["ipv4"])

        # Valid IPv4 addresses
        valid_ipv4 = ["192.168.1.1", "10.0.0.1", "203.0.113.1", "127.0.0.1"]
        for ip in valid_ipv4:
            self.assertTrue(ipv4_pattern.match(ip), f"{ip} should be valid IPv4")

        # Invalid IPv4 addresses
        invalid_ipv4 = ["256.1.1.6", "192.168.1", "192.168.1.1.6", "not.an.ip"]
        for ip in invalid_ipv4:
            self.assertFalse(ipv4_pattern.match(ip), f"{ip} should be invalid IPv4")

    def test_cidr_v4_pattern(self):
        """Test IPv4 CIDR pattern validation"""
        cidr_pattern = re.compile(IP_PATTERNS["cidr_v4"])

        # Valid CIDR notation
        valid_cidr = ["192.168.1.0/24", "10.0.0.0/8", "172.16.0.0/12"]
        for cidr in valid_cidr:
            self.assertTrue(cidr_pattern.match(cidr), f"{cidr} should be valid CIDR")

        # Invalid CIDR notation
        invalid_cidr = ["192.168.1.0/33", "192.168.1.1", "192.168.1.0/-1"]
        for cidr in invalid_cidr:
            self.assertFalse(cidr_pattern.match(cidr), f"{cidr} should be invalid CIDR")


class TestConfigurationValidation(unittest.TestCase):
    """Test configuration validation and environment setup"""

    def test_environment_variable_validation(self):
        """Test environment variable requirements"""
        # This would test that required env vars exist in production
        # For testing, we just verify the validation rules exist
        from src.core.constants import CONFIG_VALIDATION_RULES

        self.assertIn("required_env_vars", CONFIG_VALIDATION_RULES)
        self.assertIn("optional_env_vars", CONFIG_VALIDATION_RULES)
        self.assertIsInstance(CONFIG_VALIDATION_RULES["required_env_vars"], list)
        self.assertIsInstance(CONFIG_VALIDATION_RULES["optional_env_vars"], list)

    def test_port_range_validation(self):
        """Test port range configuration"""
        from src.core.constants import CONFIG_VALIDATION_RULES

        port_config = CONFIG_VALIDATION_RULES["port_range"]
        self.assertIn("min", port_config)
        self.assertIn("max", port_config)
        self.assertEqual(port_config["min"], 1024)
        self.assertEqual(port_config["max"], 65535)

    def test_cache_ttl_range_validation(self):
        """Test cache TTL range configuration"""
        from src.core.constants import CONFIG_VALIDATION_RULES

        ttl_config = CONFIG_VALIDATION_RULES["cache_ttl_range"]
        self.assertIn("min", ttl_config)
        self.assertIn("max", ttl_config)
        self.assertGreaterEqual(ttl_config["min"], 1)
        self.assertLessEqual(ttl_config["max"], 86400)


class TestPerformanceThresholds(unittest.TestCase):
    """Test performance threshold configurations"""

    def test_response_time_thresholds(self):
        """Test response time threshold values"""
        from src.core.constants import PERFORMANCE_THRESHOLDS

        self.assertIn("response_time_ms", PERFORMANCE_THRESHOLDS)
        thresholds = PERFORMANCE_THRESHOLDS["response_time_ms"]

        self.assertIn("excellent", thresholds)
        self.assertIn("good", thresholds)
        self.assertIn("acceptable", thresholds)
        self.assertIn("poor", thresholds)

        # Check logical ordering
        self.assertLess(thresholds["excellent"], thresholds["good"])
        self.assertLess(thresholds["good"], thresholds["acceptable"])
        self.assertLess(thresholds["acceptable"], thresholds["poor"])

    def test_memory_usage_thresholds(self):
        """Test memory usage threshold values"""
        from src.core.constants import PERFORMANCE_THRESHOLDS

        memory_thresholds = PERFORMANCE_THRESHOLDS["memory_usage_percent"]

        # Check all required thresholds exist
        required_levels = ["low", "normal", "high", "critical"]
        for level in required_levels:
            self.assertIn(level, memory_thresholds)
            self.assertIsInstance(memory_thresholds[level], int)
            self.assertGreaterEqual(memory_thresholds[level], 0)
            self.assertLessEqual(memory_thresholds[level], 100)


class TestSecurityConfiguration(unittest.TestCase):
    """Test security-related constants and configuration"""

    def test_jwt_settings(self):
        """Test JWT configuration constants"""
        from src.core.constants import JWT_SETTINGS

        self.assertIn("algorithm", JWT_SETTINGS)
        self.assertIn("expiry_hours", JWT_SETTINGS)
        self.assertIn("refresh_expiry_days", JWT_SETTINGS)
        self.assertIn("issuer", JWT_SETTINGS)
        self.assertIn("audience", JWT_SETTINGS)

        # Validate values
        self.assertEqual(JWT_SETTINGS["algorithm"], "HS256")
        self.assertIsInstance(JWT_SETTINGS["expiry_hours"], int)
        self.assertGreater(JWT_SETTINGS["expiry_hours"], 0)
        self.assertIsInstance(JWT_SETTINGS["refresh_expiry_days"], int)
        self.assertGreater(JWT_SETTINGS["refresh_expiry_days"], 0)

    def test_security_headers(self):
        """Test security headers configuration"""
        from src.core.constants import SECURITY_HEADERS

        # Check essential security headers exist
        essential_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy",
        ]

        for header in essential_headers:
            self.assertIn(header, SECURITY_HEADERS)
            self.assertIsInstance(SECURITY_HEADERS[header], str)
            self.assertTrue(len(SECURITY_HEADERS[header]) > 0)

    def test_rate_limiting_configuration(self):
        """Test rate limiting constants"""
        from src.core.constants import DEFAULT_RATE_LIMITS

        # Check rate limit categories exist
        categories = ["public", "authenticated", "admin", "search", "batch"]
        for category in categories:
            self.assertIn(category, DEFAULT_RATE_LIMITS)
            self.assertIsInstance(DEFAULT_RATE_LIMITS[category], int)
            self.assertGreater(DEFAULT_RATE_LIMITS[category], 0)

        # Verify logical ordering (admin > authenticated > public)
        self.assertGreater(
            DEFAULT_RATE_LIMITS["admin"], DEFAULT_RATE_LIMITS["authenticated"]
        )
        self.assertGreater(
            DEFAULT_RATE_LIMITS["authenticated"], DEFAULT_RATE_LIMITS["public"]
        )


class TestSystemLimitsAndMonitoring(unittest.TestCase):
    """Test system limits and monitoring configuration"""

    def test_system_limits(self):
        """Test system limit constants"""
        from src.core.constants import SYSTEM_LIMITS

        required_limits = [
            "max_concurrent_requests",
            "max_memory_usage_mb",
            "max_cpu_usage_percent",
            "max_disk_usage_percent",
            "max_cache_entries",
        ]

        for limit in required_limits:
            self.assertIn(limit, SYSTEM_LIMITS)
            self.assertIsInstance(SYSTEM_LIMITS[limit], int)
            self.assertGreater(SYSTEM_LIMITS[limit], 0)

    def test_health_check_intervals(self):
        """Test health check interval configuration"""
        from src.core.constants import HEALTH_CHECK_INTERVALS

        intervals = ["critical", "normal", "background"]
        for interval in intervals:
            self.assertIn(interval, HEALTH_CHECK_INTERVALS)
            self.assertIsInstance(HEALTH_CHECK_INTERVALS[interval], int)
            self.assertGreater(HEALTH_CHECK_INTERVALS[interval], 0)

        # Critical checks should be more frequent than normal
        self.assertLess(
            HEALTH_CHECK_INTERVALS["critical"], HEALTH_CHECK_INTERVALS["normal"]
        )
        self.assertLess(
            HEALTH_CHECK_INTERVALS["normal"], HEALTH_CHECK_INTERVALS["background"]
        )


if __name__ == "__main__":
    # Run all validation tests
    all_validation_failures = []
    total_tests = 0

    # Test 1: Constants loading and basic validation
    total_tests += 1
    try:
        # Import and basic validation
        from src.core.constants import API_VERSION, DEFAULT_CACHE_TTL, IP_PATTERNS

        if not API_VERSION or not isinstance(DEFAULT_CACHE_TTL, int) or not IP_PATTERNS:
            all_validation_failures.append(
                "Constants import/validation: Basic constants failed validation"
            )
    except Exception as e:
        all_validation_failures.append(
            f"Constants import/validation: Exception during import - {e}"
        )

    # Test 2: Utility function validation
    total_tests += 1
    try:
        test_key = get_cache_key("test", "arg1", 123)
        expected_key = "test:arg1:123"
        if test_key != expected_key:
            all_validation_failures.append(
                f"Utility functions: Cache key generation failed. Expected {expected_key}, got {test_key}"
            )
    except Exception as e:
        all_validation_failures.append(
            f"Utility functions: Exception during cache key test - {e}"
        )

    # Test 3: Validation function tests
    total_tests += 1
    try:
        if (
            not is_valid_ttl(300)
            or is_valid_ttl(-1)
            or not is_valid_port(8080)
            or is_valid_port(80)
        ):
            all_validation_failures.append(
                "Validation functions: TTL or port validation failed"
            )
    except Exception as e:
        all_validation_failures.append(
            f"Validation functions: Exception during validation tests - {e}"
        )

    # Test 4: IP pattern regex compilation
    total_tests += 1
    try:
        for pattern_name, pattern in IP_PATTERNS.items():
            re.compile(pattern)  # This will raise exception if invalid
    except Exception as e:
        all_validation_failures.append(
            f"IP patterns: Regex compilation failed for {pattern_name} - {e}"
        )

    # Test 5: Configuration structure validation
    total_tests += 1
    try:
        from src.core.constants import (
            ERROR_MESSAGES,
            HTTP_STATUS_CODES,
            SUCCESS_MESSAGES,
        )

        if not HTTP_STATUS_CODES.get("OK") == 200:
            all_validation_failures.append(
                "Configuration validation: HTTP status codes invalid"
            )
        if not ERROR_MESSAGES.get("invalid_ip"):
            all_validation_failures.append(
                "Configuration validation: Error messages missing"
            )
        if not SUCCESS_MESSAGES.get("auth_successful"):
            all_validation_failures.append(
                "Configuration validation: Success messages missing"
            )
    except Exception as e:
        all_validation_failures.append(
            f"Configuration validation: Exception during structure validation - {e}"
        )

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
        print(
            "Constants and utilities module is validated and formal tests can now be written"
        )
        sys.exit(0)
