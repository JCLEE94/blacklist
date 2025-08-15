#!/usr/bin/env python3
"""
통합 에러 핸들링 시스템 - 모듈화된 구조
표준화된 에러 처리 및 로깅을 위한 중앙 집중형 모듈

이 파일은 하위 모듈에서 클래스와 함수들을 임포트하여 재정의하는 방식으로
기존 코드와의 호환성을 유지하면서 모듈화를 구현합니다.
"""

try:
    # 모듈화된 구조에서 모든 클래스와 함수 임포트
    from .error_handler import (AuthenticationError, AuthorizationError,
                                BaseError, CollectionError, DatabaseError,
                                ErrorContext, ErrorHandler,
                                ExternalServiceError, ResourceNotFoundError,
                                ValidationError, error_handler,
                                handle_api_errors, log_performance,
                                register_error_handlers, retry_on_error,
                                retry_on_failure, safe_execute,
                                validate_and_convert, validate_ip_format,
                                validate_required_fields)

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
    from typing import Dict, Optional

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
        """Flask 애플리케이션에 에러 핸들러 등록"""
        import logging

        from flask import jsonify, request

        logger = logging.getLogger(__name__)

        @app.errorhandler(400)
        def bad_request(error):
            logger.warning(f"Bad Request: {request.url} - {error}")
            return (
                jsonify(
                    {
                        "error": "Bad Request",
                        "message": (
                            str(error.description)
                            if hasattr(error, "description")
                            else "Invalid request"
                        ),
                        "status_code": 400,
                    }
                ),
                400,
            )

        @app.errorhandler(401)
        def unauthorized(error):
            logger.warning(f"Unauthorized access: {request.url}")
            return (
                jsonify(
                    {
                        "error": "Unauthorized",
                        "message": "Authentication required",
                        "status_code": 401,
                    }
                ),
                401,
            )

        @app.errorhandler(403)
        def forbidden(error):
            logger.warning(f"Forbidden access: {request.url}")
            return (
                jsonify(
                    {
                        "error": "Forbidden",
                        "message": "Access denied",
                        "status_code": 403,
                    }
                ),
                403,
            )

        @app.errorhandler(404)
        def not_found(error):
            logger.info(f"Not Found: {request.url}")
            return (
                jsonify(
                    {
                        "error": "Not Found",
                        "message": "Resource not found",
                        "status_code": 404,
                    }
                ),
                404,
            )

        @app.errorhandler(500)
        def internal_error(error):
            logger.error(f"Internal Server Error: {request.url} - {error}")
            return (
                jsonify(
                    {
                        "error": "Internal Server Error",
                        "message": "An unexpected error occurred",
                        "status_code": 500,
                    }
                ),
                500,
            )

        @app.errorhandler(Exception)
        def handle_exception(error):
            logger.error(f"Unhandled Exception: {request.url} - {error}", exc_info=True)
            return (
                jsonify(
                    {
                        "error": "Internal Server Error",
                        "message": "An unexpected error occurred",
                        "status_code": 500,
                    }
                ),
                500,
            )

        logger.info("Error handlers registered successfully")
