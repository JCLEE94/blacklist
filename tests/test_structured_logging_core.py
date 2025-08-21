#!/usr/bin/env python3
"""
Core StructuredLogger tests for src/utils/structured_logging.py
StructuredLogger class functionality tests
"""

import logging
import os
import tempfile
import threading
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from flask import Flask, g

from src.utils.structured_logging import StructuredLogger, get_logger


class TestStructuredLogger(unittest.TestCase):
    """StructuredLogger 클래스 테스트"""

    def setUp(self):
        """테스트 셋업"""
        # 임시 디렉토리 사용
        self.temp_dir = tempfile.mkdtemp()
        self.logger_name = "test_logger"
        self.structured_logger = StructuredLogger(self.logger_name, self.temp_dir)

    def tearDown(self):
        """테스트 정리"""
        # 핸들러 정리
        if hasattr(self.structured_logger, "logger"):
            for handler in self.structured_logger.logger.handlers[:]:
                handler.close()
                self.structured_logger.logger.removeHandler(handler)

    def test_initialization_success(self):
        """StructuredLogger 초기화 성공 테스트"""
        logger = StructuredLogger("test_init", self.temp_dir)

        # 기본 속성 확인
        self.assertEqual(logger.name, "test_init")
        self.assertEqual(str(logger.log_dir), self.temp_dir)
        self.assertIsNotNone(logger.logger)
        self.assertIsNotNone(logger.log_buffer)
        self.assertIsNotNone(logger.buffer_lock)
        self.assertIsNotNone(logger.log_stats)

        # 로그 통계 초기화 확인
        expected_stats = ["debug", "info", "warning", "error", "critical"]
        for stat in expected_stats:
            self.assertIn(stat, logger.log_stats)
            self.assertEqual(logger.log_stats[stat], 0)

    def test_initialization_permission_error(self):
        """StructuredLogger 초기화 권한 에러 처리 테스트"""
        with patch(
            "pathlib.Path.mkdir", side_effect=PermissionError("Permission denied")
        ):
            # 권한 에러가 발생해도 정상적으로 초기화되어야 함
            logger = StructuredLogger("test_permission", "/restricted/path")
            self.assertEqual(logger.name, "test_permission")

    def test_setup_logger_basic(self):
        """로거 설정 기본 테스트"""
        logger = self.structured_logger._setup_logger()

        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.level, logging.DEBUG)
        self.assertGreater(len(logger.handlers), 0)

    def test_setup_logger_with_json_logger(self):
        """JSON 로거가 있는 경우 테스트"""
        with patch("src.utils.structured_logging.HAS_JSON_LOGGER", True):
            with patch("src.utils.structured_logging.jsonlogger") as mock_jsonlogger:
                mock_formatter = MagicMock()
                mock_jsonlogger.JsonFormatter.return_value = mock_formatter

                logger = StructuredLogger("test_json", self.temp_dir)

                # JsonFormatter가 호출되었는지 확인
                mock_jsonlogger.JsonFormatter.assert_called_once()

    def test_setup_logger_without_json_logger(self):
        """JSON 로거가 없는 경우 테스트"""
        with patch("src.utils.structured_logging.HAS_JSON_LOGGER", False):
            logger = StructuredLogger("test_no_json", self.temp_dir)
            self.assertIsNotNone(logger.logger)

    def test_setup_logger_file_handler_permission_error(self):
        """파일 핸들러 권한 에러 처리 테스트"""
        with patch(
            "logging.handlers.RotatingFileHandler",
            side_effect=PermissionError("File permission denied"),
        ):
            logger = StructuredLogger("test_file_error", self.temp_dir)
            # 에러가 발생해도 로거는 정상적으로 설정되어야 함
            self.assertIsNotNone(logger.logger)

    def test_enable_db_logging(self):
        """DB 로깅 활성화/비활성화 테스트"""
        # 활성화
        self.structured_logger.enable_db_logging(True)
        self.assertTrue(self.structured_logger.db_enabled)

        # 비활성화
        self.structured_logger.enable_db_logging(False)
        self.assertFalse(self.structured_logger.db_enabled)

    def test_save_to_db_disabled(self):
        """DB 저장 비활성화 상태 테스트"""
        # DB 저장이 비활성화된 상태에서는 아무것도 하지 않아야 함
        record = {"level": "INFO", "message": "test"}
        self.structured_logger._save_to_db(record)  # 에러가 발생하지 않아야 함

    def test_save_to_db_enabled_success(self):
        """DB 저장 활성화 성공 테스트"""
        # 임시 DB 파일 생성
        temp_db = os.path.join(self.temp_dir, "test.db")

        with patch(
            "src.utils.structured_logging.StructuredLogger._save_to_db"
        ) as mock_save:
            self.structured_logger.enable_db_logging(True)
            record = {
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "name": "test",
                "message": "test message",
                "context": {"key": "value"},
            }

            self.structured_logger._save_to_db(record)
            mock_save.assert_called_once_with(record)

    def test_save_to_db_error_handling(self):
        """DB 저장 에러 처리 테스트"""
        self.structured_logger.enable_db_logging(True)

        with patch("sqlite3.connect", side_effect=Exception("DB connection error")):
            record = {"level": "INFO", "message": "test"}
            # 에러가 발생해도 예외가 발생하지 않아야 함
            self.structured_logger._save_to_db(record)

    def test_add_to_buffer(self):
        """로그 버퍼 추가 테스트"""
        initial_buffer_size = len(self.structured_logger.log_buffer)
        initial_info_count = self.structured_logger.log_stats["info"]

        record = {"level": "INFO", "message": "test message"}
        self.structured_logger._add_to_buffer(record)

        # 버퍼 크기 증가 확인
        self.assertEqual(
            len(self.structured_logger.log_buffer), initial_buffer_size + 1
        )

        # 통계 업데이트 확인
        self.assertEqual(
            self.structured_logger.log_stats["info"], initial_info_count + 1
        )

    def test_add_to_buffer_thread_safety(self):
        """로그 버퍼 추가 스레드 안전성 테스트"""

        def add_records():
            for i in range(10):
                record = {"level": "INFO", "message": f"message_{i}"}
                self.structured_logger._add_to_buffer(record)

        threads = []
        for _ in range(5):
            thread = threading.Thread(target=add_records)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 모든 레코드가 추가되었는지 확인
        self.assertEqual(self.structured_logger.log_stats["info"], 50)

    def test_create_log_record_basic(self):
        """로그 레코드 생성 기본 테스트"""
        record = self.structured_logger._create_log_record(
            "INFO", "test message", {"key": "value"}
        )

        self.assertEqual(record["level"], "INFO")
        self.assertEqual(record["message"], "test message")
        self.assertEqual(record["context"]["key"], "value")
        self.assertEqual(record["logger_name"], self.logger_name)
        self.assertIn("timestamp", record)

    def test_create_log_record_with_exception(self):
        """예외 정보 포함 로그 레코드 생성 테스트"""
        test_exception = ValueError("Test error")
        record = self.structured_logger._create_log_record(
            "ERROR", "error occurred", exception=test_exception
        )

        self.assertIn("exception", record)
        self.assertEqual(record["exception"]["type"], "ValueError")
        self.assertEqual(record["exception"]["message"], "Test error")
        self.assertIn("traceback", record["exception"])

    def test_create_log_record_with_flask_context(self):
        """Flask 컨텍스트 포함 로그 레코드 생성 테스트"""
        app = Flask(__name__)

        with app.test_request_context(
            "/test", method="POST", headers={"User-Agent": "test-agent"}
        ):
            with app.app_context():
                g.request_id = "test-request-123"

                record = self.structured_logger._create_log_record(
                    "INFO", "test with context"
                )

                self.assertIn("request", record["context"])
                request_context = record["context"]["request"]
                self.assertEqual(request_context["method"], "POST")
                self.assertEqual(request_context["path"], "/test")
                self.assertEqual(request_context["user_agent"], "test-agent")
                self.assertEqual(record["context"]["request_id"], "test-request-123")

    def test_create_log_record_flask_context_error(self):
        """Flask 컨텍스트 에러 처리 테스트"""
        # Flask 컨텍스트 없이 실행 - 에러가 발생하지 않아야 함
        record = self.structured_logger._create_log_record("INFO", "no flask context")
        self.assertEqual(record["level"], "INFO")
        self.assertEqual(record["message"], "no flask context")

    def test_logging_methods(self):
        """각 로깅 메소드 테스트"""
        test_message = "test message"
        context = {"test_key": "test_value"}

        # Debug 로그
        self.structured_logger.debug(test_message, **context)
        self.assertEqual(self.structured_logger.log_stats["debug"], 1)

        # Info 로그
        self.structured_logger.info(test_message, **context)
        self.assertEqual(self.structured_logger.log_stats["info"], 1)

        # Warning 로그
        self.structured_logger.warning(test_message, **context)
        self.assertEqual(self.structured_logger.log_stats["warning"], 1)

        # Error 로그
        self.structured_logger.error(test_message, **context)
        self.assertEqual(self.structured_logger.log_stats["error"], 1)

        # Critical 로그
        self.structured_logger.critical(test_message, **context)
        self.assertEqual(self.structured_logger.log_stats["critical"], 1)

    def test_logging_with_exception(self):
        """예외 포함 로깅 테스트"""
        test_exception = RuntimeError("Test runtime error")

        self.structured_logger.error("Error with exception", exception=test_exception)
        self.assertEqual(self.structured_logger.log_stats["error"], 1)

        self.structured_logger.critical(
            "Critical with exception", exception=test_exception
        )
        self.assertEqual(self.structured_logger.log_stats["critical"], 1)

    def test_get_recent_logs_all(self):
        """최근 로그 조회 - 모든 레벨"""
        # 여러 로그 생성
        self.structured_logger.info("info message 1")
        self.structured_logger.warning("warning message")
        self.structured_logger.error("error message")
        self.structured_logger.info("info message 2")

        recent_logs = self.structured_logger.get_recent_logs(count=10)
        self.assertEqual(len(recent_logs), 4)

    def test_get_recent_logs_filtered(self):
        """최근 로그 조회 - 레벨 필터링"""
        # 여러 로그 생성
        self.structured_logger.info("info message 1")
        self.structured_logger.warning("warning message")
        self.structured_logger.error("error message")
        self.structured_logger.info("info message 2")

        # INFO 레벨만 조회
        info_logs = self.structured_logger.get_recent_logs(count=10, level="INFO")
        self.assertEqual(len(info_logs), 2)

        # ERROR 레벨만 조회
        error_logs = self.structured_logger.get_recent_logs(count=10, level="ERROR")
        self.assertEqual(len(error_logs), 1)

    def test_get_recent_logs_count_limit(self):
        """최근 로그 조회 - 개수 제한"""
        # 많은 로그 생성
        for i in range(20):
            self.structured_logger.info(f"message {i}")

        # 최근 5개만 조회
        recent_logs = self.structured_logger.get_recent_logs(count=5)
        self.assertEqual(len(recent_logs), 5)

        # 마지막 메시지가 가장 최근 것인지 확인
        self.assertIn("message 19", recent_logs[-1]["message"])

    def test_get_log_stats(self):
        """로그 통계 조회 테스트"""
        # 여러 로그 생성
        self.structured_logger.info("info message")
        self.structured_logger.warning("warning message")
        self.structured_logger.error("error message")
        self.structured_logger.error("error message 2")

        stats = self.structured_logger.get_log_stats()

        self.assertIn("stats", stats)
        self.assertIn("buffer_size", stats)
        self.assertIn("recent_errors", stats)
        self.assertIn("recent_warnings", stats)

        self.assertEqual(stats["stats"]["info"], 1)
        self.assertEqual(stats["stats"]["warning"], 1)
        self.assertEqual(stats["stats"]["error"], 2)
        self.assertEqual(stats["buffer_size"], 4)

    def test_search_logs_disabled(self):
        """로그 검색 비활성화 테스트"""
        # 일부 로그 생성
        self.structured_logger.info("searchable message")
        self.structured_logger.error("error with keyword")

        # 검색 기능이 비활성화되어 빈 리스트 반환
        results = self.structured_logger.search_logs("searchable")
        self.assertEqual(results, [])


if __name__ == "__main__":
    # 테스트 실행
    unittest.main(verbosity=2)
