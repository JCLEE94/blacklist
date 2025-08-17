#!/usr/bin/env python3
"""
BufferHandler and LogManager tests for src/utils/structured_logging.py
Buffer handling, log management, and integration tests
"""

import logging
import tempfile
import time
import unittest
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.utils.structured_logging import BufferHandler, LogManager, StructuredLogger


class TestBufferHandler(unittest.TestCase):
    """BufferHandler 클래스 테스트"""

    def setUp(self):
        """테스트 셋업"""
        self.temp_dir = tempfile.mkdtemp()
        self.structured_logger = StructuredLogger("test_buffer", self.temp_dir)
        self.buffer_handler = BufferHandler(self.structured_logger)

    def test_initialization(self):
        """BufferHandler 초기화 테스트"""
        self.assertEqual(self.buffer_handler.structured_logger, self.structured_logger)

    def test_emit_success(self):
        """로그 레코드 처리 성공 테스트"""
        # 로그 레코드 생성
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        record.created = time.time()

        initial_buffer_size = len(self.structured_logger.log_buffer)

        self.buffer_handler.emit(record)

        # 버퍼에 추가되었는지 확인
        self.assertEqual(
            len(self.structured_logger.log_buffer), initial_buffer_size + 1
        )

    def test_emit_with_exception_info(self):
        """예외 정보 포함 로그 레코드 처리 테스트"""
        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = (ValueError, ValueError("Test exception"), None)

            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="error with exception",
                args=(),
                exc_info=exc_info,
            )
            record.created = time.time()

            self.buffer_handler.emit(record)

            # 버퍼에 추가되었는지 확인
            self.assertGreater(len(self.structured_logger.log_buffer), 0)

    def test_emit_error_handling(self):
        """로그 레코드 처리 에러 처리 테스트"""
        # 잘못된 레코드로 에러 발생시키기
        with patch(
            "datetime.datetime.fromtimestamp", side_effect=Exception("Time error")
        ):
            record = logging.LogRecord(
                name="test_logger",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="test message",
                args=(),
                exc_info=None,
            )
            record.created = time.time()

            # 에러가 발생해도 예외가 발생하지 않아야 함
            self.buffer_handler.emit(record)


class TestLogManager(unittest.TestCase):
    """LogManager 클래스 테스트"""

    def setUp(self):
        """테스트 셋업"""
        # 기존 로거들 정리
        LogManager._loggers.clear()

    def test_singleton_pattern(self):
        """싱글톤 패턴 테스트"""
        manager1 = LogManager()
        manager2 = LogManager()

        self.assertEqual(manager1, manager2)
        self.assertIs(manager1, manager2)

    def test_get_logger_new(self):
        """새 로거 생성 테스트"""
        manager = LogManager()
        logger = manager.get_logger("new_logger")

        self.assertIsInstance(logger, StructuredLogger)
        self.assertEqual(logger.name, "new_logger")

    def test_get_logger_existing(self):
        """기존 로거 반환 테스트"""
        manager = LogManager()
        logger1 = manager.get_logger("existing_logger")
        logger2 = manager.get_logger("existing_logger")

        self.assertEqual(logger1, logger2)
        self.assertIs(logger1, logger2)

    def test_get_all_stats(self):
        """모든 로거 통계 조회 테스트"""
        manager = LogManager()

        # 여러 로거 생성 및 로그 기록
        logger1 = manager.get_logger("logger1")
        logger2 = manager.get_logger("logger2")

        logger1.info("test message 1")
        logger2.error("test error")

        all_stats = manager.get_all_stats()

        self.assertIn("logger1", all_stats)
        self.assertIn("logger2", all_stats)
        self.assertEqual(all_stats["logger1"]["stats"]["info"], 1)
        self.assertEqual(all_stats["logger2"]["stats"]["error"], 1)

    def test_search_all_logs_disabled(self):
        """모든 로거 로그 검색 비활성화 테스트"""
        manager = LogManager()

        # 로거 생성 및 로그 기록
        logger1 = manager.get_logger("search_logger1")
        logger2 = manager.get_logger("search_logger2")

        logger1.info("searchable content")
        logger2.error("error with keyword")

        # 검색 기능이 비활성화되어 빈 딕셔너리 반환
        results = manager.search_all_logs("searchable")
        self.assertEqual(results, {})


class TestLoggingIntegration(unittest.TestCase):
    """로깅 통합 테스트"""

    def setUp(self):
        """테스트 셋업"""
        # 기존 로거들 정리
        LogManager._loggers.clear()

    def test_full_logging_workflow(self):
        """전체 로깅 워크플로 테스트"""
        from src.utils.structured_logging import get_logger

        # 로거 생성
        logger = get_logger("integration_test")

        # 다양한 레벨의 로그 생성
        logger.debug("Debug message", test_context="debug")
        logger.info("Info message", test_context="info")
        logger.warning("Warning message", test_context="warning")
        logger.error("Error message", test_context="error")
        logger.critical("Critical message", test_context="critical")

        # 통계 확인
        stats = logger.get_log_stats()
        self.assertEqual(stats["stats"]["debug"], 1)
        self.assertEqual(stats["stats"]["info"], 1)
        self.assertEqual(stats["stats"]["warning"], 1)
        self.assertEqual(stats["stats"]["error"], 1)
        self.assertEqual(stats["stats"]["critical"], 1)

        # 최근 로그 확인
        recent_logs = logger.get_recent_logs(count=10)
        self.assertEqual(len(recent_logs), 5)

    def test_concurrent_logging(self):
        """동시 로깅 테스트"""
        import threading

        from src.utils.structured_logging import get_logger

        logger = get_logger("concurrent_test")

        def log_worker(worker_id):
            for i in range(10):
                logger.info(f"Worker {worker_id} - Message {i}")

        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=log_worker, args=(worker_id,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 모든 로그가 기록되었는지 확인
        stats = logger.get_log_stats()
        self.assertEqual(stats["stats"]["info"], 50)

    def test_buffer_size_limits(self):
        """버퍼 크기 제한 테스트"""
        from src.utils.structured_logging import get_logger

        logger = get_logger("buffer_limit_test")

        # 많은 로그 생성
        for i in range(2000):  # 기본 제한보다 많이
            logger.info(f"Log message {i}")

        # 버퍼 크기가 제한되는지 확인
        stats = logger.get_log_stats()
        self.assertLessEqual(stats["buffer_size"], 1000)  # 기본 제한

    def test_memory_efficient_logging(self):
        """메모리 효율적 로깅 테스트"""
        import gc

        from src.utils.structured_logging import get_logger

        logger = get_logger("memory_test")

        # 메모리 사용량 측정 전
        gc.collect()
        initial_objects = len(gc.get_objects())

        # 많은 로그 생성
        for i in range(500):
            logger.info(
                f"Memory test message {i}", data={"index": i, "large_data": "x" * 100}
            )

        # 메모리 정리
        gc.collect()
        final_objects = len(gc.get_objects())

        # 메모리 증가가 어느 정도 제한되는지 확인 (정확한 수치보다는 과도한 증가 방지)
        object_increase = final_objects - initial_objects
        self.assertLess(object_increase, 1000)  # 너무 많이 증가하지 않았는지


if __name__ == "__main__":
    # 테스트 실행
    unittest.main(verbosity=2)
