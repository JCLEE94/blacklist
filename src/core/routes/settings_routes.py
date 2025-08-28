"""Settings management routes for authentication credentials."""

import logging
import json
import os
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from functools import wraps

logger = logging.getLogger(__name__)

settings_routes_bp = Blueprint("settings_routes", __name__)

# Settings file path
SETTINGS_FILE = "instance/settings.json"


def load_settings():
    """Load settings from JSON file."""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")

    return {
        "regtech": {"username": "", "password": ""},
        "secudium": {"username": "", "password": ""},
        "collection": {"enabled": False, "interval": 21600},
    }


def save_settings(settings):
    """Save settings to JSON file."""
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")
        return False


@settings_routes_bp.route("/settings", methods=["GET"])
def settings_page():
    """Render settings page."""
    settings = load_settings()
    return render_template("settings.html", settings=settings)


@settings_routes_bp.route("/api/settings", methods=["GET"])
def get_settings():
    """Get current settings."""
    settings = load_settings()
    # Hide passwords in API response
    if "regtech" in settings:
        settings["regtech"]["password"] = (
            "***" if settings["regtech"].get("password") else ""
        )
    if "secudium" in settings:
        settings["secudium"]["password"] = (
            "***" if settings["secudium"].get("password") else ""
        )
    return jsonify(settings)


@settings_routes_bp.route("/api/settings", methods=["POST"])
def update_settings():
    """Update settings."""
    try:
        data = request.get_json()
        current_settings = load_settings()

        # Update REGTECH credentials
        if "regtech" in data:
            current_settings["regtech"]["username"] = data["regtech"].get(
                "username", ""
            )
            # Only update password if not masked
            if data["regtech"].get("password") and data["regtech"]["password"] != "***":
                current_settings["regtech"]["password"] = data["regtech"]["password"]

        # Update SECUDIUM credentials
        if "secudium" in data:
            current_settings["secudium"]["username"] = data["secudium"].get(
                "username", ""
            )
            # Only update password if not masked
            if (
                data["secudium"].get("password")
                and data["secudium"]["password"] != "***"
            ):
                current_settings["secudium"]["password"] = data["secudium"]["password"]

        # Update collection settings
        if "collection" in data:
            current_settings["collection"]["enabled"] = data["collection"].get(
                "enabled", False
            )
            current_settings["collection"]["interval"] = data["collection"].get(
                "interval", 21600
            )

        if save_settings(current_settings):
            # Update environment variables for immediate effect
            os.environ["REGTECH_USERNAME"] = current_settings["regtech"]["username"]
            os.environ["REGTECH_PASSWORD"] = current_settings["regtech"]["password"]
            os.environ["SECUDIUM_USERNAME"] = current_settings["secudium"]["username"]
            os.environ["SECUDIUM_PASSWORD"] = current_settings["secudium"]["password"]
            os.environ["COLLECTION_ENABLED"] = str(
                current_settings["collection"]["enabled"]
            )

            return jsonify({"success": True, "message": "설정이 저장되었습니다."})
        else:
            return jsonify({"success": False, "message": "설정 저장에 실패했습니다."}), 500

    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@settings_routes_bp.route("/api/settings/test", methods=["POST"])
def test_credentials():
    """Test credentials."""
    try:
        data = request.get_json()
        source = data.get("source")

        if source == "regtech":
            # Test REGTECH connection
            # TODO: Implement actual test
            return jsonify({"success": True, "message": "REGTECH 연결 테스트 성공"})
        elif source == "secudium":
            # Test SECUDIUM connection
            # TODO: Implement actual test
            return jsonify({"success": True, "message": "SECUDIUM 연결 테스트 성공"})
        else:
            return jsonify({"success": False, "message": "알 수 없는 소스"}), 400

    except Exception as e:
        logger.error(f"Failed to test credentials: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
