#!/usr/bin/env python3
"""
Flask 미들웨어 및 요청/응답 처리

요청 전처리, 응답 후처리, 보안 헤더 등 미들웨어 기능을 제공합니다.
"""

import logging

from flask import g, request

logger = logging.getLogger(__name__)

import os
import time

from src.core.constants import SECURITY_HEADERS
from src.utils.structured_logging import get_logger

logger = get_logger(__name__)


class MiddlewareMixin:
    """Flask 미들웨어 기능 믹스인"""

    def _setup_request_middleware(self, app, container):
        """요청/응답 미들웨어 설정"""

        @app.before_request
        def before_request():
            """Request preprocessing with container injection"""
            g.request_id = os.urandom(8).hex()
            g.start_time = time.time()

            # Inject container into Flask g for easy access
            g.container = container

            logger.info(
                "Request started",
                request_id=g.request_id,
                method=request.method,
                path=request.path,
                remote_addr=request.remote_addr,
            )

        @app.after_request
        def after_request(response):
            """Response post-processing with enhanced headers"""
            # Apply security headers from constants
            for header, value in SECURITY_HEADERS.items():
                response.headers[header] = value

            # Add request tracking
            response.headers["X-Request-ID"] = getattr(g, "request_id", "unknown")

            # Performance tracking
            if hasattr(g, "start_time"):
                response_time = (time.time() - g.start_time) * 1000
                response.headers["X-Response-Time"] = f"{response_time:.2f}ms"

            # Enhanced cache control
            if request.path.startswith("/api/blacklist"):
                response.headers["Cache-Control"] = "public, max-age=300"
            elif request.path == "/api/stats":
                response.headers["Cache-Control"] = "public, max-age=600"
            elif request.path.startswith("/api/search"):
                response.headers["Cache-Control"] = "public, max-age=180"
            else:
                response.headers["Cache-Control"] = "no-cache"

            return response

    def _setup_performance_middleware(self, app, container):
        """고급 성능 추적 및 Prometheus 메트릭 수집"""

        @app.after_request
        def enhanced_performance_tracking(response):
            """Enhanced performance tracking with Prometheus metrics"""
            if hasattr(g, "start_time"):
                duration = time.time() - g.start_time
                response.headers["X-Response-Time"] = f"{duration:.3f}s"

                # Prometheus 메트릭 기록
                try:
                    from ..monitoring.prometheus_metrics import get_metrics

                    metrics = get_metrics()

                    # HTTP 요청 메트릭 기록
                    method = request.method
                    endpoint = request.endpoint or "unknown"
                    status_code = response.status_code

                    metrics.record_http_request(method, endpoint, status_code, duration)

                    # API 쿼리 메트릭 기록 (API 엔드포인트인 경우)
                    if request.path.startswith("/api/"):
                        success = status_code < 400
                        metrics.record_api_query(request.path, success)

                    # 인증 시도 추적 (로그인 엔드포인트인 경우)
                    if request.path.startswith("/api/auth/"):
                        service = "api"
                        success = status_code == 200
                        metrics.record_authentication_attempt(service, success)

                except Exception as e:
                    # 메트릭 수집 실패는 로그만 남기고 요청 처리에는 영향주지 않음
                    logger.debug(f"Metrics collection failed: {e}")

            return response

    def _setup_build_info_context(self, app):
        """빌드 정보 컨텍스트 처리기"""

        @app.context_processor
        def inject_build_info():
            from pathlib import Path

            try:
                build_info_path = Path(".build_info")
                if build_info_path.exists():
                    with open(build_info_path, "r") as f:
                        for line in f:
                            if line.startswith("BUILD_TIME="):
                                build_time = line.split("=", 1)[1].strip("'\"")
                                return {"build_time": build_time}
                return {"build_time": "2025-06-18 18:48:33 KST"}
            except Exception:
                return {"build_time": "2025-06-18 18:48:33 KST"}
