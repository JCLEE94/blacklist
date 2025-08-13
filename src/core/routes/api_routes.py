"""
핵심 API 라우트
핵심 API 엔드포인트: health, blacklist, fortigate
"""

import logging
from datetime import datetime

from flask import Blueprint, Response, jsonify

from ..exceptions import create_error_response
from ..unified_service import get_unified_service

logger = logging.getLogger(__name__)

# API 라우트 블루프린트
api_routes_bp = Blueprint("api_routes", __name__)

# 통합 서비스 인스턴스
service = get_unified_service()


@api_routes_bp.route("/health", methods=["GET"])
@api_routes_bp.route("/healthz", methods=["GET"])
@api_routes_bp.route("/ready", methods=["GET"])
def health_check():
    """통합 서비스 헬스 체크 - K8s probe용 (rate limit 없음)"""
    try:
        health_info = service.get_system_health()
        return jsonify(
            {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "service": "blacklist",
                "version": "2.0.1",
                "details": health_info,
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return (
            jsonify(
                {
                    "status": "unhealthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": str(e),
                }
            ),
            503,
        )


@api_routes_bp.route("/api/health", methods=["GET"])
def service_status():
    """서비스 상태 조회"""
    try:
        stats = service.get_system_stats()
        return jsonify(
            {
                "success": True,
                "data": {
                    "service_status": "running",
                    "database_connected": True,
                    "cache_available": True,
                    "total_ips": stats.get("total_ips", 0),
                    "active_ips": stats.get("active_ips", 0),
                    "last_updated": datetime.utcnow().isoformat(),
                },
            }
        )
    except Exception as e:
        logger.error(f"Service status error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/docs", methods=["GET"])
def api_docs():
    """API 문서"""
    return jsonify(
        {
            "message": "API Documentation",
            "dashboard_url": "/",
            "note": "Visit / or /dashboard for the web interface",
            "api_endpoints": {
                "health": "/health",
                "stats": "/api/stats",
                "blacklist": "/api/blacklist/active",
                "fortigate": "/api/fortigate",
                "collection": "/api/collection/status",
            },
        }
    )


@api_routes_bp.route("/api/blacklist/active", methods=["GET"])
def get_active_blacklist():
    """활성 블랙리스트 조회 (JSON 형식)"""
    try:
        ips = service.get_active_blacklist_ips()

        # JSON 형식으로 반환
        return jsonify(
            {
                "success": True,
                "count": len(ips),
                "ips": ips,
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Active blacklist error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/blacklist/active-txt", methods=["GET"])
def get_active_blacklist_txt():
    """활성 블랙리스트 조회 (플레인 텍스트)"""
    try:
        ips = service.get_active_blacklist_ips()

        # 플레인 텍스트 형식으로 반환
        ip_list = "\n".join(ips) if ips else ""

        response = Response(
            ip_list,
            mimetype="text/plain",
            headers={
                "Content-Disposition": "attachment; filename=blacklist.txt",
                "X-Total-Count": str(len(ips)),
            },
        )
        return response
    except Exception as e:
        logger.error(f"Active blacklist txt error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/blacklist/active-simple", methods=["GET"])
def get_active_blacklist_simple():
    """활성 블랙리스트 조회 (심플 텍스트 - FortiGate용)"""
    try:
        ips = service.get_active_blacklist_ips()

        # 심플 텍스트 형식으로 반환 (한 줄에 하나씩)
        ip_list = "\n".join(ips) if ips else ""

        response = Response(ip_list, mimetype="text/plain")
        return response
    except Exception as e:
        logger.error(f"Active blacklist simple error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/fortigate-simple", methods=["GET"])
def get_fortigate_simple():
    """FortiGate External Connector 형식 (심플 버전)"""
    try:
        ips = service.get_active_blacklist_ips()

        # FortiGate External Connector 형식
        data = {"type": "IP", "version": 1, "data": ips}

        return jsonify(data)
    except Exception as e:
        logger.error(f"FortiGate simple error: {e}")
        return jsonify(create_error_response(e)), 500
