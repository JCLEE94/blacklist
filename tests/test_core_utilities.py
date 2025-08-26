"""
Core Utility Functions Test Suite

Tests for utility functions including API endpoint generation, cache key generation,
message retrieval, TTL validation, and port validation.
Split from test_core_constants_and_utilities.py for 500-line rule compliance.
"""

import os
import sys
import unittest

import pytest

from src.core.constants import (
    get_api_endpoint,
    get_cache_key,
    get_error_message,
    get_success_message,
    get_web_route,
    is_valid_port,
    is_valid_ttl,
)

# Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


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


if __name__ == "__main__":
    unittest.main()
