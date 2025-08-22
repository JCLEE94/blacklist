#!/usr/bin/env python3
"""
Authentication configuration routes for UI-based credential management.
"""


from flask import Flask, Blueprint, jsonify, request, redirect, url_for, render_template
import logging

logger = logging.getLogger(__name__)

from ..auth_manager import get_auth_manager


auth_config_bp = Blueprint("auth_config", __name__)


@auth_config_bp.route("/auth-settings", methods=["GET"])
def auth_settings_page():
    """Render auth settings page"""
    try:
        return render_template("auth_settings.html")
    except Exception as e:
        logger.error(f"Failed to render auth settings: {e}")
        return jsonify({"error": str(e)}), 500


@auth_config_bp.route("/api/auth-config", methods=["GET"])
def get_auth_config():
    """Get current authentication configuration"""
    try:
        auth_manager = get_auth_manager()
        config = auth_manager.get_config()
        return jsonify({"success": True, "config": config})
    except Exception as e:
        logger.error(f"Failed to get auth config: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@auth_config_bp.route("/api/auth-config", methods=["POST"])
def update_auth_config():
    """Update authentication configuration"""
    try:
        data = request.get_json()
        auth_manager = get_auth_manager()

        if auth_manager.save_config(data):
            return jsonify(
                {"success": True, "message": "Configuration saved successfully"}
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to save configuration"}),
                500,
            )

    except Exception as e:
        logger.error(f"Failed to update auth config: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@auth_config_bp.route("/api/auth-config/test/<source>", methods=["POST"])
def test_auth_connection(source):
    """Test authentication connection for a source"""
    try:
        if source not in ["regtech", "secudium"]:
            return jsonify({"success": False, "error": "Invalid source"}), 400

        auth_manager = get_auth_manager()
        result = auth_manager.test_connection(source)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Failed to test connection: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
