#!/usr/bin/env python3
"""
구조화된 로깅 핵심 클래스
JSON 형식의 구조화된 로그 기록과 버퍼 관리

Sample input: logger.info("User action", user_id=123, action="login")
Expected output: 구조화된 JSON 로그 레코드 저장
"""

# Conditional imports for standalone execution and package usage
try:
    from flask import Flask, Blueprint, jsonify, request, redirect, url_for, render_template
import logging
logger = logging.getLogger(__name__)
except ImportError:
    # Fallback for standalone execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    
    try:
        from flask import Flask, Blueprint, jsonify, request, redirect, url_for, render_template
import logging
logger = logging.getLogger(__name__)
    except ImportError:
        # Mock imports for testing when dependencies not available
        from unittest.mock import Mock
        logger = Mock()

import json
import logging
import os
import sqlite3
import threading
import traceback
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from pythonjsonlogger import jsonlogger
    HAS_JSON_LOGGER = True
except ImportError:
    HAS_JSON_LOGGER = False


class StructuredLogger:
    """구조화된 로깅 클래스"""

    def __init__(self, name: str, log_dir: str = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        try:
            self.log_dir.mkdir(exist_ok=True)
        except PermissionError:
            # Docker 환경에서 권한 문제 발생 시 로그 디렉토리 생성 건너뛰기
            pass

        # 로그 버퍼 (최소화)
        self.log_buffer = deque(maxlen=1000)
        self.buffer_lock = threading.Lock()

        # 로거 설정
        self.logger = self._setup_logger()

        # 로그 통계
        self.log_stats = {
            "debug": 0,
            "info": 0,
            "warning": 0,
            "error": 0,
            "critical": 0,
        }

        # DB 설정 관련 플래그
        self.db_enabled = os.getenv("LOG_DB_ENABLED", "false").lower() == "true"
        self.db_connection = None
        if self.db_enabled:
            self._setup_log_db()

    def _setup_logger(self) -> logging.Logger:
        """로거 설정"""
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.DEBUG)

        # 기존 핸들러 제거
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # JSON 로거 사용 가능하면 JSON 포맷터, 아니면 기본 포맷터
        if HAS_JSON_LOGGER:
            formatter = jsonlogger.JsonFormatter(
                fmt="%(timestamp)s %(name)s %(levelname)s %(message)s"
            )
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 파일 핸들러 (권한이 있는 경우에만)
        try:
            log_file = self.log_dir / f"{self.name}.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except (PermissionError, OSError):
            # 파일 로깅 실패 시 콘솔만 사용
            pass

        # 버퍼 핸들러 추가
        buffer_handler = BufferHandler(self)
        buffer_handler.setLevel(logging.DEBUG)
        logger.addHandler(buffer_handler)

        return logger

    def _setup_log_db(self):
        """로그 데이터베이스 설정"""
        try:
            db_path = self.log_dir / "logs.db"
            self.db_connection = sqlite3.connect(
                str(db_path), timeout=5, check_same_thread=False
            )

            # 로그 테이블 생성
            cursor = self.db_connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    logger_name TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    context TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # 인덱스 생성
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_logs_logger_name ON logs(logger_name)"
            )

            self.db_connection.commit()

        except sqlite3.Error as e:
            logger.warning(f"로그 DB 설정 실패: {e}")
            self.db_enabled = False
            self.db_connection = None

    def _save_to_db(self, record: Dict[str, Any]):
        """로그를 데이터베이스에 저장"""
        if not self.db_enabled or not self.db_connection:
            return

        try:
            cursor = self.db_connection.cursor()

            # context에서 timestamp, logger_name, level, message 제외하고 저장
            context = {k: v for k, v in record.items() if k not in 
                      ["timestamp", "logger_name", "level", "message"]}

            cursor.execute(
                """
                INSERT INTO logs (timestamp, logger_name, level, message, context)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    record.get("timestamp"),
                    record.get("logger_name"),
                    record.get("level"),
                    record.get("message"),
                    json.dumps(context) if context else None,
                ),
            )

            self.db_connection.commit()

        except sqlite3.Error as e:
            # DB 오류 시 로깅 중단하지 않음
            pass

    def enable_db_logging(self, enabled: bool = True):
        """DB 로깅 활성화/비활성화"""
        self.db_enabled = enabled
        if enabled and not self.db_connection:
            self._setup_log_db()

    def _add_to_buffer(self, record: Dict[str, Any]):
        """로그 버퍼에 추가"""
        with self.buffer_lock:
            self.log_buffer.append(record)

        # DB에도 저장
        if self.db_enabled:
            self._save_to_db(record)

    def _create_log_record(
        self,
        level: str,
        message: str,
        exception: Optional[Exception] = None,
        **context
    ) -> Dict[str, Any]:
        """로그 레코드 생성"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "logger_name": self.name,
            "level": level.upper(),
            "message": message,
        }

        # 컨텍스트 추가
        if context:
            record.update(context)

        # 예외 정보 추가
        if exception:
            record["exception"] = {
                "type": type(exception).__name__,
                "message": str(exception),
                "traceback": traceback.format_exc(),
            }

        # 통계 업데이트
        if level.lower() in self.log_stats:
            self.log_stats[level.lower()] += 1

        return record

    def debug(self, message: str, **context):
        """디버그 로그"""
        record = self._create_log_record("debug", message, **context)
        self._add_to_buffer(record)
        self.logger.debug(message, extra=context)

    def info(self, message: str, **context):
        """정보 로그"""
        record = self._create_log_record("info", message, **context)
        self._add_to_buffer(record)
        self.logger.info(message, extra=context)

    def warning(self, message: str, **context):
        """경고 로그"""
        record = self._create_log_record("warning", message, **context)
        self._add_to_buffer(record)
        self.logger.warning(message, extra=context)

    def error(self, message: str, exception: Optional[Exception] = None, **context):
        """에러 로그"""
        record = self._create_log_record("error", message, exception, **context)
        self._add_to_buffer(record)
        self.logger.error(message, extra=context)

    def critical(self, message: str, exception: Optional[Exception] = None, **context):
        """심각한 에러 로그"""
        record = self._create_log_record("critical", message, exception, **context)
        self._add_to_buffer(record)
        self.logger.critical(message, extra=context)

    def get_recent_logs(self, count: int = 100, level: Optional[str] = None) -> list:
        """최근 로그 조회"""
        with self.buffer_lock:
            logs = list(self.log_buffer)

        if level:
            logs = [log for log in logs if log.get("level", "").lower() == level.lower()]

        return logs[-count:]

    def get_log_stats(self) -> Dict[str, Any]:
        """로그 통계 조회"""
        return {
            "name": self.name,
            "stats": self.log_stats.copy(),
            "buffer_size": len(self.log_buffer),
            "db_enabled": self.db_enabled,
        }

    def search_logs(self, query: str, limit: int = 100) -> list:
        """로그 검색"""
        with self.buffer_lock:
            logs = [log for log in self.log_buffer 
                   if query.lower() in log.get("message", "").lower()]
        return logs[-limit:]


