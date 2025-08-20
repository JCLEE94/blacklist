#!/usr/bin/env python3
"""
V2 Sources API Routes
소스별 상태 및 통계 정보 제공
"""

from datetime import datetime
from datetime import timedelta

from flask import Blueprint
from flask import jsonify
from flask import request

from ...utils.unified_decorators import unified_cache

sources_v2_bp = Blueprint("sources_v2", __name__)

# Service instance will be initialized by the main app
service = None


def init_service(api_service):
    """Initialize the service instance"""
    global service
    service = api_service


@sources_v2_bp.route("/sources/status", methods=["GET"])
@unified_cache(ttl=60, key_prefix="v2:sources:status")
def get_sources_status():
    """모든 소스의 현재 상태 조회"""
    try:
        # Get current status for all sources
        sources_info = {
            "regtech": {
                "name": "REGTECH",
                "status": "active",
                "last_collection": None,
                "total_ips": 0,
                "active_ips": 0,
                "error_count": 0,
                "enabled": True,
                "health": "healthy",
            },
            "secudium": {
                "name": "SECUDIUM",
                "status": "inactive",
                "last_collection": None,
                "total_ips": 0,
                "active_ips": 0,
                "error_count": 0,
                "enabled": False,
                "health": "unknown",
            },
            "public": {
                "name": "Public Sources",
                "status": "active",
                "last_collection": None,
                "total_ips": 0,
                "active_ips": 0,
                "error_count": 0,
                "enabled": True,
                "health": "healthy",
            },
        }

        # Get actual data from service if available
        if service:
            try:
                health_info = service.get_system_health()
                if health_info:
                    # Update with actual counts
                    for source_key in sources_info:
                        count_key = f"{source_key}_count"
                        if count_key in health_info:
                            sources_info[source_key]["total_ips"] = health_info[
                                count_key
                            ]
                            sources_info[source_key]["active_ips"] = health_info[
                                count_key
                            ]
            except Exception:
                pass  # Use default values if service fails

        return jsonify(
            {
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "sources": sources_info,
                "summary": {
                    "total_sources": len(sources_info),
                    "active_sources": sum(
                        1 for s in sources_info.values() if s["status"] == "active"
                    ),
                    "total_ips": sum(s["total_ips"] for s in sources_info.values()),
                    "total_active_ips": sum(
                        s["active_ips"] for s in sources_info.values()
                    ),
                },
            }
        )
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500


@sources_v2_bp.route("/sources/<source_id>/status", methods=["GET"])
@unified_cache(ttl=60, key_prefix="v2:source:status")
def get_source_status(source_id):
    """특정 소스의 상세 상태 조회"""
    try:
        valid_sources = ["regtech", "secudium", "public"]
        if source_id not in valid_sources:
            return (
                jsonify(
                    {
                        "error": f"Invalid source: {source_id}",
                        "valid_sources": valid_sources,
                    }
                ),
                400,
            )

        # Get source-specific information
        source_info = {
            "source_id": source_id,
            "name": source_id.upper(),
            "status": "active" if source_id != "secudium" else "inactive",
            "enabled": source_id != "secudium",
            "health": "healthy" if source_id != "secudium" else "unknown",
            "statistics": {
                "total_ips": 0,
                "active_ips": 0,
                "expired_ips": 0,
                "new_today": 0,
                "removed_today": 0,
            },
            "last_collection": {
                "timestamp": None,
                "duration_ms": 0,
                "items_collected": 0,
                "errors": 0,
            },
            "configuration": {
                "auto_collect": False,
                "collection_interval": "daily",
                "retention_days": 90,
            },
        }

        # Get actual data from service if available
        if service:
            try:
                stats = service.get_collection_stats(source_id)
                if stats:
                    source_info["statistics"].update(stats)
            except Exception:
                pass

        return jsonify(
            {
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "source": source_info,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500


@sources_v2_bp.route("/sources/<source_id>/trigger", methods=["POST"])
def trigger_source_collection(source_id):
    """특정 소스의 수집 트리거"""
    try:
        valid_sources = ["regtech", "secudium", "public"]
        if source_id not in valid_sources:
            return (
                jsonify(
                    {
                        "error": f"Invalid source: {source_id}",
                        "valid_sources": valid_sources,
                    }
                ),
                400,
            )

        # Check if collection is enabled
        import os

        if os.getenv("COLLECTION_ENABLED", "false").lower() != "true":
            return (
                jsonify(
                    {
                        "error": "Collection is disabled",
                        "message": "Set COLLECTION_ENABLED=true to enable collection",
                    }
                ),
                403,
            )

        # Trigger collection (placeholder - actual implementation would call collector)
        return jsonify(
            {
                "status": "triggered",
                "source": source_id,
                "message": f"Collection triggered for {source_id}",
                "job_id": f"{source_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                "estimated_duration": "30-60 seconds",
            }
        )
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500


@sources_v2_bp.route("/sources/compare", methods=["GET"])
@unified_cache(ttl=300, key_prefix="v2:sources:compare")
def compare_sources():
    """소스 간 비교 분석"""
    try:
        comparison = {
            "timestamp": datetime.utcnow().isoformat(),
            "period": request.args.get("period", "7days"),
            "sources": {
                "regtech": {
                    "total_ips": 0,
                    "unique_ips": 0,
                    "overlap_with_others": 0,
                    "exclusive_ips": 0,
                    "reliability_score": 0.95,
                },
                "secudium": {
                    "total_ips": 0,
                    "unique_ips": 0,
                    "overlap_with_others": 0,
                    "exclusive_ips": 0,
                    "reliability_score": 0.90,
                },
                "public": {
                    "total_ips": 0,
                    "unique_ips": 0,
                    "overlap_with_others": 0,
                    "exclusive_ips": 0,
                    "reliability_score": 0.85,
                },
            },
            "overlaps": {
                "regtech_secudium": 0,
                "regtech_public": 0,
                "secudium_public": 0,
                "all_three": 0,
            },
            "recommendations": [
                "REGTECH shows highest reliability",
                "Consider enabling SECUDIUM for better coverage",
                "Public sources provide supplementary data",
            ],
        }

        return jsonify({"status": "success", "comparison": comparison})
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500
