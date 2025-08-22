# !/usr/bin/env python3
"""
모니터링 공통 에러 핸들러
모든 모니터링 관련 Blueprint에서 공유하는 에러 핸들러

Sample input: HTTP 에러 상황 (400, 401, 403, 429, 500)
Expected output: 일관된 JSON 에러 응답
"""

# Conditional imports for standalone execution and package usage
try:
    from flask import Blueprint, jsonify
except ImportError:
    # Fallback for standalone execution
    try:
        from flask import Blueprint, jsonify
    except ImportError:
        # Mock imports for testing when dependencies not available
        from unittest.mock import Mock
        Blueprint = Mock()
        jsonify = Mock()

# 공통 에러 핸들러를 위한 헬퍼 블루프린트
handlers_bp = Blueprint("monitoring_handlers", __name__)


def register_error_handlers(blueprint):
    """블루프린트에 공통 에러 핸들러 등록"""
    
    @blueprint.errorhandler(400)
    def bad_request(error):
        return jsonify({"success": False, "error": "Invalid request data"}), 400

    @blueprint.errorhandler(401)
    def unauthorized(error):
        return jsonify({"success": False, "error": "Authentication required"}), 401

    @blueprint.errorhandler(403)
    def forbidden(error):
        return jsonify({"success": False, "error": "Insufficient permissions"}), 403

    @blueprint.errorhandler(429)
    def rate_limit_exceeded(error):
        return (
            jsonify(
                {"success": False, "error": "Rate limit exceeded. Please try again later."}
            ),
            429,
        )

    @blueprint.errorhandler(500)
    def internal_error(error):
        return jsonify({"success": False, "error": "Internal server error"}), 500


if __name__ == "__main__":
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: Helper blueprint creation
    total_tests += 1
    try:
        if handlers_bp.name != "monitoring_handlers":
            all_validation_failures.append("Blueprint test: Name mismatch")
    except Exception as e:
        all_validation_failures.append(f"Blueprint test: Failed - {e}")

    # Test 2: Error handler registration function exists
    total_tests += 1
    try:
        if not callable(register_error_handlers):
            all_validation_failures.append("Function test: register_error_handlers not callable")
    except Exception as e:
        all_validation_failures.append(f"Function test: Failed - {e}")

    # Test 3: Error handler registration simulation
    total_tests += 1
    try:
        # Mock blueprint to test registration
        class MockBlueprint:
            def __init__(self):
                self.error_handlers = {}
            
            def errorhandler(self, code):
                def decorator(func):
                    self.error_handlers[code] = func
                    return func
                return decorator
        
        mock_bp = MockBlueprint()
        register_error_handlers(mock_bp)
        
        expected_codes = [400, 401, 403, 429, 500]
        for code in expected_codes:
            if code not in mock_bp.error_handlers:
                all_validation_failures.append(f"Error handler registration: Missing handler for {code}")
    except Exception as e:
        all_validation_failures.append(f"Error handler registration test: Failed - {e}")

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
        print("Common handlers module is validated and ready for use")
        sys.exit(0)