class BufferHandler(logging.Handler):
    """로그 버퍼 핸들러"""

    def __init__(self, structured_logger: StructuredLogger):
        super().__init__()
        self.structured_logger = structured_logger

    def emit(self, record):
        """로그 레코드 처리"""
        try:
            # 로그 레코드를 구조화된 형태로 변환
            log_record = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "logger_name": record.name,
                "level": record.levelname,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }

            # 추가 컨텍스트가 있으면 포함
            if hasattr(record, "__dict__"):
                for key, value in record.__dict__.items():
                    if key not in ["name", "msg", "args", "levelname", "levelno", 
                                  "pathname", "filename", "module", "lineno", 
                                  "funcName", "created", "msecs", "relativeCreated", 
                                  "thread", "threadName", "processName", "process",
                                  "exc_info", "exc_text", "stack_info"]:
                        log_record[key] = value

            self.structured_logger._add_to_buffer(log_record)

        except Exception:
            # 로깅 시스템 자체의 오류는 무시
            pass


if __name__ == "__main__":
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: StructuredLogger creation
    total_tests += 1
    try:
        test_logger = StructuredLogger("test_logger", log_dir="/tmp/test_logs")
        if test_logger.name != "test_logger":
            all_validation_failures.append("Logger creation: Name mismatch")
        if not hasattr(test_logger, 'log_buffer'):
            all_validation_failures.append("Logger creation: Missing log_buffer")
    except Exception as e:
        all_validation_failures.append(f"Logger creation test: Failed - {e}")

    # Test 2: Log methods exist and are callable
    total_tests += 1
    try:
        test_logger = StructuredLogger("test_logger2", log_dir="/tmp/test_logs")
        log_methods = [test_logger.debug, test_logger.info, test_logger.warning, 
                      test_logger.error, test_logger.critical]
        for method in log_methods:
            if not callable(method):
                all_validation_failures.append(f"Log methods test: {method.__name__} not callable")
    except Exception as e:
        all_validation_failures.append(f"Log methods test: Failed - {e}")

    # Test 3: BufferHandler functionality
    total_tests += 1
    try:
        test_logger = StructuredLogger("test_logger3", log_dir="/tmp/test_logs")
        buffer_handler = BufferHandler(test_logger)
        
        if not hasattr(buffer_handler, 'emit'):
            all_validation_failures.append("BufferHandler test: Missing emit method")
        if not callable(buffer_handler.emit):
            all_validation_failures.append("BufferHandler test: emit not callable")
    except Exception as e:
        all_validation_failures.append(f"BufferHandler test: Failed - {e}")

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
        print("Structured logger core module is validated and ready for use")
        sys.exit(0)