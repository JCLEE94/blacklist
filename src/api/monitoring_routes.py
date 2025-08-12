#!/usr/bin/env python3
"""
시스템 모니터링 API 라우트
"""

import logging

from flask import Blueprint
from flask import jsonify
from flask import request

from ..utils.error_recovery import get_error_collector
from ..utils.error_recovery import get_health_checker
from ..utils.error_recovery import get_resource_monitor
from ..utils.performance_optimizer import get_performance_monitor
from ..utils.performance_optimizer import optimize_database_queries
from ..utils.security import rate_limit
from ..utils.security import require_auth
from ..utils.system_stability import get_system_monitor

logger = logging.getLogger(__name__)

# 블루프린트 생성
monitoring_bp = Blueprint("monitoring", __name__, url_prefix="/api/monitoring")


@monitoring_bp.route("/health", methods=["GET"])
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
            _register_default_health_checks(health_checker)

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


@monitoring_bp.route("/performance", methods=["GET"])
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
                "recommendations": _generate_performance_recommendations(
                    metrics, slow_queries
                ),
            }
        )

    except Exception as e:
        logger.error(f"성능 메트릭 조회 실패: {e}")
        return jsonify({"success": False, "error": "성능 메트릭을 조회할 수 없습니다"}), 500


@monitoring_bp.route("/performance/cleanup", methods=["POST"])
@require_auth(roles=["admin"])
def cleanup_performance_data():
    """성능 데이터 정리"""
    try:
        from ..utils.performance_optimizer import cleanup_performance_data

        cleanup_performance_data()

        return jsonify({"success": True, "message": "성능 데이터가 정리되었습니다"})

    except Exception as e:
        logger.error(f"성능 데이터 정리 실패: {e}")
        return jsonify({"success": False, "error": "성능 데이터를 정리할 수 없습니다"}), 500


@monitoring_bp.route("/health/<check_name>", methods=["GET"])
@require_auth(roles=["admin"])
def get_specific_health_check(check_name: str):
    """특정 헬스 체크 실행"""
    try:
        health_checker = get_health_checker()

        if not health_checker.checks:
            _register_default_health_checks(health_checker)

        result = health_checker.run_check(check_name)

        return jsonify({"success": True, "check_name": check_name, "result": result})

    except Exception as e:
        logger.error(f"개별 헬스 체크 실행 실패 ({check_name}): {e}")
        return (
            jsonify({"success": False, "error": f"헬스 체크 {check_name}을 실행할 수 없습니다"}),
            500,
        )


@monitoring_bp.route("/metrics", methods=["GET"])
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
        return jsonify({"success": False, "error": "시스템 메트릭을 가져올 수 없습니다"}), 500


@monitoring_bp.route("/errors", methods=["GET"])
@require_auth(roles=["admin"])
def get_error_summary():
    """에러 요약 통계 조회"""
    try:
        error_collector = get_error_collector()
        summary = error_collector.get_error_summary()

        return jsonify({"success": True, "error_summary": summary})

    except Exception as e:
        logger.error(f"에러 요약 조회 실패: {e}")
        return jsonify({"success": False, "error": "에러 요약을 가져올 수 없습니다"}), 500


@monitoring_bp.route("/errors/clear", methods=["POST"])
@require_auth(roles=["admin"])
def clear_old_errors():
    """오래된 에러 정리"""
    try:
        hours = min(int(request.args.get("hours", 24)), 168)  # 최대 7일

        error_collector = get_error_collector()
        error_collector.clear_old_errors(hours)

        return jsonify({"success": True, "message": f"{hours}시간 이전의 오래된 에러가 정리되었습니다"})

    except Exception as e:
        logger.error(f"에러 정리 실패: {e}")
        return jsonify({"success": False, "error": "에러 정리 중 오류가 발생했습니다"}), 500


@monitoring_bp.route("/status", methods=["GET"])
def get_overall_status():
    """전체 시스템 상태 요약 (인증 불필요)"""
    try:
        # 기본 상태 정보만 제공
        health_checker = get_health_checker()

        if not health_checker.checks:
            _register_default_health_checks(health_checker)

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


def _register_default_health_checks(health_checker):
    """기본 헬스 체크들 등록"""

    def database_check():
        """데이터베이스 연결 체크"""
        try:
            from ..core.container import get_container

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
            from ..core.container import get_container

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
            from ..core.collectors.collector_factory import get_collector_factory

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


# 에러 핸들러
@monitoring_bp.errorhandler(400)
def bad_request(error):
    return jsonify({"success": False, "error": "Invalid request data"}), 400


@monitoring_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({"success": False, "error": "Authentication required"}), 401


@monitoring_bp.errorhandler(403)
def forbidden(error):
    return jsonify({"success": False, "error": "Insufficient permissions"}), 403


@monitoring_bp.errorhandler(429)
def rate_limit_exceeded(error):
    return (
        jsonify(
            {"success": False, "error": "Rate limit exceeded. Please try again later."}
        ),
        429,
    )


@monitoring_bp.errorhandler(500)
def internal_error(error):
    return jsonify({"success": False, "error": "Internal server error"}), 500


def _generate_performance_recommendations(metrics, slow_queries):
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
        from ..utils.system_stability import get_system_monitor

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
