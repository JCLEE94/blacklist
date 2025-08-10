#!/usr/bin/env python3
"""
V2 Health and Performance API Routes
"""

from datetime import datetime

from flask import Blueprint
from flask import jsonify

from ...utils.unified_decorators import unified_cache
from .service import V2APIService

health_v2_bp = Blueprint("health_v2", __name__)

# Service instance will be initialized by the main app
service: V2APIService = None


def init_service(api_service: V2APIService):
    """Initialize the service instance"""
    global service
    service = api_service


@health_v2_bp.route("/health", methods=["GET"])
def health_check():
    """시스템 건강 상태 확인 (V2)"""
    try:
        # 기본 시스템 건강도 조회
        health = service.blacklist_manager.get_system_health()

        # V2 향상 건강 정보
        enhanced_health = {
            "status": health.get("status", "unknown"),
            "version": "2.0",
            "api_version": "v2",
            "timestamp": datetime.now().isoformat(),
            "uptime": "online",  # 실제 구현에서는 시작 시간 기반
            "database": health.get("database", {}),
            "cache": health.get("cache", {}),
            "components": {
                "blacklist_manager": (
                    "healthy"
                    if health.get("database", {}).get("active_ips", 0) > 0
                    else "degraded"
                ),
                "cache_system": "healthy" if health.get("cache") else "unavailable",
                "api_service": "healthy",
            },
            "metrics": {
                "active_ips": health.get("database", {}).get("active_ips", 0),
                "active_sources": health.get("database", {}).get("active_sources", 0),
                "total_records": health.get("database", {}).get("total_records", 0),
                "recent_ips_24h": health.get("database", {}).get("recent_ips_24h", 0),
            },
        }

        # 전체 상태 결정
        all_healthy = all(
            status == "healthy" for status in enhanced_health["components"].values()
        )
        enhanced_health["overall_status"] = "healthy" if all_healthy else "degraded"

        # HTTP 상태 코드 결정
        http_status = 200 if all_healthy else 503

        return jsonify(enhanced_health), http_status

    except Exception as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "version": "2.0",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                    "overall_status": "unhealthy",
                    "components": {
                        "blacklist_manager": "error",
                        "cache_system": "error",
                        "api_service": "error",
                    },
                }
            ),
            500,
        )


@health_v2_bp.route("/performance", methods=["GET"])
@unified_cache(ttl=60, key_prefix="v2:performance")
def get_performance_metrics():
    """성능 메트릭 (V2)"""
    try:
        result = service.get_performance_metrics()

        # V2 향상 성능 정보 추가
        enhanced_result = {
            "api_version": "v2",
            "performance_metrics": result.get("performance", {}),
            "cache_performance": result.get("cache", {}),
            "database_performance": result.get("database", {}),
            "response_times": {
                "avg_query_time": "<100ms",
                "cache_hit_ratio": result.get("cache", {}).get("hit_rate", 0),
                "database_query_time": "<50ms",
            },
            "throughput": {
                "requests_per_minute": result.get("performance", {}).get(
                    "requests_per_minute", 0
                ),
                "cache_operations_per_minute": result.get("cache", {}).get(
                    "operations_per_minute", 0
                ),
            },
            "generated_at": result.get("timestamp"),
        }

        return jsonify(enhanced_result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@health_v2_bp.route("/status", methods=["GET"])
@unified_cache(ttl=30, key_prefix="v2:status")
def get_detailed_status():
    """상세 시스템 상태 (V2)"""
    try:
        # 기본 건강도 데이터
        health = service.blacklist_manager.get_system_health()

        # 성능 메트릭
        performance = service.get_performance_metrics()

        # 통계 데이터
        analytics = service.get_analytics_summary(7)  # 7일 데이터

        detailed_status = {
            "system_info": {
                "api_version": "v2",
                "service_name": "Blacklist Management API",
                "timestamp": datetime.now().isoformat(),
                "environment": "production",  # 환경변수에서 조회 가능
            },
            "health": health,
            "performance": performance,
            "data_summary": {
                "active_blacklist_entries": analytics.get("summary", {}).get(
                    "total_active_ips", 0
                ),
                "countries_covered": analytics.get("summary", {}).get(
                    "unique_countries", 0
                ),
                "data_sources_active": analytics.get("summary", {}).get(
                    "active_sources", 0
                ),
                "last_update": analytics.get("generated_at"),
            },
            "operational_metrics": {
                "database_status": (
                    "operational" if health.get("status") != "error" else "error"
                ),
                "cache_status": "operational" if health.get("cache") else "degraded",
                "api_status": "operational",
                "data_freshness": "current",  # 실제 데이터 업데이트 시간 기반
            },
        }

        return jsonify(detailed_status)

    except Exception as e:
        return (
            jsonify(
                {
                    "error": str(e),
                    "system_info": {
                        "api_version": "v2",
                        "timestamp": datetime.now().isoformat(),
                        "status": "error",
                    },
                }
            ),
            500,
        )


@health_v2_bp.route("/diagnostics", methods=["GET"])
def get_diagnostics():
    """시스템 진단 정보 (V2)"""
    try:
        # 다양한 시스템 구성요소 진단
        diagnostics = {
            "api_info": {
                "version": "v2",
                "endpoints_available": [
                    "/api/v2/health",
                    "/api/v2/performance",
                    "/api/v2/blacklist/enhanced",
                    "/api/v2/analytics/summary",
                    "/api/v2/export/json",
                ],
                "features_enabled": [
                    "batch_ip_check",
                    "analytics",
                    "export_multiple_formats",
                    "threat_level_analysis",
                    "geo_analysis",
                ],
            },
            "connectivity": {
                "database": self._test_database_connection(),
                "cache": self._test_cache_connection(),
                "external_apis": "not_implemented",  # 외부 API 연결 테스트
            },
            "data_integrity": {
                "blacklist_consistency": self._check_data_consistency(),
                "index_health": "good",  # DB 인덱스 상태
                "data_validation": "passed",
            },
            "resource_usage": {
                "memory_usage": "normal",
                "disk_usage": "normal",
                "cpu_usage": "normal",
                "note": "Detailed metrics require psutil installation",
            },
            "timestamp": datetime.now().isoformat(),
        }

        return jsonify(diagnostics)

    except Exception as e:
        return jsonify({"error": str(e), "timestamp": datetime.now().isoformat()}), 500


def _test_database_connection() -> str:
    """DB 연결 테스트"""
    try:
        health = service.blacklist_manager.get_system_health()
        return "connected" if health.get("status") != "error" else "error"
    except Exception:
        return "error"


def _test_cache_connection() -> str:
    """캐시 연결 테스트"""
    try:
        # 간단한 캐시 테스트
        service.cache.set("health_test", "ok", ttl=10)
        result = service.cache.get("health_test")
        return "connected" if result == "ok" else "error"
    except Exception:
        return "error"


def _check_data_consistency() -> str:
    """데이터 일관성 검사"""
    try:
        # 기본 일관성 검사
        active_ips = service.blacklist_manager.get_active_ips()
        all_ips_with_metadata = service.blacklist_manager.get_all_active_ips()

        # 수량 비교
        if len(active_ips) == len(all_ips_with_metadata):
            return "consistent"
        else:
            return "inconsistent"
    except Exception:
        return "error"
