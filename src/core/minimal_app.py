# !/usr/bin/env python3
"""
최소 기능 Flask 애플리케이션
하드웨어 제약 환경이나 비상 상황에서 사용할 최소 기능 앱

단순하고 안정적인 기능만 제공하여 테스트 안정성 확보
"""

from datetime import datetime
from typing import Any, Dict

from flask import Flask, Blueprint, jsonify, request, redirect, url_for, render_template
import logging
logger = logging.getLogger(__name__)


def create_minimal_app(config: Dict[str, Any] = None) -> Flask:
    """
    최소 기능 Flask 애플리케이션 생성

    Args:
        config: 애플리케이션 설정 딕셔너리

    Returns:
        Flask: 최소 기능 Flask 애플리케이션 인스턴스
    """
    app = Flask(__name__)

    # 기본 설정 적용
    app.config.update(
        {"SECRET_KEY": "minimal-app-secret-key", "TESTING": False, "DEBUG": False}
    )

    # 사용자 설정 적용
    if config:
        app.config.update(config)

    # 기본 라우트 등록
    register_minimal_routes(app)

    # 에러 핸들러 등록
    register_error_handlers(app)

    logger.info("Minimal Flask application created successfully")
    return app


def register_minimal_routes(app: Flask):
    """최소 기능 라우트 등록"""

    @app.route("/")
    def index():
        """루트 엔드포인트"""
        return jsonify(
            {
                "service": "blacklist-minimal",
                "version": "1.0.0",
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "message": "Minimal Blacklist Service is running",
            }
        )

    @app.route("/health")
    @app.route("/healthz")
    @app.route("/ready")
    def health_check():
        """헬스 체크 엔드포인트"""
        return jsonify(
            {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "uptime": "0d 0h 0m",
                "version": "1.0.0",
            }
        )

    @app.route("/api/health")
    def api_health():
        """상세 API 헬스 체크"""
        return jsonify(
            {
                "service": {
                    "name": "blacklist-minimal",
                    "version": "1.0.0",
                    "status": "healthy",
                },
                "system": {
                    "timestamp": datetime.now().isoformat(),
                    "memory_usage": "0MB",
                    "uptime": "0d 0h 0m",
                },
                "features": {
                    "blacklist": "disabled",
                    "collection": "disabled",
                    "statistics": "basic",
                },
            }
        )

    @app.route("/api/status")
    def service_status():
        """서비스 상태 조회"""
        return jsonify(
            {
                "success": True,
                "status": "minimal-mode",
                "timestamp": datetime.now().isoformat(),
                "statistics": {"total_ips": 0, "active_ips": 0, "sources": {}},
                "message": "Running in minimal mode - limited functionality",
            }
        )

    @app.route("/api/blacklist/active")
    def get_active_blacklist():
        """활성 블랙리스트 조회 (최소 기능)"""
        return jsonify(
            {
                "success": True,
                "ips": [],
                "count": 0,
                "timestamp": datetime.now().isoformat(),
                "message": "Minimal mode - no blacklist data available",
            }
        )

    @app.route("/api/info")
    def service_info():
        """서비스 정보"""
        return jsonify(
            {
                "name": "Blacklist Management System",
                "version": "1.0.0",
                "mode": "minimal",
                "description": "Minimal functionality for constrained environments",
                "endpoints": [
                    "/health",
                    "/api/health",
                    "/api/status",
                    "/api/blacklist/active",
                    "/api/info",
                ],
                "limitations": [
                    "No data collection",
                    "No persistent storage",
                    "Basic health checks only",
                ],
            }
        )


def register_error_handlers(app: Flask):
    """에러 핸들러 등록"""

    @app.errorhandler(404)
    def not_found_error(error):
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Not Found",
                    "message": "The requested endpoint does not exist",
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            404,
        )

    @app.errorhandler(500)
    def internal_error(error):
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred",
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )

    @app.errorhandler(Exception)
    def handle_exception(error):
        logger.error(f"Unhandled exception: {error}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Unexpected Error",
                    "message": "An unexpected error occurred",
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


class MinimalBlacklistApp:
    """
    최소 기능 블랙리스트 애플리케이션 클래스

    객체 지향 인터페이스를 선호하는 코드를 위한 래퍼 클래스
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        초기화

        Args:
            config: 애플리케이션 설정
        """
        self.app = create_minimal_app(config)
        self.config = config or {}

    def run(self, host: str = "0.0.0.0", port: int = 2542, debug: bool = False):
        """
        애플리케이션 실행

        Args:
            host: 블리드 호스트
            port: 포트 번호
            debug: 디버그 모드
        """
        logger.info(f"Starting minimal application on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

    def get_app(self) -> Flask:
        """
        Flask 애플리케이션 인스턴스 반환"""
        return self.app

    def get_status(self) -> Dict[str, Any]:
        """애플리케이션 상태 조회"""
        return {
            "status": "running",
            "mode": "minimal",
            "config": self.config,
            "timestamp": datetime.now().isoformat(),
        }


if __name__ == "__main__":
    # 검증 함수
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: 최소 앱 생성
    total_tests += 1
    try:
        app = create_minimal_app()
        if not isinstance(app, Flask):
            all_validation_failures.append("Minimal app creation: Invalid return type")
    except Exception as e:
        all_validation_failures.append(f"Minimal app creation: Exception {e}")

    # Test 2: 설정 적용
    total_tests += 1
    try:
        config = {"TESTING": True, "DEBUG": True}
        app = create_minimal_app(config)
        if not app.config.get("TESTING") or not app.config.get("DEBUG"):
            all_validation_failures.append(
                "Config application: Configuration not applied"
            )
    except Exception as e:
        all_validation_failures.append(f"Config application: Exception {e}")

    # Test 3: MinimalBlacklistApp 클래스
    total_tests += 1
    try:
        minimal_app = MinimalBlacklistApp({"TEST_MODE": True})
        status = minimal_app.get_status()
        if status["mode"] != "minimal" or "timestamp" not in status:
            all_validation_failures.append(
                "MinimalBlacklistApp: Invalid status response"
            )
    except Exception as e:
        all_validation_failures.append(f"MinimalBlacklistApp: Exception {e}")

    # Test 4: 라우트 등록 확인
    total_tests += 1
    try:
        app = create_minimal_app()
        with app.test_client() as client:
            response = client.get("/health")
            if response.status_code != 200:
                all_validation_failures.append(
                    "Route registration: Health endpoint not working"
                )
    except Exception as e:
        all_validation_failures.append(f"Route registration: Exception {e}")

    # 최종 검증 결과
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
        print("Minimal Flask application is validated and ready for use")
        sys.exit(0)
