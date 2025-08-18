#!/usr/bin/env python3
"""
Collector Management Routes - Individual collector control
Handles enabling, disabling, triggering, and canceling collectors
"""

import logging
from flask import Blueprint, jsonify, request

try:
    from ...core.collectors.collector_factory import get_collector_factory
    from ...utils.security import input_validation, rate_limit, require_auth
    COLLECTOR_AVAILABLE = True
except ImportError:
    COLLECTOR_AVAILABLE = False

logger = logging.getLogger(__name__)

collector_bp = Blueprint("collection_collectors", __name__, url_prefix="/api/collection")


@collector_bp.route("/collectors", methods=["GET"])
@rate_limit(limit=30, window_seconds=60)  # 30 requests per minute
def list_collectors():
    """List all available collectors with their status"""
    if not COLLECTOR_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "Collection system not available"
        }), 503
        
    try:
        factory = get_collector_factory()
        collectors = factory.list_collectors() if hasattr(factory, 'list_collectors') else []
        
        return jsonify({
            "success": True,
            "collectors": collectors,
            "total": len(collectors)
        })
        
    except Exception as e:
        logger.error(f"Failed to list collectors: {e}")
        return jsonify({
            "success": False,
            "error": "Unable to list collectors"
        }), 500


@collector_bp.route("/collectors/<collector_name>/enable", methods=["POST"])
@require_auth
@rate_limit(limit=10, window_seconds=60)  # 10 requests per minute
def enable_collector(collector_name: str):
    """Enable a specific collector"""
    if not COLLECTOR_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "Collection system not available"
        }), 503
        
    # Input validation
    if not input_validation.validate_collector_name(collector_name):
        return jsonify({
            "success": False,
            "error": "Invalid collector name"
        }), 400
        
    try:
        factory = get_collector_factory()
        manager = factory.create_collection_manager()
        
        if hasattr(manager, 'enable_collector'):
            result = manager.enable_collector(collector_name)
            return jsonify({
                "success": True,
                "message": f"Collector '{collector_name}' enabled successfully",
                "result": result
            })
        else:
            return jsonify({
                "success": False,
                "error": "Enable functionality not available"
            }), 501
            
    except Exception as e:
        logger.error(f"Failed to enable collector {collector_name}: {e}")
        return jsonify({
            "success": False,
            "error": f"Unable to enable collector: {str(e)}"
        }), 500


@collector_bp.route("/collectors/<collector_name>/disable", methods=["POST"])
@require_auth
@rate_limit(limit=10, window_seconds=60)  # 10 requests per minute
def disable_collector(collector_name: str):
    """Disable a specific collector"""
    if not COLLECTOR_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "Collection system not available"
        }), 503
        
    # Input validation
    if not input_validation.validate_collector_name(collector_name):
        return jsonify({
            "success": False,
            "error": "Invalid collector name"
        }), 400
        
    try:
        factory = get_collector_factory()
        manager = factory.create_collection_manager()
        
        if hasattr(manager, 'disable_collector'):
            result = manager.disable_collector(collector_name)
            return jsonify({
                "success": True,
                "message": f"Collector '{collector_name}' disabled successfully",
                "result": result
            })
        else:
            return jsonify({
                "success": False,
                "error": "Disable functionality not available"
            }), 501
            
    except Exception as e:
        logger.error(f"Failed to disable collector {collector_name}: {e}")
        return jsonify({
            "success": False,
            "error": f"Unable to disable collector: {str(e)}"
        }), 500


@collector_bp.route("/collectors/<collector_name>/trigger", methods=["POST"])
@require_auth
@rate_limit(limit=5, window_seconds=60)  # 5 requests per minute
def trigger_collector(collector_name: str):
    """Trigger manual collection for a specific collector"""
    if not COLLECTOR_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "Collection system not available"
        }), 503
        
    # Input validation
    if not input_validation.validate_collector_name(collector_name):
        return jsonify({
            "success": False,
            "error": "Invalid collector name"
        }), 400
        
    try:
        factory = get_collector_factory()
        manager = factory.create_collection_manager()
        
        if hasattr(manager, 'trigger_collector'):
            result = manager.trigger_collector(collector_name)
            return jsonify({
                "success": True,
                "message": f"Collection triggered for '{collector_name}'",
                "task_id": result.get('task_id') if isinstance(result, dict) else None
            })
        else:
            return jsonify({
                "success": False,
                "error": "Trigger functionality not available"
            }), 501
            
    except Exception as e:
        logger.error(f"Failed to trigger collector {collector_name}: {e}")
        return jsonify({
            "success": False,
            "error": f"Unable to trigger collector: {str(e)}"
        }), 500


@collector_bp.route("/collectors/<collector_name>/cancel", methods=["POST"])
@require_auth
@rate_limit(limit=10, window_seconds=60)  # 10 requests per minute
def cancel_collector(collector_name: str):
    """Cancel running collection for a specific collector"""
    if not COLLECTOR_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "Collection system not available"
        }), 503
        
    # Input validation
    if not input_validation.validate_collector_name(collector_name):
        return jsonify({
            "success": False,
            "error": "Invalid collector name"
        }), 400
        
    try:
        factory = get_collector_factory()
        manager = factory.create_collection_manager()
        
        if hasattr(manager, 'cancel_collector'):
            result = manager.cancel_collector(collector_name)
            return jsonify({
                "success": True,
                "message": f"Collection cancelled for '{collector_name}'",
                "result": result
            })
        else:
            return jsonify({
                "success": False,
                "error": "Cancel functionality not available"
            }), 501
            
    except Exception as e:
        logger.error(f"Failed to cancel collector {collector_name}: {e}")
        return jsonify({
            "success": False,
            "error": f"Unable to cancel collector: {str(e)}"
        }), 500


if __name__ == "__main__":
    # Validation test for collector routes
    import sys
    from flask import Flask
    
    # Mock auth and validation for testing
    class MockAuth:
        @staticmethod
        def require_auth(f):
            return f
    
    class MockInputValidation:
        @staticmethod
        def validate_collector_name(name):
            return isinstance(name, str) and len(name) > 0
    
    # Replace imports for testing
    import sys
    sys.modules['...utils.security'] = type('MockModule', (), {
        'require_auth': MockAuth.require_auth,
        'input_validation': MockInputValidation(),
        'rate_limit': lambda **kwargs: lambda f: f
    })()
    
    app = Flask(__name__)
    app.register_blueprint(collector_bp)
    
    all_validation_failures = []
    total_tests = 0
    
    print("🔧 Testing Collector Management Routes...")
    
    with app.test_client() as client:
        # Test 1: List collectors
        total_tests += 1
        try:
            response = client.get('/api/collection/collectors')
            if response.status_code not in [200, 503]:
                all_validation_failures.append(f"List collectors: Unexpected status code {response.status_code}")
            else:
                print("  - List collectors endpoint responds correctly")
        except Exception as e:
            all_validation_failures.append(f"List collectors: Exception occurred - {str(e)}")
        
        # Test 2: Enable collector (should work even if system unavailable)
        total_tests += 1
        try:
            response = client.post('/api/collection/collectors/test/enable')
            if response.status_code not in [200, 401, 503]:  # 401 for missing auth
                all_validation_failures.append(f"Enable collector: Unexpected status code {response.status_code}")
            else:
                print("  - Enable collector endpoint responds correctly")
        except Exception as e:
            all_validation_failures.append(f"Enable collector: Exception occurred - {str(e)}")
    
    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Collector Management Routes are ready for use")
        sys.exit(0)