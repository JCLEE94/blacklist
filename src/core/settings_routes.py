# !/usr/bin/env python3
"""
설정 관리 API 엔드포인트 - Modular Entry Point

This module imports and re-exports all modular settings routes
for backward compatibility and centralized route registration.
"""

import logging

from flask import Blueprint, Flask, jsonify, redirect, render_template, request, url_for

logger = logging.getLogger(__name__)
from .settings.api_routes import api_settings_bp

# Import modular route blueprints
from .settings.auth_routes import auth_settings_bp
from .settings.ui_routes import ui_settings_bp

# Create main settings blueprint
settings_bp = Blueprint("settings", __name__)

# Register sub-blueprints
settings_bp.register_blueprint(auth_settings_bp)
settings_bp.register_blueprint(api_settings_bp)
settings_bp.register_blueprint(ui_settings_bp)


# Re-export individual route functions for backward compatibility

# All routes are automatically registered via sub-blueprints


# All API routes are now modularized and automatically registered
