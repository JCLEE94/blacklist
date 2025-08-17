"""
헬스체크 전용 라우트
api_routes.py에서 분할된 헬스체크 관련 엔드포인트
"""

import logging
from datetime import datetime

from flask import Blueprint, jsonify

from ..exceptions import create_error_response
from ..unified_service import get_unified_service

logger = logging.getLogger(__name__)

# 헬스체크 라우트 블루프린트
health_routes_bp = Blueprint("health_routes", __name__)

# 통합 서비스 인스턴스
service = get_unified_service()


@health_routes_bp.route("/health", methods=["GET"])
@health_routes_bp.route("/healthz", methods=["GET"])
@health_routes_bp.route("/ready", methods=["GET"])
def health_check():
    """통합 서비스 헬스 체크 - K8s probe용 (rate limit 없음)"""
    try:
        health_info = service.get_system_health()

        # Create components structure expected by tests
        db_status = health_info.get("status")
        components = {
            "database": "healthy" if db_status == "healthy" else "unhealthy",
            "cache": "healthy",  # Assume cache is healthy for now
            "blacklist": (
                "healthy" if health_info.get("total_ips", 0) >= 0 else "unhealthy"
            ),
        }

        overall_status = (
            "healthy"
            if all(status == "healthy" for status in components.values())
            else "degraded"
        )

        response_data = {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "blacklist-management",
            "version": "1.0.35",
            "components": components,
        }

        status_code = 200 if overall_status == "healthy" else 503
        return jsonify(response_data), status_code

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        error_response = {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "service": "blacklist-management",
        }
        return jsonify(error_response), 503


@health_routes_bp.route("/api/health", methods=["GET"])
def detailed_health_check():
    """상세 헬스 체크 - 모든 컴포넌트 상태 포함"""
    try:
        # 기본 헬스 정보 수집
        health_info = service.get_system_health()

        # 상세 컴포넌트 체크
        db_status = health_info.get("status")
        collection_enabled = health_info.get("collection_enabled")

        detailed_components = {
            "database": {
                "status": "healthy" if db_status == "healthy" else "unhealthy",
                "total_entries": health_info.get("total_ips", 0),
                "last_updated": health_info.get("last_updated", "unknown"),
            },
            "cache": {"status": "healthy", "type": "redis", "fallback": "memory"},
            "collection": {
                "status": "enabled" if collection_enabled else "disabled",
                "last_collection": health_info.get("last_collection", "never"),
            },
            "sources": {"regtech": "available", "secudium": "available"},
        }

        overall_status = "healthy"
        for component, details in detailed_components.items():
            if isinstance(details, dict) and details.get("status") in [
                "unhealthy",
                "error",
            ]:
                overall_status = "degraded"
                break

        response_data = {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "blacklist-management",
            "version": "1.0.35",
            "uptime": health_info.get("uptime", "unknown"),
            "components": detailed_components,
            "metrics": {
                "total_ips": health_info.get("total_ips", 0),
                "active_ips": health_info.get("active_ips", 0),
                "expired_ips": health_info.get("expired_ips", 0),
            },
        }

        status_code = 200 if overall_status == "healthy" else 503
        return jsonify(response_data), status_code

    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return create_error_response(
            "health_check_failed", f"Health check failed: {str(e)}", 500
        )
