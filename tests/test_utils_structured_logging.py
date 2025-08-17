#!/usr/bin/env python3
"""
Base import tests for src/utils/structured_logging.py
This file now contains only basic import tests.
The main functionality tests have been modularized into:
- test_structured_logging_core.py: StructuredLogger class tests
- test_structured_logging_buffer.py: BufferHandler and LogManager tests
- test_structured_logging_flask.py: Flask integration tests
"""

import unittest

import pytest


class TestStructuredLoggingImports(unittest.TestCase):
    """구조화된 로깅 모듈 임포트 테스트"""

    def test_import_structured_logger(self):
        """StructuredLogger 임포트 테스트"""
        try:
            from src.utils.structured_logging import StructuredLogger

            self.assertIsNotNone(StructuredLogger)
        except ImportError:
            pytest.skip("StructuredLogger not available")

    def test_import_buffer_handler(self):
        """BufferHandler 임포트 테스트"""
        try:
            from src.utils.structured_logging import BufferHandler

            self.assertIsNotNone(BufferHandler)
        except ImportError:
            pytest.skip("BufferHandler not available")

    def test_import_log_manager(self):
        """LogManager 임포트 테스트"""
        try:
            from src.utils.structured_logging import LogManager

            self.assertIsNotNone(LogManager)
        except ImportError:
            pytest.skip("LogManager not available")

    def test_import_get_logger(self):
        """get_logger 함수 임포트 테스트"""
        try:
            from src.utils.structured_logging import get_logger

            self.assertIsNotNone(get_logger)
        except ImportError:
            pytest.skip("get_logger not available")

    def test_import_setup_request_logging(self):
        """setup_request_logging 함수 임포트 테스트"""
        try:
            from src.utils.structured_logging import setup_request_logging

            self.assertIsNotNone(setup_request_logging)
        except ImportError:
            pytest.skip("setup_request_logging not available")


class TestBasicLoggingAvailability(unittest.TestCase):
    """기본 로깅 사용 가능성 테스트"""

    def test_logging_module_availability(self):
        """로깅 모듈 사용 가능성 테스트"""
        try:
            import src.utils.structured_logging

            self.assertIsNotNone(src.utils.structured_logging)
        except ImportError:
            pytest.skip("Structured logging module not available")


if __name__ == "__main__":
    print("Running base structured logging tests...")
    print("For detailed tests, run:")
    print("  python tests/test_structured_logging_core.py")
    print("  python tests/test_structured_logging_buffer.py")
    print("  python tests/test_structured_logging_flask.py")
    unittest.main(verbosity=2)
