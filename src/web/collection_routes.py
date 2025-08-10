"""
Web collection routes for Blacklist Manager
Collection control and monitoring pages
"""

import logging
from datetime import datetime
from datetime import timedelta

from flask import Blueprint
from flask import flash
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for

logger = logging.getLogger(__name__)

collection_bp = Blueprint("collection", __name__, url_prefix="")


@collection_bp.route("/blacklist-search")
def blacklist_search():
    """Blacklist search page"""
    return render_template("blacklist_search.html")


@collection_bp.route("/collection-control")
def collection_control():
    """Collection control page"""
    return render_template("collection_control.html")


@collection_bp.route("/raw-data")
def raw_data_viewer():
    """Raw data viewer page"""
    try:
        return render_template(
            "raw_data_modern.html",
            current_time=datetime.now(),
        )
    except Exception as e:
        logger.error(f"Raw data viewer error: {e}")
        flash(f"Raw data 페이지 로드 중 오류가 발생했습니다: {str(e)}", "error")
        return redirect(url_for("dashboard.dashboard"))


@collection_bp.route("/api/raw-data")
def api_raw_data():
    """Raw data API endpoint"""
    try:
        # Get query parameters
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 100, type=int)
        request.args.get("date")
        request.args.get("source")

        # Mock raw data
        mock_data = []
        total_count = 500  # Mock total

        # Generate mock data based on page
        start_idx = (page - 1) * limit
        for i in range(start_idx, min(start_idx + limit, total_count)):
            mock_data.append(
                {
                    "id": i + 1,
                    "ip": f"192.168.{i//255}.{i%255}",
                    "source": "REGTECH" if i % 2 == 0 else "SECUDIUM",
                    "country": "KR" if i % 3 == 0 else "US",
                    "attack_type": "Malware" if i % 2 == 0 else "Phishing",
                    "detection_date": (
                        datetime.now() - timedelta(days=i % 30)
                    ).strftime("%Y-%m-%d"),
                    "created_at": (datetime.now() - timedelta(days=i % 30)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                }
            )

        return jsonify(
            {
                "success": True,
                "data": mock_data,
                "total": total_count,
                "page": page,
                "limit": limit,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Raw data API error: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "data": [],
                    "total": 0,
                }
            ),
            500,
        )


@collection_bp.route("/regtech-collector")
def regtech_collector():
    """REGTECH collector page"""
    try:
        # Mock collector status
        collector_info = {
            "status": "ready",
            "last_collection": "2024-01-15 10:30:00",
            "total_collected": 1250,
            "connection_status": "connected",
        }

        return render_template(
            "regtech_collector.html",
            collector_info=collector_info,
            current_time=datetime.now(),
        )

    except Exception as e:
        logger.error(f"REGTECH collector page error: {e}")
        flash(
            f"REGTECH collector 페이지 로드 중 오류가 발생했습니다: {str(e)}", "error"
        )
        return redirect(url_for("dashboard.dashboard"))


@collection_bp.route("/secudium-collector")
def secudium_collector():
    """SECUDIUM collector page"""
    return render_template("secudium_collector.html")


@collection_bp.route("/api/collection/secudium/test", methods=["POST"])
def api_secudium_test():
    """SECUDIUM collector test API"""
    try:
        # Mock test result
        return jsonify(
            {
                "success": True,
                "message": "SECUDIUM connection test successful",
                "status": "connected",
                "test_time": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"SECUDIUM test error: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                }
            ),
            500,
        )


@collection_bp.route("/api/collection/secudium/trigger", methods=["POST"])
def api_secudium_trigger():
    """SECUDIUM collection trigger API"""
    try:
        # Mock collection trigger
        return jsonify(
            {
                "success": True,
                "message": "SECUDIUM collection started",
                "job_id": "secudium_001",
                "estimated_time": "5 minutes",
                "started_at": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"SECUDIUM trigger error: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                }
            ),
            500,
        )


