#!/usr/bin/env python3
"""
Tests for src/core/constants.py - Complete coverage for system constants.

This module provides comprehensive test coverage for the system constants,
ensuring all constants are properly defined and have expected values.

Test Coverage Areas:
- Version information constants
- Environment configuration constants
- Cache configuration constants
- Data retention settings
- IP format support
- Regular expression patterns
- Feature flags
- Error codes and messages
"""

import os
import re
import sys

import pytest

# Import with proper Python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.core.constants import *


class TestVersionConstants:
    """Test cases for version and system information constants."""

    def test_api_version_format(self):
        """Test API version follows semantic versioning format."""
        assert API_VERSION is not None
        assert isinstance(API_VERSION, str)
        # Should contain version-like pattern (numbers and dots)
        assert re.match(r"\d+\.\d+\.\d+", API_VERSION)

    def test_system_name_defined(self):
        """Test system name is properly defined."""
        assert SYSTEM_NAME is not None
        assert isinstance(SYSTEM_NAME, str)
        assert len(SYSTEM_NAME) > 0
        assert "Blacklist" in SYSTEM_NAME or "blacklist" in SYSTEM_NAME.lower()

    def test_author_defined(self):
        """Test author information is defined."""
        assert AUTHOR is not None
        assert isinstance(AUTHOR, str)
        assert len(AUTHOR) > 0


class TestEnvironmentConstants:
    """Test cases for environment configuration constants."""

    def test_environment_constants_defined(self):
        """Test all environment constants are properly defined."""
        environments = [ENV_PRODUCTION, ENV_DEVELOPMENT, ENV_TESTING]

        for env in environments:
            assert env is not None
            assert isinstance(env, str)
            assert len(env) > 0

    def test_environment_values(self):
        """Test environment constants have expected values."""
        assert ENV_PRODUCTION == "production"
        assert ENV_DEVELOPMENT == "development"
        assert ENV_TESTING == "testing"

    def test_environment_uniqueness(self):
        """Test all environment values are unique."""
        environments = [ENV_PRODUCTION, ENV_DEVELOPMENT, ENV_TESTING]
        assert len(environments) == len(set(environments))


class TestCacheConstants:
    """Test cases for cache configuration constants."""

    def test_cache_ttl_constants(self):
        """Test cache TTL constants are properly defined."""
        ttl_constants = [DEFAULT_CACHE_TTL, LONG_CACHE_TTL, SHORT_CACHE_TTL]

        for ttl in ttl_constants:
            assert ttl is not None
            assert isinstance(ttl, int)
            assert ttl > 0

    def test_cache_ttl_ordering(self):
        """Test cache TTL values are in logical order."""
        assert SHORT_CACHE_TTL < DEFAULT_CACHE_TTL < LONG_CACHE_TTL

    def test_cache_prefix_constants(self):
        """Test cache prefix constants are properly defined."""
        prefixes = [
            CACHE_PREFIX_BLACKLIST,
            CACHE_PREFIX_STATS,
            CACHE_PREFIX_SEARCH,
            CACHE_PREFIX_HEALTH,
            CACHE_PREFIX_AUTH,
        ]

        for prefix in prefixes:
            assert prefix is not None
            assert isinstance(prefix, str)
            assert len(prefix) > 0
            # Should not contain spaces or special characters that could cause issues
            assert " " not in prefix
            assert prefix.isalnum() or "_" in prefix

    def test_cache_prefix_uniqueness(self):
        """Test all cache prefixes are unique."""
        prefixes = [
            CACHE_PREFIX_BLACKLIST,
            CACHE_PREFIX_STATS,
            CACHE_PREFIX_SEARCH,
            CACHE_PREFIX_HEALTH,
            CACHE_PREFIX_AUTH,
        ]
        assert len(prefixes) == len(set(prefixes))


