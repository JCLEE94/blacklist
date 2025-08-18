#!/usr/bin/env python3
"""
Collection API Module - Modular collection management API
"""

from .main_routes import collection_bp
from .status_routes import status_bp
from .collector_routes import collector_bp
from .config_routes import config_bp

__all__ = ['collection_bp', 'status_bp', 'collector_bp', 'config_bp']