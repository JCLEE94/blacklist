"""
Core Constants Test Suite

Tests for system constants including API version, cache configuration,
IP format support, HTTP status codes, and message constants.
Split from test_core_constants_and_utilities.py for 500-line rule compliance.
"""

import os
import re
import sys
import unittest
from datetime import datetime

import pytest

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
)

# Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


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


if __name__ == "__main__":
    unittest.main()