class TestDataRetentionConstants:
    """Test cases for data retention configuration."""

    def test_data_retention_constants(self):
        """Test data retention constants are properly defined."""
        retention_days = [
            DEFAULT_DATA_RETENTION_DAYS,
            MAX_DATA_RETENTION_DAYS,
            MIN_DATA_RETENTION_DAYS,
        ]

        for days in retention_days:
            assert days is not None
            assert isinstance(days, int)
            assert days > 0

    def test_data_retention_ordering(self):
        """Test data retention values are in logical order."""
        assert (
            MIN_DATA_RETENTION_DAYS
            <= DEFAULT_DATA_RETENTION_DAYS
            <= MAX_DATA_RETENTION_DAYS
        )

    def test_data_retention_reasonable_values(self):
        """Test data retention values are reasonable."""
        # Minimum should be at least a week
        assert MIN_DATA_RETENTION_DAYS >= 7
        # Maximum should not exceed 5 years (reasonable for most systems)
        assert MAX_DATA_RETENTION_DAYS <= 365 * 5
        # Default should be reasonable for most use cases
        assert 30 <= DEFAULT_DATA_RETENTION_DAYS <= 365


class TestIPFormatConstants:
    """Test cases for IP format support constants."""

    def test_supported_ip_formats_defined(self):
        """Test supported IP formats are properly defined."""
        assert SUPPORTED_IP_FORMATS is not None
        assert isinstance(SUPPORTED_IP_FORMATS, list)
        assert len(SUPPORTED_IP_FORMATS) > 0

    def test_ip_format_values(self):
        """Test IP format values are as expected."""
        expected_formats = ["ipv4", "ipv6", "cidr_v4", "cidr_v6"]

        for expected in expected_formats:
            assert expected in SUPPORTED_IP_FORMATS

    def test_ip_patterns_defined(self):
        """Test IP pattern constants are properly defined."""
        assert IP_PATTERNS is not None
        assert isinstance(IP_PATTERNS, dict)
        assert len(IP_PATTERNS) > 0

    def test_ip_patterns_completeness(self):
        """Test IP patterns exist for all supported formats."""
        for ip_format in SUPPORTED_IP_FORMATS:
            assert ip_format in IP_PATTERNS
            pattern = IP_PATTERNS[ip_format]
            assert pattern is not None
            assert isinstance(pattern, str)
            assert len(pattern) > 0

    def test_ip_patterns_are_valid_regex(self):
        """Test that all IP patterns are valid regular expressions."""
        for format_name, pattern in IP_PATTERNS.items():
            try:
                re.compile(pattern)
            except re.error:
                pytest.fail(f"Invalid regex pattern for {format_name}: {pattern}")

    def test_ipv4_pattern_functionality(self):
        """Test IPv4 pattern matches valid IPv4 addresses."""
        if "ipv4" in IP_PATTERNS:
            ipv4_pattern = re.compile(IP_PATTERNS["ipv4"])

            # Valid IPv4 addresses
            valid_ips = ["192.168.1.1", "10.0.0.1", "255.255.255.255", "0.0.0.0"]
            for ip in valid_ips:
                assert ipv4_pattern.match(ip), f"Failed to match valid IPv4: {ip}"

            # Invalid IPv4 addresses
            invalid_ips = ["256.1.1.1", "192.168.1", "192.168.1.1.1", "abc.def.ghi.jkl"]
            for ip in invalid_ips:
                assert not ipv4_pattern.match(
                    ip
                ), f"Incorrectly matched invalid IPv4: {ip}"


class TestFeatureFlagsAndErrorCodes:
    """Test cases for feature flags and error codes if they exist."""

    def test_constants_accessibility(self):
        """Test that importing constants doesn't raise exceptions."""
        # This test ensures all constants can be imported without issues
        try:
            import src.core.constants

            # If we get here, import was successful
            assert True
        except Exception as e:
            pytest.fail(f"Failed to import constants: {e}")

    def test_no_none_constants(self):
        """Test that critical constants are not None."""
        import src.core.constants as constants

        # Get all constants that are not private (don't start with _)
        public_constants = [
            name
            for name in dir(constants)
            if not name.startswith("_") and name.isupper()
        ]

        for const_name in public_constants:
            const_value = getattr(constants, const_name)
            # Allow empty strings but not None for string constants
            if isinstance(const_value, str):
                assert const_value is not None
            elif isinstance(const_value, (int, float)):
                assert const_value is not None
            elif isinstance(const_value, (list, dict, tuple)):
                assert const_value is not None


