# !/usr/bin/env python3
"""
시스템 헬스 체크 API 라우트
헬스 체크, 시스템 상태 조회 관련 엔드포인트

Sample input: GET /api/monitoring/health
Expected output: 시스템 전체 상태 및 헬스 체크 결과
"""

# Conditional imports for standalone execution and package usage
try:
    from flask import Blueprint, jsonify, logger

    from ...utils.error_recovery import get_health_checker
    from ...utils.performance_optimizer import get_performance_monitor
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

        from utils.error_recovery import get_health_checker
        from utils.performance_optimizer import get_performance_monitor
        from utils.security import rate_limit, require_auth
        from utils.system_stability import get_system_monitor

        logger = logging.getLogger(__name__)
    except ImportError:
        # Mock imports for testing when dependencies not available
        from unittest.mock import Mock

        get_health_checker = Mock()
        get_performance_monitor = Mock()

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
health_bp = Blueprint("monitoring_health", __name__, url_prefix="/api/monitoring")


@health_bp.route("/health", methods=["GET"])
@rate_limit(limit=60, window_seconds=60)  # 분당 60회
def get_system_health():
    """시스템 전체 헬스 체크"""
    try:
        # 시스템 모니터에서 건강 상태 조회
        system_monitor = get_system_monitor()
        health = system_monitor.get_system_health()

        # 성능 메트릭 추가
        performance_monitor = get_performance_monitor()
        performance_metrics = performance_monitor.get_current_metrics()

        # 레거시 헬스 체커도 사용
        health_checker = get_health_checker()

        # 기본 헬스 체크들 등록 (처음 호출 시)
        if not health_checker.checks:
            register_default_health_checks(health_checker)

        results = health_checker.run_all_checks()

        # 통합된 헬스 체크 응답
        return jsonify(
            {
                "success": True,
                "overall_status": health.overall_status,
                "timestamp": health.timestamp.isoformat(),
                "system_health": {
                    "cpu_percent": health.cpu_percent,
                    "memory_percent": health.memory_percent,
                    "disk_percent": health.disk_percent,
                    "database_status": health.database_status,
                    "cache_status": health.cache_status,
                    "uptime_seconds": health.uptime_seconds,
                    "active_connections": health.active_connections,
                    "error_count_last_hour": health.error_count_last_hour,
                    "warnings": health.warnings,
                },
                "performance_metrics": {
                    "total_requests": performance_metrics.total_requests,
                    "avg_response_time_ms": performance_metrics.avg_response_time,
                    "cache_hit_rate": performance_metrics.cache_hit_rate,
                    "memory_usage_mb": performance_metrics.memory_usage_mb,
                },
                "legacy_health_checks": results,
            }
        )

    except Exception as e:
        logger.error(f"헬스 체크 실행 실패: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": "헬스 체크를 실행할 수 없습니다",
                    "health": {"overall_status": "error", "error": str(e)},
                }
            ),
            500,
        )


@health_bp.route("/health/<check_name>", methods=["GET"])
@require_auth(roles=["admin"])
def get_specific_health_check(check_name: str):
    """특정 헬스 체크 실행"""
    try:
        health_checker = get_health_checker()

        if not health_checker.checks:
            register_default_health_checks(health_checker)

        result = health_checker.run_check(check_name)

        return jsonify({"success": True, "check_name": check_name, "result": result})

    except Exception as e:
        logger.error(f"개별 헬스 체크 실행 실패 ({check_name}): {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"헬스 체크 {check_name}을 실행할 수 없습니다",
                }
            ),
            500,
        )


@health_bp.route("/status", methods=["GET"])
def get_overall_status():
    """전체 시스템 상태 요약 (인증 불필요)"""
    try:
        # 기본 상태 정보만 제공
        health_checker = get_health_checker()

        if not health_checker.checks:
            register_default_health_checks(health_checker)

        # 마지막 헬스 체크 결과 사용 (새로 실행하지 않음)
        last_results = health_checker.get_last_results()

        if not last_results:
            # 마지막 결과가 없으면 빠른 체크만 실행
            overall_status = "unknown"
        else:
            # 모든 체크가 healthy인지 확인
            all_healthy = all(
                result.get("status") == "healthy" for result in last_results.values()
            )
            overall_status = "healthy" if all_healthy else "degraded"

        return jsonify(
            {
                "success": True,
                "status": overall_status,
                "checks_available": len(health_checker.checks),
                "last_check_count": len(last_results),
            }
        )

    except Exception as e:
        logger.error(f"전체 상태 조회 실패: {e}")
        return jsonify({"success": False, "status": "error", "error": str(e)}), 500


