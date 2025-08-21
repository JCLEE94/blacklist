"""Routes package for unified blacklist system"""

from .admin_routes import admin_routes_bp
from .api_routes import api_routes_bp
from .collection_routes import collection_routes_bp
from .web_routes import web_routes_bp
from .web_stats_routes import web_stats_routes_bp

__all__ = [
    "web_routes_bp",
    "web_stats_routes_bp",
    "api_routes_bp",
    "collection_routes_bp",
    "admin_routes_bp",
]
