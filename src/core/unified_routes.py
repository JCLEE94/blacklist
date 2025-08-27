"""
통합 API 라우트 - 새로운 모듈화된 버전
모든 블랙리스트 API를 하나로 통합한 라우트 시스템
분리된 모듈들에서 블루프린트를 가져와서 등록
"""

import logging

from flask import Blueprint

logger = logging.getLogger(__name__)

from .routes.admin_routes import admin_routes_bp
from .routes.analytics_routes import analytics_routes_bp
from .routes.api_routes import api_routes_bp
from .routes.collection_routes import collection_routes_bp
from .routes.export_routes import export_routes_bp
from .routes.health_routes import health_routes_bp
from .routes.web_routes import web_routes_bp

# Main unified blueprint that combines all sub-blueprints
unified_bp = Blueprint("unified", __name__)

# Register all sub-blueprints
unified_bp.register_blueprint(
    health_routes_bp
)  # Register health routes first at root level
unified_bp.register_blueprint(web_routes_bp)
unified_bp.register_blueprint(api_routes_bp)
unified_bp.register_blueprint(export_routes_bp)
unified_bp.register_blueprint(analytics_routes_bp)
unified_bp.register_blueprint(collection_routes_bp)
unified_bp.register_blueprint(admin_routes_bp)

# Test utilities moved to tests/utils/test_utils.py
# Import them directly from the test package when needed


# Main configuration function for backward compatibility
def configure_routes(app):
    """Configure routes on Flask app for backward compatibility"""
    app.register_blueprint(unified_bp)
    return app


# Export the main blueprint only
__all__ = [
    "unified_bp",
    "configure_routes",
]

logger.info("Unified routes initialized with modular structure")
logger.info(
    "Registered blueprints: web_routes, api_routes, export_routes, analytics_routes, collection_routes, admin_routes"
)
