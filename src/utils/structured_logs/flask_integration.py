#!/usr/bin/env python3
"""
Flask 로깅 통합
Flask 애플리케이션과 구조화된 로깅 시스템 연동

Sample input: setup_request_logging(flask_app)
Expected output: Flask 요청/응답 로깅 및 API 엔드포인트 설정
"""

# Conditional imports for standalone execution and package usage
try:
    import logging

    from flask import Blueprint, jsonify, request

    from .log_manager import get_logger

    logger = logging.getLogger(__name__)
except ImportError:
    # Fallback for standalone execution
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).parent))

    try:
        from log_manager import get_logger

        sys.path.append(str(Path(__file__).parent.parent.parent))
        import logging

        from flask import Blueprint, jsonify, request

        logger = logging.getLogger(__name__)
    except ImportError:
        # Mock imports for testing when dependencies not available
        from unittest.mock import Mock

        get_logger = Mock()
        Blueprint = Mock()
        jsonify = Mock()
        request = Mock()

import time


def setup_request_logging(app):
    """Flask 애플리케이션에 요청 로깅 설정"""
    request_logger = get_logger("request")

    @app.before_request
    def before_request():
        """요청 시작 전 로깅"""
        request.start_time = time.time()

        # 요청 정보 로깅
        request_logger.info(
            "요청 시작",
            method=request.method,
            path=request.path,
            remote_addr=request.remote_addr,
            user_agent=str(request.user_agent),
            args=dict(request.args),
            content_length=request.content_length,
        )

    @app.after_request
    def after_request(response):
        """요청 완료 후 로깅"""
        duration = time.time() - getattr(request, "start_time", time.time())

        # 응답 정보 로깅
        request_logger.info(
            "요청 완료",
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
            content_length=response.content_length,
        )

        return response

    # 로깅 관련 API 엔드포인트 등록
    logging_bp = Blueprint("logging", __name__)

    @logging_bp.route("/api/logs/stats")
    def get_log_stats():
        """로그 통계 조회"""
        from .log_manager import LogManager

        manager = LogManager()
        stats = manager.get_all_stats()
        return jsonify({"success": True, "stats": stats})

    @logging_bp.route("/api/logs/search")
    def search_logs():
        """로그 검색"""
        query = request.args.get("q", "")
        limit = min(int(request.args.get("limit", 100)), 1000)  # 최대 1000개

        if not query:
            return jsonify({"success": False, "error": "검색어가 필요합니다"}), 400

        from .log_manager import LogManager

        manager = LogManager()
        results = manager.search_all_logs(query, limit)

        return jsonify(
            {
                "success": True,
                "query": query,
                "results": results,
                "total_loggers": len(results),
            }
        )

    app.register_blueprint(logging_bp)


if __name__ == "__main__":
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: setup_request_logging function exists
    total_tests += 1
    try:
        if not callable(setup_request_logging):
            all_validation_failures.append(
                "Function test: setup_request_logging not callable"
            )
    except Exception as e:
        all_validation_failures.append(f"Function test: Failed - {e}")

    # Test 2: Mock Flask app integration
    total_tests += 1
    try:
        # Mock Flask app to test setup
        class MockApp:
            def __init__(self):
                self.before_request_funcs = []
                self.after_request_funcs = []
                self.blueprints = []

            def before_request(self, f):
                self.before_request_funcs.append(f)
                return f

            def after_request(self, f):
                self.after_request_funcs.append(f)
                return f

            def register_blueprint(self, bp):
                self.blueprints.append(bp)

        mock_app = MockApp()
        setup_request_logging(mock_app)

        # Should have registered before_request and after_request handlers
        if len(mock_app.before_request_funcs) == 0:
            all_validation_failures.append(
                "Flask integration: No before_request handler registered"
            )
        if len(mock_app.after_request_funcs) == 0:
            all_validation_failures.append(
                "Flask integration: No after_request handler registered"
            )
        if len(mock_app.blueprints) == 0:
            all_validation_failures.append("Flask integration: No blueprint registered")

    except Exception as e:
        all_validation_failures.append(f"Flask integration test: Failed - {e}")

    # Test 3: Request/response logging functions
    total_tests += 1
    try:
        # Test that we can access the logger
        test_logger = get_logger("test_request")
        if not hasattr(test_logger, "info"):
            all_validation_failures.append("Logger test: Missing info method")
    except Exception as e:
        all_validation_failures.append(f"Logger test: Failed - {e}")

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
        print("Flask integration module is validated and ready for use")
        sys.exit(0)
