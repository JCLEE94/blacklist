#!/usr/bin/env python3
"""
통합 에러 핸들링 시스템 - 모듈화된 구조
표준화된 에러 처리 및 로깅을 위한 중앙 집중형 모듈

이 파일은 하위 모듈에서 클래스와 함수들을 임포트하여 재정의하는 방식으로
기존 코드와의 호환성을 유지하면서 모듈화를 구현합니다.
"""

try:
    # 모듈화된 구조에서 모든 클래스와 함수 임포트
    from .error_handler import AuthenticationError
    from .error_handler import AuthorizationError
    from .error_handler import BaseError
    from .error_handler import CollectionError
    from .error_handler import DatabaseError
    from .error_handler import ErrorContext
    from .error_handler import ErrorHandler
    from .error_handler import ExternalServiceError
    from .error_handler import ResourceNotFoundError
    from .error_handler import ValidationError
    from .error_handler import error_handler
    from .error_handler import handle_api_errors
    from .error_handler import log_performance
    from .error_handler import register_error_handlers
    from .error_handler import retry_on_error
    from .error_handler import retry_on_failure
    from .error_handler import safe_execute
    from .error_handler import validate_and_convert
    from .error_handler import validate_ip_format
    from .error_handler import validate_required_fields

    # 전역 에러 핸들러에서 편의 함수들 재정의
    def handle_api_errors_legacy(func):
        """Legacy API error handler for backward compatibility"""
        return error_handler.handle_api_error(func)

    def safe_execute_legacy(
        func, default=None, error_message="작업 실행 중 오류", raise_on_error=False
    ):
        """Legacy safe execute for backward compatibility"""
        return error_handler.safe_execute(func, default, error_message, raise_on_error)

    # Export all for backward compatibility
    __all__ = [
        # Classes
        "BaseError",
        "ValidationError",
        "AuthenticationError",
        "AuthorizationError",
        "ResourceNotFoundError",
        "ExternalServiceError",
        "CollectionError",
        "DatabaseError",
        "ErrorHandler",
        "ErrorContext",
        # Functions
        "handle_api_errors",
        "safe_execute",
        "retry_on_error",
        "retry_on_failure",
        "log_performance",
        "register_error_handlers",
        "validate_required_fields",
        "validate_ip_format",
        "validate_and_convert",
        # Global instances
        "error_handler",
    ]

except ImportError:
    # 모듈화된 구조를 불러올 수 없는 경우 기본 구현 사용
    import logging
    from typing import Dict
    from typing import Optional

    logger = logging.getLogger(__name__)

    class BaseError(Exception):
        """기본 에러 클래스 - 폴백 구현"""

        def __init__(
            self,
            message: str,
            code: str = "UNKNOWN_ERROR",
            status_code: int = 500,
            details: Optional[Dict] = None,
        ):
            super().__init__(message)
            self.message = message
            self.code = code
            self.status_code = status_code
            self.details = details or {}
            logger.error(f"{self.code}: {message}")

    # 기본 예외 클래스들 정의
    ValidationError = type("ValidationError", (BaseError,), {})
    AuthenticationError = type("AuthenticationError", (BaseError,), {})

    class ErrorHandler:
        """기본 에러 핸들러 - 폴백 구현"""

        def __init__(self):
            self.error_stats = {}

        def log_error(self, error, context=None):
            logger.error(f"Error: {error}")

        def format_error_response(self, error, request_id=None):
            return {"error": {"message": str(error), "code": "ERROR"}}, 500

    # 전역 인스턴스
    error_handler = ErrorHandler()

    # 기본 함수들
    def handle_api_errors(func):
        return func

    def safe_execute(func, default=None, **kwargs):
        try:
            return func()
        except Exception as e:
            logger.error(f"Safe execute error: {e}")
            return default

    def register_error_handlers(app):
        pass
