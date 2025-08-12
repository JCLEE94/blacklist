#!/usr/bin/env python3
"""
구조화된 로깅 시스템
JSON 형식의 구조화된 로그와 중앙 집중형 로깅 관리
"""

import json
import logging
import logging.handlers
import os
import sqlite3
import sys
import threading
import traceback
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Optional

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

        # 로그 DB 설정 비활성화 (성능 최적화)

    def _setup_logger(self) -> logging.Logger:
        """로거 설정"""
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.DEBUG)

        # 기존 핸들러 제거
        logger.handlers.clear()

        # JSON 포맷터
        if HAS_JSON_LOGGER:
            json_formatter = jsonlogger.JsonFormatter(
                "%(timestamp)s %(level)s %(name)s %(message)s", timestamp=True
            )
        else:
            # Fallback to standard formatter
            json_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

        # 콘솔 핸들러 (모든 환경에서 사용)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(
            logging.DEBUG if os.getenv("FLASK_ENV") == "development" else logging.INFO
        )
        console_handler.setFormatter(json_formatter)
        logger.addHandler(console_handler)

        # 파일 핸들러는 권한 문제로 인해 일시적으로 비활성화
        # Docker 환경에서 로그 폴더 권한 설정 후 활성화 필요
        try:
            # 파일 핸들러 (JSON 로그)
            json_file = self.log_dir / f"{self.name}.json"
            json_handler = logging.handlers.RotatingFileHandler(
                json_file, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
            )
            json_handler.setLevel(logging.INFO)
            json_handler.setFormatter(json_formatter)
            logger.addHandler(json_handler)

            # 에러 파일 핸들러
            error_file = self.log_dir / f"{self.name}_errors.log"
            error_handler = logging.handlers.RotatingFileHandler(
                error_file, maxBytes=5 * 1024 * 1024, backupCount=3  # 5MB
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(json_formatter)
            logger.addHandler(error_handler)
        except PermissionError:
            # 파일 권한 문제 발생시 콘솔 로깅만 사용
            logger.warning("File logging disabled due to permission issues")

        # 커스텀 버퍼 핸들러
        buffer_handler = BufferHandler(self)
        buffer_handler.setLevel(logging.DEBUG)
        logger.addHandler(buffer_handler)

        return logger

    def _setup_log_db(self):
        """로그 데이터베이스 설정"""
        try:
            db_path = self.log_dir / "logs.db"
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
        except (PermissionError, sqlite3.OperationalError):
            # Docker 환경에서 권한 문제 발생 시 DB 로깅 비활성화
            return

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS structured_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                logger_name TEXT NOT NULL,
                message TEXT NOT NULL,
                context TEXT,
                traceback TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_logs_timestamp
            ON structured_logs(timestamp)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_logs_level
            ON structured_logs(level)
        """
        )

        conn.commit()
        conn.close()

    def _save_to_db(self, record: Dict[str, Any]):
        """DB 저장 비활성화 (성능 최적화)"""
        pass

    def _add_to_buffer(self, record: Dict[str, Any]):
        """로그를 버퍼에 추가"""
        with self.buffer_lock:
            self.log_buffer.append(record)

            # 로그 통계 업데이트
            level = record.get("level", "INFO").lower()
            if level in self.log_stats:
                self.log_stats[level] += 1

    def _create_log_record(
        self,
        level: str,
        message: str,
        context: Optional[Dict] = None,
        exception: Optional[Exception] = None,
    ) -> Dict[str, Any]:
        """구조화된 로그 레코드 생성"""
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "logger_name": self.name,
            "message": message,
            "context": context or {},
        }

        # 요청 컨텍스트 추가
        try:
            from flask import g
            from flask import request

            if request:
                record["context"]["request"] = {
                    "method": request.method,
                    "path": request.path,
                    "ip": request.remote_addr,
                    "user_agent": request.headers.get("User-Agent", ""),
                }
                if hasattr(g, "request_id"):
                    record["context"]["request_id"] = g.request_id
        except:
            pass

        # 예외 정보 추가
        if exception:
            record["exception"] = {
                "type": type(exception).__name__,
                "message": str(exception),
                "traceback": traceback.format_exc(),
            }

        return record

    def debug(self, message: str, **context):
        """디버그 로그"""
        record = self._create_log_record("DEBUG", message, context)
        self._add_to_buffer(record)
        self.logger.debug(message, extra={"context": context})

    def info(self, message: str, **context):
        """정보 로그"""
        record = self._create_log_record("INFO", message, context)
        self._add_to_buffer(record)
        self._save_to_db(record)
        self.logger.info(message, extra={"context": context})

    def warning(self, message: str, **context):
        """경고 로그"""
        record = self._create_log_record("WARNING", message, context)
        self._add_to_buffer(record)
        self._save_to_db(record)
        self.logger.warning(message, extra={"context": context})

    def error(self, message: str, exception: Optional[Exception] = None, **context):
        """에러 로그"""
        record = self._create_log_record("ERROR", message, context, exception)
        self._add_to_buffer(record)
        self._save_to_db(record)

        if exception:
            self.logger.error(message, exc_info=exception, extra={"context": context})
        else:
            self.logger.error(message, extra={"context": context})

    def critical(self, message: str, exception: Optional[Exception] = None, **context):
        """치명적 에러 로그"""
        record = self._create_log_record("CRITICAL", message, context, exception)
        self._add_to_buffer(record)
        self._save_to_db(record)

        if exception:
            self.logger.critical(
                message, exc_info=exception, extra={"context": context}
            )
        else:
            self.logger.critical(message, extra={"context": context})

    def get_recent_logs(self, count: int = 100, level: Optional[str] = None) -> list:
        """최근 로그 조회"""
        with self.buffer_lock:
            logs = list(self.log_buffer)

        if level:
            logs = [
                log for log in logs if log.get("level", "").upper() == level.upper()
            ]

        return logs[-count:]

    def get_log_stats(self) -> Dict[str, Any]:
        """로그 통계 조회"""
        return {
            "stats": self.log_stats.copy(),
            "buffer_size": len(self.log_buffer),
            "recent_errors": self.get_recent_logs(10, "ERROR"),
            "recent_warnings": self.get_recent_logs(10, "WARNING"),
        }

    def search_logs(self, query: str, limit: int = 100) -> list:
        """로그 검색 비활성화 (성능 최적화)"""
        return []


class BufferHandler(logging.Handler):
    """로그 버퍼 핸들러"""

    def __init__(self, structured_logger: StructuredLogger):
        super().__init__()
        self.structured_logger = structured_logger

    def emit(self, record):
        """로그 레코드 처리"""
        try:
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "logger_name": record.name,
                "message": record.getMessage(),
                "context": getattr(record, "context", {}),
            }

            if record.exc_info:
                log_entry["traceback"] = self.format(record)

            self.structured_logger._add_to_buffer(log_entry)
        except Exception:
            self.handleError(record)


class LogManager:
    """중앙 로그 관리자"""

    _instance = None
    _loggers = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_logger(self, name: str) -> StructuredLogger:
        """로거 인스턴스 가져오기"""
        if name not in self._loggers:
            self._loggers[name] = StructuredLogger(name)
        return self._loggers[name]

    def get_all_stats(self) -> Dict[str, Any]:
        """모든 로거의 통계"""
        stats = {}
        for name, logger in self._loggers.items():
            stats[name] = logger.get_log_stats()
        return stats

    def search_all_logs(self, query: str, limit: int = 100) -> Dict[str, list]:
        """모든 로거에서 로그 검색"""
        results = {}
        for name, logger in self._loggers.items():
            logs = logger.search_logs(query, limit)
            if logs:
                results[name] = logs
        return results


# 전역 로그 매니저
log_manager = LogManager()


def get_logger(name: str) -> StructuredLogger:
    """구조화된 로거 인스턴스 가져오기"""
    return log_manager.get_logger(name)


def setup_request_logging(app):
    """Flask 요청 로깅 설정"""
    import uuid

    from flask import g
    from flask import request

    logger = get_logger("request")

    @app.before_request
    def before_request():
        # request_id가 없을 때만 설정
        if not hasattr(g, "request_id"):
            g.request_id = str(uuid.uuid4())

        # start_time이 없을 때만 설정 (real_time_monitoring에서 이미 설정할 수 있음)
        if not hasattr(g, "start_time"):
            g.start_time = datetime.utcnow()

        # 로깅을 위해 시간을 datetime으로 저장
        g.log_start_time = datetime.utcnow()

        logger.info(
            "Request started",
            request_id=g.request_id,
            method=request.method,
            path=request.path,
            ip=request.remote_addr,
        )

    @app.after_request
    def after_request(response):
        if hasattr(g, "log_start_time"):
            duration = (datetime.utcnow() - g.log_start_time).total_seconds()

            logger.info(
                "Request completed",
                request_id=getattr(g, "request_id", "unknown"),
                status_code=response.status_code,
                duration_seconds=duration,
            )

        return response

    # 로그 관리 API 엔드포인트
    @app.route("/api/logs/stats", methods=["GET"])
    def get_log_stats():
        """로그 통계 조회"""
        return json.dumps(log_manager.get_all_stats(), indent=2)

    @app.route("/api/logs/search", methods=["GET"])
    def search_logs():
        """로그 검색"""
        query = request.args.get("q", "")
        limit = min(int(request.args.get("limit", 100)), 1000)

        if not query:
            return json.dumps({"error": "검색어를 입력하세요"}), 400

        results = log_manager.search_all_logs(query, limit)
        return json.dumps(results, indent=2)
