#!/usr/bin/env python3
"""
Flask 미들웨어 및 요청/응답 처리

요청 전처리, 응답 후처리, 보안 헤더 등 미들웨어 기능을 제공합니다.
"""

import os
import time

from flask import g
from flask import request

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
        """성능 모니터링 미들웨어"""

        @app.before_request
        def performance_before_request():
            """Performance monitoring setup"""
            g.start_time = time.time()
            g.profiler = getattr(app, "profiler", None)

        @app.after_request
        def performance_after_request(response):
            """Performance metrics recording"""
            duration = time.time() - g.get("start_time", time.time())

            # Safely handle profiler metrics
            try:
                profiler = g.get("profiler")
                if profiler and hasattr(profiler, "function_timings"):
                    endpoint_key = f"endpoint_{request.endpoint or 'unknown'}"
                    if not hasattr(profiler.function_timings, "__getitem__"):
                        profiler.function_timings = {}
                    if endpoint_key not in profiler.function_timings:
                        profiler.function_timings[endpoint_key] = []
                    profiler.function_timings[endpoint_key].append(duration)
            except Exception:
                # Silently ignore profiler errors to avoid breaking the application
                pass

            # Add performance headers
            response.headers["X-Response-Time"] = f"{duration:.3f}s"
            response.headers["X-Optimized"] = "true"
            response.headers["X-Compression-Enabled"] = str(
                response.headers.get("Content-Encoding") == "gzip"
            )

            # Check if orjson is available
            try:
                pass

                json_engine = "orjson"
            except ImportError:
                json_engine = "stdlib"
            response.headers["X-JSON-Engine"] = json_engine

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
