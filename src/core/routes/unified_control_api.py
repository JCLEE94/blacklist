#!/usr/bin/env python3
"""
통합 제어 대시보드 API 라우트
HTML과 분리된 API 엔드포인트들
"""

from datetime import datetime

from flask import Blueprint, jsonify

try:
    from ..collection_db_collector import DatabaseCollectionSystem
    from ..database.collection_settings import CollectionSettingsDB

    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

from .unified_control_html import UNIFIED_DASHBOARD_HTML

bp = Blueprint("unified_control", __name__)


@bp.route("/unified-control")
def unified_control_dashboard():
    """통합 제어 대시보드 메인 페이지"""
    return UNIFIED_DASHBOARD_HTML


@bp.route("/api/unified/status")
def get_unified_status():
    """통합 시스템 상태 조회"""
    if not DB_AVAILABLE:
        return jsonify({"error": "Database not available"}), 500

    try:
        db = CollectionSettingsDB()
        DatabaseCollectionSystem()

        # 기본 통계
        stats = db.get_collection_statistics()

        # 활성 소스
        sources = db.get_all_sources()
        active_sources = [s for s in sources if s["enabled"]]

        # 최근 상태
        recent_collections = stats.get("recent_collections", [])[:5]

        return jsonify(
            {
                "status": "healthy",
                "statistics": {
                    "total_collections": stats.get("total_collections", 0),
                    "successful_collections": stats.get("successful_collections", 0),
                    "failed_collections": stats.get("failed_collections", 0),
                    "total_ips": stats.get("total_ips_collected", 0),
                },
                "sources": {
                    "total": len(sources),
                    "active": len(active_sources),
                    "list": active_sources,
                },
                "recent_activity": recent_collections,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@bp.route("/api/unified/health")
def health_check():
    """헬스 체크"""
    try:
        if not DB_AVAILABLE:
            return (
                jsonify(
                    {
                        "status": "degraded",
                        "message": "Database not available",
                        "components": {
                            "database": "unavailable",
                            "collector": "unavailable",
                        },
                    }
                ),
                503,
            )

        # DB 연결 테스트
        db = CollectionSettingsDB()
        sources = db.get_all_sources()

        return jsonify(
            {
                "status": "healthy",
                "message": "All systems operational",
                "components": {"database": "healthy", "collector": "healthy"},
                "sources_count": len(sources),
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        return (
            jsonify(
                {
                    "status": "unhealthy",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )
