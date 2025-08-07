#!/usr/bin/env python3
"""
설정 관리 API 엔드포인트 - Modular Entry Point

This module imports and re-exports all modular settings routes
for backward compatibility and centralized route registration.
"""
from flask import Blueprint

# Import modular route blueprints
from .settings.auth_routes import auth_settings_bp
from .settings.api_routes import api_settings_bp
from .settings.ui_routes import ui_settings_bp

# Create main settings blueprint
settings_bp = Blueprint("settings", __name__)

# Register sub-blueprints
settings_bp.register_blueprint(auth_settings_bp)
settings_bp.register_blueprint(api_settings_bp)
settings_bp.register_blueprint(ui_settings_bp)

# Re-export individual route functions for backward compatibility
from .settings.ui_routes import settings_page, settings_management
from .settings.auth_routes import (
    update_regtech_auth,
    refresh_regtech_token,
    regtech_token_status,
    test_regtech_collection,
    update_secudium_auth
)
from .settings.api_routes import (
    get_all_settings_api,
    update_settings_bulk,
    update_individual_setting,
    save_settings,
    reset_all_settings
)


# Route functions are now imported from modular components
# All routes are automatically registered via sub-blueprints












# All API routes are now modularized and automatically registered