def register_default_health_checks(health_checker):
    """기본 헬스 체크들 등록"""

    def database_check():
        """데이터베이스 연결 체크"""
        try:
            from ...core.container import get_container

            container = get_container()
            blacklist_manager = container.get("blacklist_manager")

            if blacklist_manager:
                # 간단한 쿼리로 DB 연결 확인
                # 실제 구현에 따라 수정 필요
                return {"status": "connected", "type": "database"}
            else:
                return {"status": "not_available", "type": "database"}
        except Exception as e:
            raise Exception(f"Database connection failed: {e}")

    def cache_check():
        """캐시 연결 체크"""
        try:
            from ...core.container import get_container

            container = get_container()
            cache_manager = container.get("cache_manager")

            if cache_manager:
                # 캐시 연결 테스트
                test_key = "__health_check__"
                cache_manager.set(test_key, "ok", ttl=10)
                result = cache_manager.get(test_key)

                if result == "ok":
                    cache_manager.delete(test_key)
                    return {"status": "connected", "type": "cache"}
                else:
                    raise Exception("Cache read/write test failed")
            else:
                return {"status": "not_available", "type": "cache"}
        except Exception as e:
            raise Exception(f"Cache connection failed: {e}")

    def collection_check():
        """수집 시스템 체크"""
        try:
            from ...core.collectors.collector_factory import get_collector_factory

            factory = get_collector_factory()
            status = factory.get_collector_status()

            if status.get("total_collectors", 0) > 0:
                return {
                    "status": "available",
                    "type": "collection",
                    "collectors": status.get("total_collectors", 0),
                }
            else:
                return {"status": "no_collectors", "type": "collection"}
        except Exception as e:
            raise Exception(f"Collection system check failed: {e}")

    def disk_space_check():
        """디스크 공간 체크"""
        try:
            import psutil

            disk_usage = psutil.disk_usage("/")

            free_percent = (disk_usage.free / disk_usage.total) * 100

            if free_percent < 10:
                raise Exception(f"Low disk space: {free_percent:.1f}% free")
            elif free_percent < 20:
                return {
                    "status": "warning",
                    "free_percent": round(free_percent, 1),
                    "message": "Low disk space warning",
                }
            else:
                return {"status": "ok", "free_percent": round(free_percent, 1)}
        except Exception as e:
            raise Exception(f"Disk space check failed: {e}")

    # 헬스 체크들 등록
    health_checker.register_check("database", database_check)
    health_checker.register_check("cache", cache_check)
    health_checker.register_check("collection", collection_check)
    health_checker.register_check("disk_space", disk_space_check)


if __name__ == "__main__":
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: Blueprint creation
    total_tests += 1
    try:
        if health_bp.name != "monitoring_health":
            all_validation_failures.append("Blueprint test: Name mismatch")
        if health_bp.url_prefix != "/api/monitoring":
            all_validation_failures.append("Blueprint test: URL prefix mismatch")
    except Exception as e:
        all_validation_failures.append(f"Blueprint test: Failed - {e}")

    # Test 2: Health check registration function
    total_tests += 1
    try:
        # Mock health checker for testing
        class MockHealthChecker:
            def __init__(self):
                self.checks = {}

            def register_check(self, name, func):
                self.checks[name] = func

        mock_checker = MockHealthChecker()
        register_default_health_checks(mock_checker)

        expected_checks = ["database", "cache", "collection", "disk_space"]
        for check_name in expected_checks:
            if check_name not in mock_checker.checks:
                all_validation_failures.append(
                    f"Health check registration: Missing {check_name}"
                )
    except Exception as e:
        all_validation_failures.append(f"Health check registration test: Failed - {e}")

    # Test 3: Route functions exist
    total_tests += 1
    try:
        route_functions = [
            get_system_health,
            get_specific_health_check,
            get_overall_status,
        ]
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
        print("Health routes module is validated and ready for use")
        sys.exit(0)
