#!/usr/bin/env python3
"""
Flask 블루프린트 등록 관리

다양한 블루프린트를 등록하고 오류 처리를 담당합니다.
"""

from src.utils.structured_logging import get_logger

logger = get_logger(__name__)


class BlueprintRegistrationMixin:
    """Flask 블루프린트 등록 관리 믹스인"""

    def _register_core_blueprints(self, app, container):
        """핵심 블루프린트 등록 - 불필요한 중복 제거"""
        # Register root route blueprint
        from ..root_route import root_bp

        app.register_blueprint(root_bp)
        logger.info("Root routes registered successfully")

        # Register unified routes blueprint (핵심 API)
        from ..unified_routes import unified_bp

        app.register_blueprint(unified_bp)
        logger.info("Unified routes registered successfully")

        # Register simple collection management panel (통합 수집 관리 패널)
        try:
            from ..routes.simple_collection_panel import simple_collection_bp

            app.register_blueprint(simple_collection_bp)
            logger.info("🔄 Simple collection management panel registered successfully")
        except Exception as e:
            logger.error(f"Failed to register simple collection management: {e}")

    def _register_v2_blueprints(self, app, container):
        """V2 API 블루프린트 등록 - 필수 기능만 유지"""
        try:
            from ..v2_routes import v2_bp
            from ..v2_routes_wrapper import init_v2_services

            # Initialize V2 services with dependencies from container
            blacklist_manager = container.get("blacklist_manager")
            cache_manager = container.get("cache_manager")

            if blacklist_manager and cache_manager:
                init_v2_services(blacklist_manager, cache_manager)
                logger.info("V2 API services initialized successfully")
            else:
                logger.warning("V2 API services not initialized - missing dependencies")

            app.register_blueprint(v2_bp)
            logger.info("V2 API routes registered successfully")
        except Exception as e:
            logger.error(f"Failed to register V2 API routes: {e}")

    def _register_debug_blueprints(self, app, container):
        """디버그 블루프린트 등록 - 개발 환경에서만 활성화"""
        import os

        if os.getenv("FLASK_ENV") == "development":
            try:
                from ..debug_routes import debug_bp

                app.register_blueprint(debug_bp)
                logger.info("Debug routes registered (development mode)")
            except Exception as e:
                logger.error(f"Failed to register debug routes: {e}")
        else:
            logger.info("Debug routes disabled in production")

    def _register_security_blueprints(self, app, container):
        """보안 관련 블루프린트 등록 - 핵심 기능만 유지"""
        # Register authentication routes (필수)
        try:
            from ...api.auth_routes import auth_bp

            app.register_blueprint(auth_bp)
            logger.info("Authentication routes registered successfully")
        except Exception as e:
            logger.error(f"Failed to register auth routes: {e}")

        # Register collection management routes (핵심 API)
        try:
            from ...api.collection_routes import collection_bp

            app.register_blueprint(collection_bp)
            logger.info("Collection management routes registered successfully")
        except Exception as e:
            logger.error(f"Failed to register collection routes: {e}")
