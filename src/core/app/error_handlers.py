#!/usr/bin/env python3
"""
Flask 오류 처리기 관리

애플리케이션 전체에서 발생하는 다양한 오류들을 처리합니다.
"""


from flask import Flask, Blueprint, jsonify, request, redirect, url_for, render_template
import logging
logger = logging.getLogger(__name__)

from src.core.exceptions import BlacklistError, create_error_response, handle_exception
from src.utils.structured_logging import get_logger

logger = get_logger(__name__)


class ErrorHandlerMixin:
    """Flask 오류 처리기 믹스인"""

    def _setup_error_handlers(self, app):
        """오류 처리기 등록"""

        @app.errorhandler(BlacklistError)
        def handle_blacklist_error(error: BlacklistError):
            """Handle custom Blacklist exceptions"""
            return create_error_response(error, include_details=app.debug), 400

        @app.errorhandler(404)
        def not_found(error):
            """Handle 404 errors"""
            if request.path.startswith("/api/"):
                return {"error": "API endpoint not found", "path": request.path}, 404
            return {"error": "Not found"}, 404

        @app.errorhandler(429)
        def rate_limit_exceeded(error):
            """Handle rate limit exceeded"""
            return {
                "error": "Rate limit exceeded",
                "message": str(error.description),
                "retry_after": getattr(error, "retry_after", 3600),
            }, 429

        @app.errorhandler(500)
        def internal_error(error):
            """Handle internal server errors"""
            logger.error("Internal error", exception=error, status_code=500)

            # Convert to structured error
            if isinstance(error, Exception):
                structured_error = handle_exception(error)
                return (
                    create_error_response(structured_error, include_details=app.debug),
                    500,
                )

            return {"error": "Internal server error"}, 500
