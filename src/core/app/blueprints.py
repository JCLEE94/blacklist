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
