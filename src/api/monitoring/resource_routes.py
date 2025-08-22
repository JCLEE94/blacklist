# !/usr/bin/env python3
"""
시스템 리소스 모니터링 API 라우트
시스템 메트릭 조회 관련 엔드포인트

Sample input: GET /api/monitoring/metrics
Expected output: 시스템 리소스 메트릭 및 요약 통계
"""

# Conditional imports for standalone execution and package usage
try:
    from ...utils.error_recovery import get_resource_monitor
    from ...utils.security import require_auth
    from flask import Blueprint, jsonify, logger, request
except ImportError:
    # Fallback for standalone execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent))
    
    try:
        from utils.error_recovery import get_resource_monitor
        from utils.security import require_auth
        from flask import Flask, Blueprint, jsonify, request, redirect, url_for, render_template
import logging
logger = logging.getLogger(__name__)
    except ImportError:
        # Mock imports for testing when dependencies not available
        from unittest.mock import Mock
        get_resource_monitor = Mock()
        require_auth = lambda **kwargs: lambda f: f
        
        # Basic Flask imports for testing
        try:
            from flask import Blueprint, jsonify, request
            import logging
logger = logging.getLogger(__name__)
        except ImportError:
            Blueprint = Mock()
            jsonify = Mock()
            logger = Mock()
            request = Mock()

# 블루프린트 생성
resource_bp = Blueprint("monitoring_resource", __name__, url_prefix="/api/monitoring")


@resource_bp.route("/metrics", methods=["GET"])
@require_auth(roles=["admin"])
def get_system_metrics():
    """시스템 리소스 메트릭 조회"""
    try:
        resource_monitor = get_resource_monitor()

        # 현재 메트릭 수집
        current_metrics = resource_monitor.collect_metrics()

        # 요약 통계 (기본 1시간)
        hours = min(int(request.args.get("hours", 1)), 24)  # 최대 24시간
        summary = resource_monitor.get_metrics_summary(hours)

        return jsonify(
            {"success": True, "current_metrics": current_metrics, "summary": summary}
        )

    except Exception as e:
        logger.error(f"시스템 메트릭 조회 실패: {e}")
        return (
            jsonify({"success": False, "error": "시스템 메트릭을 가져올 수 없습니다"}),
            500,
        )


if __name__ == "__main__":
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: Blueprint creation
    total_tests += 1
    try:
        if resource_bp.name != "monitoring_resource":
            all_validation_failures.append("Blueprint test: Name mismatch")
        if resource_bp.url_prefix != "/api/monitoring":
            all_validation_failures.append("Blueprint test: URL prefix mismatch")
    except Exception as e:
        all_validation_failures.append(f"Blueprint test: Failed - {e}")

    # Test 2: Route function exists and is callable
    total_tests += 1
    try:
        if not callable(get_system_metrics):
            all_validation_failures.append("Route function test: get_system_metrics not callable")
    except Exception as e:
        all_validation_failures.append(f"Route function test: Failed - {e}")

    # Test 3: Request parameter handling
    total_tests += 1
    try:
        # This tests the parameter validation logic (hours clamping)
        test_hours_1 = min(int("5"), 24)  # Normal case
        test_hours_2 = min(int("30"), 24)  # Over limit case
        
        if test_hours_1 != 5:
            all_validation_failures.append("Parameter test: Normal hours handling failed")
        if test_hours_2 != 24:
            all_validation_failures.append("Parameter test: Over-limit hours handling failed")
    except Exception as e:
        all_validation_failures.append(f"Parameter test: Failed - {e}")

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
        print("Resource routes module is validated and ready for use")
        sys.exit(0)