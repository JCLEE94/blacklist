#!/usr/bin/env python3
"""
Web Interface Module for Deployment Dashboard

Handles Flask routes, SocketIO events, and HTML template for the deployment dashboard.
Separated from core dashboard logic for better maintainability.

Links:
- Flask documentation: https://flask.palletsprojects.com/
- Flask-SocketIO documentation: https://flask-socketio.readthedocs.io/
- Chart.js documentation: https://www.chartjs.org/

Sample input: setup_routes(dashboard_instance)
Expected output: Flask routes configured for dashboard web interface
"""

import logging
from flask import render_template_string, jsonify, request
from flask_socketio import emit

# Import HTML template from separate module
try:
    from .dashboard_template import DASHBOARD_TEMPLATE
except ImportError:
    from dashboard_template import DASHBOARD_TEMPLATE

logger = logging.getLogger(__name__)


def setup_routes(dashboard):
    """Setup Flask routes for dashboard web interface"""

    @dashboard.app.route("/")
    def dashboard_home():
        """Main dashboard page"""
        return render_template_string(DASHBOARD_TEMPLATE)

    @dashboard.app.route("/api/current-metrics")
    def get_current_metrics():
        """Get current metrics"""
        return jsonify(dashboard.current_metrics)

    @dashboard.app.route("/api/deployment-history")
    def get_deployment_history_api():
        """Get deployment history"""
        limit = request.args.get("limit", 50, type=int)
        history = dashboard.get_deployment_history(limit)
        return jsonify(history)

    @dashboard.app.route("/api/metrics-history/<metric_type>")
    def get_metrics_history_api(metric_type):
        """Get metrics history"""
        hours = request.args.get("hours", 24, type=int)
        history = dashboard.get_metrics_history(metric_type, hours)
        return jsonify(history)

    @dashboard.app.route("/api/log-event", methods=["POST"])
    def log_event():
        """Log deployment event via API"""
        data = request.get_json() or {}
        dashboard.log_deployment_event(
            event_type=data.get("event_type", "unknown"),
            version=data.get("version"),
            status=data.get("status"),
            details=data.get("details"),
            duration_seconds=data.get("duration_seconds"),
        )
        return jsonify({"status": "logged"})


def setup_socketio_events(dashboard):
    """Setup SocketIO events for real-time updates"""

    @dashboard.socketio.on("connect")
    def handle_connect():
        """Handle client connection"""
        logger.info(f"Client connected: {request.sid}")
        emit("metrics_update", dashboard.current_metrics)

    @dashboard.socketio.on("disconnect")
    def handle_disconnect():
        """Handle client disconnection"""
        logger.info(f"Client disconnected: {request.sid}")

    @dashboard.socketio.on("request_metrics")
    def handle_metrics_request():
        """Handle metrics request"""
        emit("metrics_update", dashboard.current_metrics)


if __name__ == "__main__":
    # Validation tests
    import sys
    from unittest.mock import MagicMock

    all_validation_failures = []
    total_tests = 0

    # Test 1: Template import availability
    total_tests += 1
    try:
        if len(DASHBOARD_TEMPLATE) > 1000 and "<!DOCTYPE html>" in DASHBOARD_TEMPLATE:
            pass  # Test passed
        else:
            all_validation_failures.append(
                f"Dashboard template invalid: {len(DASHBOARD_TEMPLATE)} characters"
            )
    except Exception as e:
        all_validation_failures.append(f"Dashboard template import failed: {e}")

    # Test 2: Route setup function
    total_tests += 1
    try:
        # Mock dashboard object
        dashboard = MagicMock()
        dashboard.app = MagicMock()
        dashboard.current_metrics = {"test": "data"}

        # Test setup_routes doesn't crash
        setup_routes(dashboard)

        # Verify route decorator was called
        if dashboard.app.route.called:
            pass  # Test passed
        else:
            all_validation_failures.append(
                "Route setup function did not register routes"
            )
    except Exception as e:
        all_validation_failures.append(f"Route setup failed: {e}")

    # Test 3: SocketIO events setup
    total_tests += 1
    try:
        # Mock dashboard object with socketio
        dashboard = MagicMock()
        dashboard.socketio = MagicMock()
        dashboard.current_metrics = {"test": "data"}

        # Test setup_socketio_events doesn't crash
        setup_socketio_events(dashboard)

        # Verify socketio.on was called
        if dashboard.socketio.on.called:
            pass  # Test passed
        else:
            all_validation_failures.append(
                "SocketIO events setup did not register handlers"
            )
    except Exception as e:
        all_validation_failures.append(f"SocketIO events setup failed: {e}")

    # Final validation result
    if all_validation_failures:
        print(
            f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print("Web interface module is validated and ready for use")
        sys.exit(0)