@collection_bp.route("/api/collection/secudium/progress")
def api_secudium_progress():
    """SECUDIUM collection progress API"""
    try:
        # Mock progress data
        return jsonify(
            {
                "success": True,
                "progress": {
                    "status": "running",
                    "percentage": 65,
                    "current_step": "Processing data",
                    "items_processed": 130,
                    "total_items": 200,
                    "estimated_remaining": "2 minutes",
                },
            }
        )
    except Exception as e:
        logger.error(f"SECUDIUM progress error: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                }
            ),
            500,
        )


@collection_bp.route("/api/collection/secudium/logs")
def api_secudium_logs():
    """SECUDIUM collection logs API"""
    try:
        # Mock log data
        logs = [
            {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "level": "INFO",
                "message": "Starting SECUDIUM collection",
            },
            {
                "timestamp": (datetime.now() - timedelta(seconds=30)).strftime(
                    "%H:%M:%S"
                ),
                "level": "INFO",
                "message": "Connected to SECUDIUM API",
            },
            {
                "timestamp": (datetime.now() - timedelta(minutes=1)).strftime(
                    "%H:%M:%S"
                ),
                "level": "INFO",
                "message": "Processing page 1 of 5",
            },
        ]

        return jsonify(
            {
                "success": True,
                "logs": logs,
            }
        )
    except Exception as e:
        logger.error(f"SECUDIUM logs error: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "logs": [],
                }
            ),
            500,
        )


@collection_bp.route("/api/collection/secudium/status")
def api_secudium_status():
    """SECUDIUM collection status API"""
    try:
        # Mock status data
        return jsonify(
            {
                "success": True,
                "status": {
                    "is_running": False,
                    "last_collection": "2024-01-15 09:45:00",
                    "total_collected": 850,
                    "connection_status": "connected",
                    "next_scheduled": "2024-01-16 09:00:00",
                },
            }
        )
    except Exception as e:
        logger.error(f"SECUDIUM status error: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                }
            ),
            500,
        )


@collection_bp.route("/api/collection/secudium/stop", methods=["POST"])
def api_secudium_stop():
    """SECUDIUM collection stop API"""
    try:
        # Mock stop operation
        return jsonify(
            {
                "success": True,
                "message": "SECUDIUM collection stopped",
                "stopped_at": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"SECUDIUM stop error: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                }
            ),
            500,
        )


@collection_bp.route("/api/regtech/collect", methods=["POST"])
def api_regtech_collect():
    """REGTECH collection API"""
    try:
        data = request.get_json() or {}
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        # Mock collection process
        return jsonify(
            {
                "success": True,
                "message": "REGTECH collection completed",
                "collected_count": 125,
                "date_range": {
                    "start": start_date,
                    "end": end_date,
                },
                "collection_time": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"REGTECH collect error: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                }
            ),
            500,
        )


@collection_bp.route("/api/regtech/stats")
def api_regtech_stats():
    """REGTECH statistics API"""
    try:
        # Mock REGTECH stats
        stats = {
            "total_collected": 1250,
            "last_24h": 85,
            "last_7days": 432,
            "success_rate": 98.5,
            "avg_collection_time": "3.2 minutes",
            "last_collection": "2024-01-15 10:30:00",
        }

        return jsonify(
            {
                "success": True,
                "stats": stats,
            }
        )

    except Exception as e:
        logger.error(f"REGTECH stats error: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                }
            ),
            500,
        )


@collection_bp.route("/api/sources/stats")
def api_sources_stats():
    """All sources statistics API"""
    try:
        # Mock sources stats
        sources = {
            "REGTECH": {
                "total": 1250,
                "active": 1180,
                "last_update": "2024-01-15 10:30:00",
                "status": "active",
            },
            "SECUDIUM": {
                "total": 850,
                "active": 820,
                "last_update": "2024-01-15 09:45:00",
                "status": "active",
            },
        }

        return jsonify(
            {
                "success": True,
                "sources": sources,
                "total_all_sources": sum(s["total"] for s in sources.values()),
                "active_all_sources": sum(s["active"] for s in sources.values()),
            }
        )

    except Exception as e:
        logger.error(f"Sources stats error: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                }
            ),
            500,
        )