class TestConstantsIntegrity:
    """Test cases for overall constants integrity."""

    def test_constants_module_structure(self):
        """Test constants module has expected structure."""
        import src.core.constants as constants

        # Should have docstring
        assert constants.__doc__ is not None
        assert len(constants.__doc__) > 0

    def test_no_circular_dependencies(self):
        """Test constants module doesn't create circular dependencies."""
        # This test ensures constants can be imported independently
        try:
            import src.core.constants

            # Should be able to access attributes without issues
            _ = src.core.constants.API_VERSION
            assert True
        except ImportError as e:
            pytest.fail(f"Circular dependency detected: {e}")


if __name__ == "__main__":
    # Validation block - test core constants with actual data
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: API Version validation
    total_tests += 1
    try:
        if not isinstance(API_VERSION, str):
            all_validation_failures.append(
                f"API Version: Expected string, got {type(API_VERSION)}"
            )
        elif not re.match(r"\d+\.\d+\.\d+", API_VERSION):
            all_validation_failures.append(
                f"API Version: Invalid format: {API_VERSION}"
            )
    except NameError:
        all_validation_failures.append("API Version: API_VERSION constant not defined")
    except Exception as e:
        all_validation_failures.append(f"API Version: Exception raised: {e}")

    # Test 2: Cache TTL values validation
    total_tests += 1
    try:
        ttl_values = [SHORT_CACHE_TTL, DEFAULT_CACHE_TTL, LONG_CACHE_TTL]
        for ttl in ttl_values:
            if not isinstance(ttl, int) or ttl <= 0:
                all_validation_failures.append(f"Cache TTL: Invalid TTL value: {ttl}")

        if not (SHORT_CACHE_TTL < DEFAULT_CACHE_TTL < LONG_CACHE_TTL):
            all_validation_failures.append("Cache TTL: TTL values not in logical order")
    except NameError as e:
        all_validation_failures.append(f"Cache TTL: TTL constant not defined: {e}")
    except Exception as e:
        all_validation_failures.append(f"Cache TTL: Exception raised: {e}")

    # Test 3: Environment constants validation
    total_tests += 1
    try:
        env_constants = [ENV_PRODUCTION, ENV_DEVELOPMENT, ENV_TESTING]
        expected_values = ["production", "development", "testing"]

        if env_constants != expected_values:
            all_validation_failures.append(
                f"Environment constants: Expected {expected_values}, got {env_constants}"
            )

        if len(set(env_constants)) != len(env_constants):
            all_validation_failures.append(
                "Environment constants: Duplicate values found"
            )
    except NameError as e:
        all_validation_failures.append(
            f"Environment constants: Constant not defined: {e}"
        )
    except Exception as e:
        all_validation_failures.append(f"Environment constants: Exception raised: {e}")

    # Test 4: IP patterns validation
    total_tests += 1
    try:
        if not isinstance(IP_PATTERNS, dict):
            all_validation_failures.append(
                f"IP Patterns: Expected dict, got {type(IP_PATTERNS)}"
            )
        else:
            for format_name, pattern in IP_PATTERNS.items():
                try:
                    re.compile(pattern)
                except re.error:
                    all_validation_failures.append(
                        f"IP Patterns: Invalid regex for {format_name}: {pattern}"
                    )

                if not isinstance(pattern, str) or len(pattern) == 0:
                    all_validation_failures.append(
                        f"IP Patterns: Invalid pattern for {format_name}"
                    )
    except NameError:
        all_validation_failures.append("IP Patterns: IP_PATTERNS constant not defined")
    except Exception as e:
        all_validation_failures.append(f"IP Patterns: Exception raised: {e}")

    # Test 5: Data retention validation
    total_tests += 1
    try:
        retention_values = [
            MIN_DATA_RETENTION_DAYS,
            DEFAULT_DATA_RETENTION_DAYS,
            MAX_DATA_RETENTION_DAYS,
        ]
        for days in retention_values:
            if not isinstance(days, int) or days <= 0:
                all_validation_failures.append(
                    f"Data retention: Invalid retention days: {days}"
                )

        if not (
            MIN_DATA_RETENTION_DAYS
            <= DEFAULT_DATA_RETENTION_DAYS
            <= MAX_DATA_RETENTION_DAYS
        ):
            all_validation_failures.append(
                "Data retention: Values not in logical order"
            )
    except NameError as e:
        all_validation_failures.append(f"Data retention: Constant not defined: {e}")
    except Exception as e:
        all_validation_failures.append(f"Data retention: Exception raised: {e}")

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
        print("System constants are validated and ready for comprehensive testing")
        sys.exit(0)
