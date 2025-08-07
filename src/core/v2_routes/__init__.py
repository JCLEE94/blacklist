"""Modular V2 API Routes package"""

from .service import V2APIService
from .blacklist_routes import blacklist_v2_bp
from .analytics_routes import analytics_v2_bp
from .export_routes import export_v2_bp
from .health_routes import health_v2_bp

# Main blueprint that combines all sub-blueprints
from flask import Blueprint

v2_bp = Blueprint("v2_api", __name__, url_prefix="/api/v2")

# Register sub-blueprints
v2_bp.register_blueprint(blacklist_v2_bp)
v2_bp.register_blueprint(analytics_v2_bp)
v2_bp.register_blueprint(export_v2_bp)
v2_bp.register_blueprint(health_v2_bp)

__all__ = [
    'v2_bp',
    'V2APIService',
    'blacklist_v2_bp',
    'analytics_v2_bp',
    'export_v2_bp',
    'health_v2_bp',
]
