"""
통합 API 라우트 - 새로운 모듈화된 버전
모든 블랙리스트 API를 하나로 통합한 라우트 시스템
분리된 모듈들에서 블루프린트를 가져와서 등록
"""

import logging

from flask import Blueprint

from .routes.admin_routes import admin_routes_bp
from .routes.api_routes import api_routes_bp
from .routes.collection_routes import collection_routes_bp
from .routes.web_routes import web_routes_bp

logger = logging.getLogger(__name__)

# Main unified blueprint that combines all sub-blueprints
unified_bp = Blueprint("unified", __name__)

# Register all sub-blueprints
unified_bp.register_blueprint(web_routes_bp)
unified_bp.register_blueprint(api_routes_bp)
unified_bp.register_blueprint(collection_routes_bp)
unified_bp.register_blueprint(admin_routes_bp)

# Import test utilities for backwards compatibility
from .routes.test_utils import (
    _test_collection_data_flow,
    _test_collection_endpoints,
    _test_collection_state_consistency,
    _test_concurrent_requests,
    _test_database_api_consistency,
    _test_statistics_integration,
    run_all_tests,
)

# Main configuration function for backward compatibility
def configure_routes(app):
    """Configure routes on Flask app for backward compatibility"""
    app.register_blueprint(unified_bp)
    return app


# Export the main blueprint and test functions
__all__ = [
    "unified_bp",
    "configure_routes",
    "_test_collection_endpoints",
    "_test_collection_state_consistency",
    "_test_concurrent_requests",
    "_test_statistics_integration",
    "_test_database_api_consistency",
    "_test_collection_data_flow",
    "run_all_tests",
]

logger.info("Unified routes initialized with modular structure")
logger.info(
    f"Registered blueprints: web_routes, api_routes, collection_routes, admin_routes"
)
