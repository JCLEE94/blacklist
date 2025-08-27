# !/usr/bin/env python3
"""
성능 모니터링 API 라우트
성능 메트릭 조회 및 성능 최적화 관련 엔드포인트

Sample input: GET /api/monitoring/performance
Expected output: 상세 성능 메트릭 및 권장사항
"""

# Conditional imports for standalone execution and package usage
try:
    from flask import Blueprint, jsonify, logger

    from ...utils.performance_optimizer import (
        cleanup_performance_data,
        get_performance_monitor,
        optimize_database_queries,
    )
    from ...utils.security import rate_limit, require_auth
    from ...utils.system_stability import get_system_monitor
except ImportError:
    # Fallback for standalone execution
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).parent.parent.parent))

    try:
        import logging

        from flask import (
            Blueprint,
            jsonify,
        )

        from utils.performance_optimizer import (
            cleanup_performance_data,
            get_performance_monitor,
            optimize_database_queries,
        )
        from utils.security import rate_limit, require_auth
        from utils.system_stability import get_system_monitor

        logger = logging.getLogger(__name__)
    except ImportError:
        # Mock imports for testing when dependencies not available
        from unittest.mock import Mock

        get_performance_monitor = Mock()
        optimize_database_queries = Mock(return_value=[])
        cleanup_performance_data = Mock()

        def rate_limit(**kwargs):
            def decorator(f):
                return f

            return decorator

        def require_auth(**kwargs):
            def decorator(f):
                return f

            return decorator

        get_system_monitor = Mock()

        # Basic Flask imports for testing
        try:
            import logging

            from flask import Blueprint, jsonify

            logger = logging.getLogger(__name__)
        except ImportError:
            Blueprint = Mock()
            jsonify = Mock()
            logger = Mock()

# 블루프린트 생성
performance_bp = Blueprint(
    "monitoring_performance", __name__, url_prefix="/api/monitoring"
)


@performance_bp.route("/performance", methods=["GET"])
@require_auth(roles=["admin"])
@rate_limit(limit=30, window_seconds=60)
def get_performance_metrics():
    """상세 성능 메트릭 조회"""
    try:
        performance_monitor = get_performance_monitor()
        metrics = performance_monitor.get_current_metrics()

        # 느린 쿼리 분석
        slow_queries = optimize_database_queries()

        # 캐시 통계
        cache_stats = performance_monitor.smart_cache.get_stats()

        return jsonify(
            {
                "success": True,
                "timestamp": metrics.timestamp.isoformat(),
                "performance": {
                    "total_requests": metrics.total_requests,
                    "avg_response_time_ms": metrics.avg_response_time,
                    "cache_hit_rate": metrics.cache_hit_rate,
                    "memory_usage_mb": metrics.memory_usage_mb,
                    "database_query_time": metrics.database_query_time,
                    "active_connections": metrics.active_connections,
                    "error_rate": metrics.error_rate,
                },
                "cache_stats": cache_stats,
                "slow_queries": slow_queries,
                "recommendations": generate_performance_recommendations(
                    metrics, slow_queries
                ),
            }
        )

    except Exception as e:
        logger.error(f"성능 메트릭 조회 실패: {e}")
        return (
            jsonify({"success": False, "error": "성능 메트릭을 조회할 수 없습니다"}),
            500,
        )


@performance_bp.route("/performance/cleanup", methods=["POST"])
@require_auth(roles=["admin"])
def cleanup_performance_data_endpoint():
    """성능 데이터 정리"""
    try:
        cleanup_performance_data()

        return jsonify({"success": True, "message": "성능 데이터가 정리되었습니다"})

    except Exception as e:
        logger.error(f"성능 데이터 정리 실패: {e}")
        return (
            jsonify({"success": False, "error": "성능 데이터를 정리할 수 없습니다"}),
            500,
        )


