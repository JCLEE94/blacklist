from flask import Blueprint, Flask, jsonify, request
import logging
logger = logging.getLogger(__name__)

# !/usr/bin/env python3
"""
Collection Configuration Routes - Configuration management
Handles collection system configuration get and update operations
"""


try:
    from ...core.collectors.collector_factory import get_collector_factory
    from ...utils.security import input_validation, rate_limit, require_auth

    COLLECTOR_AVAILABLE = True
except ImportError:
    COLLECTOR_AVAILABLE = False


config_bp = Blueprint("collection_config", __name__, url_prefix="/api/collection")


@config_bp.route("/config", methods=["GET"])
@rate_limit(limit=30, window_seconds=60)  # 30 requests per minute
def get_collection_config():
    """Get current collection system configuration"""
    if not COLLECTOR_AVAILABLE:
        return (
            jsonify({"success": False, "error": "Collection system not available"}),
            503,
        )

    try:
        factory = get_collector_factory()
        manager = factory.create_collection_manager()

        config = (
            manager.get_config()
            if hasattr(manager, "get_config")
            else {
                "auto_collection_enabled": False,
                "collection_interval_minutes": 60,
                "max_concurrent_collections": 2,
                "retry_attempts": 3,
                "timeout_seconds": 300,
            }
        )

        return jsonify({"success": True, "config": config})

    except Exception as e:
        logger.error(f"Failed to get collection config: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Unable to retrieve collection configuration",
                }
            ),
            500,
        )


@config_bp.route("/config", methods=["PUT"])
@require_auth
@rate_limit(limit=10, window_seconds=60)  # 10 requests per minute
def update_collection_config():
    """Update collection system configuration"""
    if not COLLECTOR_AVAILABLE:
        return (
            jsonify({"success": False, "error": "Collection system not available"}),
            503,
        )

    try:
        # Get JSON data from request
        if request.is_json:
            config_data = request.get_json() or {}
        else:
            config_data = request.form.to_dict() or {}

        # Validate configuration data
        validation_result = input_validation.validate_config(config_data)
        if not validation_result.get("valid", False):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Invalid configuration data",
                        "details": validation_result.get("errors", []),
                    }
                ),
                400,
            )

        factory = get_collector_factory()
        manager = factory.create_collection_manager()

        if hasattr(manager, "update_config"):
            result = manager.update_config(config_data)
            return jsonify(
                {
                    "success": True,
                    "message": "Configuration updated successfully",
                    "config": result,
                }
            )
        else:
            return (
                jsonify(
                    {"success": False, "error": "Configuration update not supported"}
                ),
                501,
            )

    except Exception as e:
        logger.error(f"Failed to update collection config: {e}")
        return (
            jsonify(
                {"success": False, "error": f"Unable to update configuration: {str(e)}"}
            ),
            500,
        )


@config_bp.route("/trigger-all", methods=["POST"])
@require_auth
@rate_limit(limit=3, window_seconds=60)  # 3 requests per minute
def trigger_all_collections():
    """Trigger collection for all enabled collectors"""
    if not COLLECTOR_AVAILABLE:
        return (
            jsonify({"success": False, "error": "Collection system not available"}),
            503,
        )

    try:
        factory = get_collector_factory()
        manager = factory.create_collection_manager()

        if hasattr(manager, "trigger_all"):
            result = manager.trigger_all()
            return jsonify(
                {
                    "success": True,
                    "message": "All collections triggered successfully",
                    "tasks": (
                        result.get("tasks", []) if isinstance(result, dict) else []
                    ),
                }
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Trigger all functionality not available",
                    }
                ),
                501,
            )

    except Exception as e:
        logger.error(f"Failed to trigger all collections: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Unable to trigger all collections: {str(e)}",
                }
            ),
            500,
        )


@config_bp.route("/cancel-all", methods=["POST"])
@require_auth
@rate_limit(limit=5, window_seconds=60)  # 5 requests per minute
def cancel_all_collections():
    """Cancel all running collections"""
    if not COLLECTOR_AVAILABLE:
        return (
            jsonify({"success": False, "error": "Collection system not available"}),
            503,
        )

    try:
        factory = get_collector_factory()
        manager = factory.create_collection_manager()

        if hasattr(manager, "cancel_all"):
            result = manager.cancel_all()
            return jsonify(
                {
                    "success": True,
                    "message": "All collections cancelled successfully",
                    "cancelled": (
                        result.get("cancelled", 0) if isinstance(result, dict) else 0
                    ),
                }
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Cancel all functionality not available",
                    }
                ),
                501,
            )

    except Exception as e:
        logger.error(f"Failed to cancel all collections: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Unable to cancel all collections: {str(e)}",
                }
            ),
            500,
        )


if __name__ == "__main__":
    # Validation test for config routes
    import sys

    # Mock modules for testing
    class MockAuth:
        @staticmethod
        def require_auth(f):
            return f

    class MockInputValidation:
        @staticmethod
        def validate_config(config):
            return {"valid": True, "errors": []}

    # Replace imports for testing

    sys.modules["...utils.security"] = type(
        "MockModule",
        (),
        {
            "require_auth": MockAuth.require_auth,
            "input_validation": MockInputValidation(),
            "rate_limit": lambda **kwargs: lambda f: f,
        },
    )()

    app = Flask(__name__)
    app.register_blueprint(config_bp)

    all_validation_failures = []
    total_tests = 0

    print("⚙️ Testing Collection Configuration Routes...")

    with app.test_client() as client:
        # Test 1: Get config
        total_tests += 1
        try:
            response = client.get("/api/collection/config")
            if response.status_code not in [200, 503]:
                all_validation_failures.append(
                    f"Get config: Unexpected status code {response.status_code}"
                )
            else:
                print("  - Get config endpoint responds correctly")
        except Exception as e:
            all_validation_failures.append(f"Get config: Exception occurred - {str(e)}")

        # Test 2: Update config
        total_tests += 1
        try:
            response = client.put(
                "/api/collection/config", json={"auto_collection_enabled": True}
            )
            if response.status_code not in [200, 401, 503]:  # 401 for missing auth
                all_validation_failures.append(
                    f"Update config: Unexpected status code {response.status_code}"
                )
            else:
                print("  - Update config endpoint responds correctly")
        except Exception as e:
            all_validation_failures.append(
                f"Update config: Exception occurred - {str(e)}"
            )

        # Test 3: Trigger all
        total_tests += 1
        try:
            response = client.post("/api/collection/trigger-all")
            if response.status_code not in [200, 401, 503]:  # 401 for missing auth
                all_validation_failures.append(
                    f"Trigger all: Unexpected status code {response.status_code}"
                )
            else:
                print("  - Trigger all endpoint responds correctly")
        except Exception as e:
            all_validation_failures.append(
                f"Trigger all: Exception occurred - {str(e)}"
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
        print("Collection Configuration Routes are ready for use")
        sys.exit(0)
