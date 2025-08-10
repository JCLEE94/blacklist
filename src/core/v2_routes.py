#!/usr/bin/env python3
"""
Backward compatibility wrapper for modularized V2 Routes

This file maintains backward compatibility while the actual implementation
has been modularized into the v2_routes/ package.
"""

# Import everything from the modular package
from src.core.v2_routes import V2APIService
from src.core.v2_routes import analytics_v2_bp
from src.core.v2_routes import blacklist_v2_bp
from src.core.v2_routes import export_v2_bp
from src.core.v2_routes import health_v2_bp
from src.core.v2_routes import v2_bp


# Initialize service instances for sub-blueprints
def init_v2_services(blacklist_manager, cache_manager):
    """Initialize V2 API services for all route modules"""
    service = V2APIService(blacklist_manager, cache_manager)

    # Initialize services for each route module
    from src.core.v2_routes.analytics_routes import \
        init_service as init_analytics_service
    from src.core.v2_routes.blacklist_routes import \
        init_service as init_blacklist_service
    from src.core.v2_routes.export_routes import \
        init_service as init_export_service
    from src.core.v2_routes.health_routes import \
        init_service as init_health_service

    init_blacklist_service(service)
    init_analytics_service(service)
    init_export_service(service)
    init_health_service(service)

    return service


# Re-export for backward compatibility
__all__ = [
    "v2_bp",
    "V2APIService",
    "init_v2_services",
    "blacklist_v2_bp",
    "analytics_v2_bp",
    "export_v2_bp",
    "health_v2_bp",
]

# Preserve the original class name and functionality
# All imports and usage patterns remain the same
