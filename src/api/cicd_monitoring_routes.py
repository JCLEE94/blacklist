"""
Legacy CI/CD Monitoring Routes - DEPRECATED
This module has been refactored into modular components in the cicd/ package.
This file is kept for backward compatibility only.

New imports should use:
from src.api.cicd import register_cicd_blueprints, cicd_monitoring_bp

Deprecated: This file will be removed in a future version.
"""

import logging

# Import everything from the new modular cicd package
from .cicd import *

logger = logging.getLogger(__name__)

# Add deprecation warning
logger.warning(
    "src.api.cicd_monitoring_routes.py is deprecated. Use 'from src.api.cicd import ...' instead. "
    "This legacy module will be removed in a future version."
)

# All functionality now provided by the modular cicd package
# This file serves only as a compatibility layer
