"""
Web UI routes for Blacklist Manager - New Modular Version
Updated to use modular structure instead of a single large file
"""

import logging

from flask import Blueprint

from .api_routes import api_bp
from .collection_routes import collection_bp
from .dashboard_routes import dashboard_bp
from .data_routes import data_bp

logger = logging.getLogger(__name__)

# Main web blueprint that combines all sub-blueprints
web_bp = Blueprint("web", __name__, url_prefix="")

# Register all sub-blueprints
web_bp.register_blueprint(dashboard_bp)
web_bp.register_blueprint(api_bp)
web_bp.register_blueprint(collection_bp)
web_bp.register_blueprint(data_bp)

# Export the main blueprint
__all__ = ["web_bp"]

logger.info("Web routes initialized with modular structure")
logger.info("Registered blueprints: dashboard, api, collection, data")
