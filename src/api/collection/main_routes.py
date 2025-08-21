#!/usr/bin/env python3
"""
Main Collection Routes - Combined blueprint with all collection endpoints
Provides the main collection_bp that combines all modular route blueprints
"""

from flask import Blueprint, Flask

from .collector_routes import collector_bp
from .config_routes import config_bp
# Import all modular route blueprints
from .status_routes import status_bp

# Create the main collection blueprint
collection_bp = Blueprint("collection", __name__, url_prefix="/api/collection")

# Register all sub-blueprints with the main blueprint
# Note: We need to handle URL prefix conflicts carefully


def register_collection_routes(app: Flask):
    """Register all collection routes with the Flask app"""
    app.register_blueprint(status_bp)
    app.register_blueprint(collector_bp)
    app.register_blueprint(config_bp)


# For backward compatibility, we can also provide a combined view
@collection_bp.route("/info")
def collection_info():
    """Get information about available collection endpoints"""
    from flask import jsonify

    return jsonify(
        {
            "success": True,
            "message": "Collection API - Modular endpoints available",
            "endpoints": {
                "status": {
                    "GET /api/collection/status": "Get collection system status",
                    "GET /api/collection/daily-stats": "Get daily collection statistics",
                    "GET /api/collection/history": "Get collection execution history",
                },
                "collectors": {
                    "GET /api/collection/collectors": "List all collectors",
                    "POST /api/collection/collectors/<name>/enable": "Enable collector",
                    "POST /api/collection/collectors/<name>/disable": "Disable collector",
                    "POST /api/collection/collectors/<name>/trigger": "Trigger collector",
                    "POST /api/collection/collectors/<name>/cancel": "Cancel collector",
                },
                "config": {
                    "GET /api/collection/config": "Get configuration",
                    "PUT /api/collection/config": "Update configuration",
                    "POST /api/collection/trigger-all": "Trigger all collections",
                    "POST /api/collection/cancel-all": "Cancel all collections",
                },
            },
            "version": "1.1.9",
        }
    )


if __name__ == "__main__":
    # Validation test for main routes integration
    import sys

    from flask import Flask

    app = Flask(__name__)

    # Register all collection routes
    register_collection_routes(app)
    app.register_blueprint(collection_bp)

    all_validation_failures = []
    total_tests = 0

    print("🔗 Testing Main Collection Routes Integration...")

    with app.test_client() as client:
        # Test 1: Info endpoint
        total_tests += 1
        try:
            response = client.get("/api/collection/info")
            if response.status_code != 200:
                all_validation_failures.append(
                    f"Info endpoint: Expected 200, got {response.status_code}"
                )
            else:
                print("  - Info endpoint responds correctly")
        except Exception as e:
            all_validation_failures.append(
                f"Info endpoint: Exception occurred - {str(e)}"
            )

        # Test 2: Status endpoint (from modular routes)
        total_tests += 1
        try:
            response = client.get("/api/collection/status")
            if response.status_code not in [200, 503]:
                all_validation_failures.append(
                    f"Modular status: Unexpected status code {response.status_code}"
                )
            else:
                print("  - Modular status endpoint accessible")
        except Exception as e:
            all_validation_failures.append(
                f"Modular status: Exception occurred - {str(e)}"
            )

        # Test 3: Collectors endpoint (from modular routes)
        total_tests += 1
        try:
            response = client.get("/api/collection/collectors")
            if response.status_code not in [200, 503]:
                all_validation_failures.append(
                    f"Modular collectors: Unexpected status code {response.status_code}"
                )
            else:
                print("  - Modular collectors endpoint accessible")
        except Exception as e:
            all_validation_failures.append(
                f"Modular collectors: Exception occurred - {str(e)}"
            )

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
        print("Main Collection Routes Integration is ready for use")
        sys.exit(0)
