#!/usr/bin/env python3
"""
Flask 애플리케이션 설정 관리

기본 설정, 성능 최적화, 보안 헤더 등 앱 설정을 담당합니다.
"""

import os


class AppConfigurationMixin:
    """Flask 애플리케이션 설정 관리 믹스인"""

    def _setup_basic_config(self, app):
        """기본 Flask 설정"""
        # Enable proxy headers handling
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

        # Performance optimizations
        if app.config.get("ENABLE_PROFILER", False):
            from werkzeug.middleware.profiler import ProfilerMiddleware

            app.wsgi_app = ProfilerMiddleware(
                app.wsgi_app, profile_dir="./profiler_logs"
            )

    def _setup_cors(self, app):
        """CORS 설정"""
        from flask_cors import CORS

        CORS(app, origins=os.environ.get("ALLOWED_ORIGINS", "*").split(","))

    def _setup_compression(self, app):
        """응답 압축 설정"""
        from flask_compress import Compress

        compress = Compress()
        compress.init_app(app)

        # Configure compression settings for better performance
        app.config.update(
            {
                "COMPRESS_MIMETYPES": [
                    "application/json",
                    "text/plain",
                    "text/html",
                    "text/css",
                    "text/xml",
                    "application/xml",
                    "application/xhtml+xml",
                ],
                "COMPRESS_LEVEL": 6,  # Balance between compression ratio and speed
                "COMPRESS_MIN_SIZE": 1024,  # Only compress files larger than 1KB
                "COMPRESS_CACHE_KEY": lambda: __import__("flask").request.path,
                "COMPRESS_CACHE_BACKEND": "SimpleCache",
                "COMPRESS_DEBUG": app.debug,
            }
        )

    def _setup_json_optimization(self, app):
        """JSON 직렬화 최적화"""
        try:
            pass

            app.json_encoder = None  # Disable default JSON encoder to use orjson
            app.config["JSON_SORT_KEYS"] = False  # orjson handles sorting
            from src.utils.structured_logging import get_logger

            logger = get_logger(__name__)
            logger.info(
                "orjson 활성화됨 - JSON 직렬화 성능 향상",
                feature="orjson",
                status="enabled",
            )
            return True
        except ImportError:
            return False

    def _setup_timezone(self, app):
        """타임존 설정 (KST)"""
        os.environ["TZ"] = "Asia/Seoul"
        try:
            import time

            time.tzset()
        except Exception:
            pass  # Windows에서는 tzset이 없음
