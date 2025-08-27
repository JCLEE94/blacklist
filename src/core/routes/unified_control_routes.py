#!/usr/bin/env python3
"""
Unified Control Routes - Refactored modular version
Provides the main dashboard endpoints with template support
"""


try:
    pass

    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

import logging

from flask import (
    Blueprint,
    Flask,
    jsonify,
    redirect,
    render_template,
    render_template_string,
    request,
    url_for,
)

logger = logging.getLogger(__name__)

from .handlers.health_handler import HealthCheckHandler
from .handlers.status_handler import UnifiedStatusHandler

# Import template content
from .templates.dashboard_template import get_dashboard_template

bp = Blueprint("unified_control", __name__)

# Initialize handlers
status_handler = UnifiedStatusHandler()
health_handler = HealthCheckHandler()


@bp.route("/unified-control")
def unified_control_dashboard():
    """Unified control dashboard main page"""
    template = get_dashboard_template()
    return render_template_string(template)


@bp.route("/api/unified/status")
def get_unified_status():
    """Get unified system status"""
    return status_handler.get_status()


@bp.route("/api/unified/health")
def health_check():
    """Health check endpoint"""
    return health_handler.check_health()


if __name__ == "__main__":
    # Validation test for refactored routes
    import sys

    app = Flask(__name__)
    app.register_blueprint(bp)

    all_validation_failures = []
    total_tests = 0

    print("🔧 Testing Unified Control Routes (Refactored)...")

    with app.test_client() as client:
        # Test 1: Dashboard route
        total_tests += 1
        try:
            response = client.get("/unified-control")
            if response.status_code != 200:
                all_validation_failures.append(
                    f"Dashboard route: Expected 200, got {response.status_code}"
                )
        except Exception as e:
            all_validation_failures.append(
                f"Dashboard route: Exception occurred - {str(e)}"
            )

        # Test 2: Status API
        total_tests += 1
        try:
            response = client.get("/api/unified/status")
            if response.status_code != 200:
                all_validation_failures.append(
                    f"Status API: Expected 200, got {response.status_code}"
                )
        except Exception as e:
            all_validation_failures.append(f"Status API: Exception occurred - {str(e)}")

        # Test 3: Health check API
        total_tests += 1
        try:
            response = client.get("/api/unified/health")
            if response.status_code != 200:
                all_validation_failures.append(
                    f"Health API: Expected 200, got {response.status_code}"
                )
        except Exception as e:
            all_validation_failures.append(f"Health API: Exception occurred - {str(e)}")

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
        print("Unified Control Routes (Refactored) is ready for use")
        sys.exit(0)
