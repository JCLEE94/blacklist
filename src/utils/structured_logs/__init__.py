#!/usr/bin/env python3
"""
구조화된 로깅 시스템
기존의 대형 structured_logging.py 파일을 기능별로 분할한 패키지

Modules:
- structured_logger: 핵심 StructuredLogger 클래스와 BufferHandler
- log_manager: LogManager 싱글톤과 전역 함수들
- flask_integration: Flask 애플리케이션 통합 기능
"""

from .flask_integration import setup_request_logging
from .log_manager import LogManager, get_logger
from .structured_logger import BufferHandler, StructuredLogger

__all__ = [
    "StructuredLogger",
    "BufferHandler",
    "LogManager",
    "get_logger",
    "setup_request_logging",
]
