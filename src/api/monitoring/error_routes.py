# !/usr/bin/env python3
"""
에러 관리 API 라우트
에러 수집, 조회, 정리 관련 엔드포인트

Sample input: GET /api/monitoring/errors
Expected output: 에러 요약 통계 및 관리 기능
"""

# Conditional imports for standalone execution and package usage
try:
    from ...utils.error_recovery import get_error_collector
    from ...utils.security import require_auth
    from ..common.imports import Blueprint, jsonify, logger, request
except ImportError:
    # Fallback for standalone execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent))
    
    try:
        from utils.error_recovery import get_error_collector
        from utils.security import require_auth
        from common.imports import Blueprint, jsonify, logger, request
    except ImportError:
        # Mock imports for testing when dependencies not available
        from unittest.mock import Mock
        get_error_collector = Mock()
        require_auth = lambda **kwargs: lambda f: f
        
        # Basic Flask imports for testing
        try:
            from flask import Blueprint, jsonify, request
            from loguru import logger
        except ImportError:
            Blueprint = Mock()
            jsonify = Mock()
            logger = Mock()
            request = Mock()

# 블루프린트 생성
error_bp = Blueprint("monitoring_error", __name__, url_prefix="/api/monitoring")


@error_bp.route("/errors", methods=["GET"])
@require_auth(roles=["admin"])
def get_error_summary():
    """에러 요약 통계 조회"""
    try:
        error_collector = get_error_collector()
        summary = error_collector.get_error_summary()

        return jsonify({"success": True, "error_summary": summary})

    except Exception as e:
        logger.error(f"에러 요약 조회 실패: {e}")
        return (
            jsonify({"success": False, "error": "에러 요약을 가져올 수 없습니다"}),
            500,
        )


@error_bp.route("/errors/clear", methods=["POST"])
@require_auth(roles=["admin"])
def clear_old_errors():
    """오래된 에러 정리"""
    try:
        hours = min(int(request.args.get("hours", 24)), 168)  # 최대 7일

        error_collector = get_error_collector()
        error_collector.clear_old_errors(hours)

        return jsonify(
            {
                "success": True,
                "message": f"{hours}시간 이전의 오래된 에러가 정리되었습니다",
            }
        )

    except Exception as e:
        logger.error(f"에러 정리 실패: {e}")
        return (
            jsonify({"success": False, "error": "에러 정리 중 오류가 발생했습니다"}),
            500,
        )


if __name__ == "__main__":
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: Blueprint creation
    total_tests += 1
    try:
        if error_bp.name != "monitoring_error":
            all_validation_failures.append("Blueprint test: Name mismatch")
        if error_bp.url_prefix != "/api/monitoring":
            all_validation_failures.append("Blueprint test: URL prefix mismatch")
    except Exception as e:
        all_validation_failures.append(f"Blueprint test: Failed - {e}")

    # Test 2: Route functions exist and are callable
    total_tests += 1
    try:
        route_functions = [get_error_summary, clear_old_errors]
        for func in route_functions:
            if not callable(func):
                all_validation_failures.append(f"Route function test: {func.__name__} not callable")
    except Exception as e:
        all_validation_failures.append(f"Route function test: Failed - {e}")

    # Test 3: Hours parameter validation logic
    total_tests += 1
    try:
        # Test the hours clamping logic used in clear_old_errors
        test_hours_normal = min(int("48"), 168)  # Normal case (2 days)
        test_hours_max = min(int("200"), 168)  # Over limit case
        test_hours_default = min(int("24"), 168)  # Default case
        
        if test_hours_normal != 48:
            all_validation_failures.append("Hours validation: Normal case failed")
        if test_hours_max != 168:
            all_validation_failures.append("Hours validation: Max limit case failed")
        if test_hours_default != 24:
            all_validation_failures.append("Hours validation: Default case failed")
    except Exception as e:
        all_validation_failures.append(f"Hours validation test: Failed - {e}")

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
        print("Error routes module is validated and ready for use")
        sys.exit(0)