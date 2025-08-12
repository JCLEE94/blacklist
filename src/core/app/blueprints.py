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
        """핵심 블루프린트 등록"""
        # Register unified routes blueprint directly
        from ..unified_routes import unified_bp

        app.register_blueprint(unified_bp)
        logger.info("Unified routes registered successfully")

        # Register settings routes (non-conflicting admin functions)
        try:
            from ..settings_routes import settings_bp

            app.register_blueprint(settings_bp)
            logger.info("Settings routes registered successfully")
        except Exception as e:
            logger.error(
                "Failed to register settings routes",
                exception=e,
                blueprint="settings_bp",
            )

    def _register_v2_blueprints(self, app, container):
        """V2 API 블루프린트 등록"""
        # Register V2 API routes (advanced features under /api/v2)
        try:
            from ..v2_routes import v2_bp
            from ..v2_routes_wrapper import init_v2_services

            # Initialize V2 services with dependencies from container
            blacklist_manager = container.get("blacklist_manager")
            cache_manager = container.get("cache_manager")

            if blacklist_manager and cache_manager:
                # Initialize V2 services for all route modules
                v2_service = init_v2_services(blacklist_manager, cache_manager)
                logger.info("V2 API services initialized successfully")
            else:
                logger.warning("V2 API services not initialized - missing dependencies")

            # Register the V2 blueprint
            app.register_blueprint(v2_bp)
            logger.info("V2 API routes registered successfully")
        except Exception as e:
            logger.error(
                "Failed to register V2 API routes", exception=e, blueprint="v2_bp"
            )

    def _register_debug_blueprints(self, app, container):
        """디버그 블루프린트 등록"""
        # Register debug routes for troubleshooting
        try:
            from ..debug_routes import debug_bp

            app.register_blueprint(debug_bp)
            logger.info("Debug routes registered successfully")
        except Exception as e:
            logger.error(
                "Failed to register debug routes", exception=e, blueprint="debug_bp"
            )

    def _register_security_blueprints(self, app, container):
        """보안 관련 블루프린트 등록"""
        # Register API key management routes
        try:
            from ...api.api_key_routes import api_key_bp

            app.register_blueprint(api_key_bp)
            logger.info("API key management routes registered successfully")
        except Exception as e:
            logger.error(
                "Failed to register API key routes", exception=e, blueprint="api_key_bp"
            )

        # Register authentication routes
        try:
            from ...api.auth_routes import auth_bp

            app.register_blueprint(auth_bp)
            logger.info("Authentication routes registered successfully")
        except Exception as e:
            logger.error(
                "Failed to register auth routes", exception=e, blueprint="auth_bp"
            )

        # Register collection management routes
        try:
            from ...api.collection_routes import collection_bp

            app.register_blueprint(collection_bp)
            logger.info("Collection management routes registered successfully")
        except Exception as e:
            logger.error(
                "Failed to register collection routes",
                exception=e,
                blueprint="collection_bp",
            )

        # Register system monitoring routes
        try:
            from ...api.monitoring_routes import monitoring_bp

            app.register_blueprint(monitoring_bp)
            logger.info("System monitoring routes registered successfully")
        except Exception as e:
            logger.error(
                "Failed to register monitoring routes",
                exception=e,
                blueprint="monitoring_bp",
            )