def generate_performance_recommendations(metrics, slow_queries):
    """성능 최적화 권장사항 생성"""
    recommendations = []

    # 응답 시간 기반 권장사항
    if metrics.avg_response_time > 1000:  # 1초 이상
        recommendations.append(
            {
                "type": "critical",
                "area": "response_time",
                "message": f"평균 응답시간이 {metrics.avg_response_time}ms로 매우 느립니다",
                "suggestion": "데이터베이스 쿼리 최적화, 캐시 활용 증대, 인덱스 추가를 검토하세요",
            }
        )
    elif metrics.avg_response_time > 500:  # 500ms 이상
        recommendations.append(
            {
                "type": "warning",
                "area": "response_time",
                "message": f"평균 응답시간이 {metrics.avg_response_time}ms로 개선이 필요합니다",
                "suggestion": "주요 API 엔드포인트의 성능을 모니터링하고 병목 지점을 식별하세요",
            }
        )

    # 캐시 활용률 기반 권장사항
    if metrics.cache_hit_rate < 50:
        recommendations.append(
            {
                "type": "warning",
                "area": "cache",
                "message": f"캐시 적중률이 {metrics.cache_hit_rate}%로 낮습니다",
                "suggestion": "캐시 TTL 설정 최적화, 자주 사용되는 데이터의 캐시 적용을 검토하세요",
            }
        )

    # 느린 쿼리 기반 권장사항
    if slow_queries:
        recommendations.append(
            {
                "type": "critical",
                "area": "database",
                "message": f"{len(slow_queries)}개의 느린 쿼리가 감지되었습니다",
                "suggestion": "쿼리 최적화, 인덱스 추가, 데이터베이스 스키마 개선을 검토하세요",
            }
        )

    # 메모리 사용량 기반 권장사항 (시스템 모니터에서 가져와야 함)
    try:
        system_monitor = get_system_monitor()
        health = system_monitor.get_system_health()

        if health.memory_percent > 85:
            recommendations.append(
                {
                    "type": "critical",
                    "area": "memory",
                    "message": f"메모리 사용률이 {health.memory_percent}%로 매우 높습니다",
                    "suggestion": "메모리 누수 확인, 불필요한 객체 정리, 메모리 캐시 크기 조정을 검토하세요",
                }
            )
        elif health.memory_percent > 75:
            recommendations.append(
                {
                    "type": "warning",
                    "area": "memory",
                    "message": f"메모리 사용률이 {health.memory_percent}%로 높습니다",
                    "suggestion": "메모리 사용 패턴을 모니터링하고 최적화를 검토하세요",
                }
            )

        if health.cpu_percent > 80:
            recommendations.append(
                {
                    "type": "warning",
                    "area": "cpu",
                    "message": f"CPU 사용률이 {health.cpu_percent}%로 높습니다",
                    "suggestion": "비동기 처리, 배치 처리, 워커 프로세스 추가를 검토하세요",
                }
            )
    except Exception:
        pass  # 시스템 모니터링 실패 시 권장사항 제외

    return recommendations


if __name__ == "__main__":
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: Blueprint creation
    total_tests += 1
    try:
        if performance_bp.name != "monitoring_performance":
            all_validation_failures.append("Blueprint test: Name mismatch")
        if performance_bp.url_prefix != "/api/monitoring":
            all_validation_failures.append("Blueprint test: URL prefix mismatch")
    except Exception as e:
        all_validation_failures.append(f"Blueprint test: Failed - {e}")

    # Test 2: Performance recommendations function
    total_tests += 1
    try:
        # Mock metrics object for testing
        class MockMetrics:
            def __init__(self):
                self.avg_response_time = 750  # Should trigger warning
                self.cache_hit_rate = 30  # Should trigger warning

        mock_metrics = MockMetrics()
        mock_slow_queries = ["SELECT * FROM table", "UPDATE table SET col=val"]

        recommendations = generate_performance_recommendations(
            mock_metrics, mock_slow_queries
        )

        # Should have at least 3 recommendations (response time, cache, slow queries)
        if len(recommendations) < 3:
            all_validation_failures.append(
                f"Performance recommendations: Expected at least 3, got {len(recommendations)}"
            )

        # Check for expected recommendation types
        rec_areas = [rec.get("area") for rec in recommendations]
        expected_areas = ["response_time", "cache", "database"]
        for area in expected_areas:
            if area not in rec_areas:
                all_validation_failures.append(
                    f"Performance recommendations: Missing {area} recommendation"
                )

    except Exception as e:
        all_validation_failures.append(
            f"Performance recommendations test: Failed - {e}"
        )

    # Test 3: Route functions exist and are callable
    total_tests += 1
    try:
        route_functions = [get_performance_metrics, cleanup_performance_data_endpoint]
        for func in route_functions:
            if not callable(func):
                all_validation_failures.append(
                    f"Route function test: {func.__name__} not callable"
                )
    except Exception as e:
        all_validation_failures.append(f"Route function test: Failed - {e}")

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
        print("Performance routes module is validated and ready for use")
        sys.exit(0)
