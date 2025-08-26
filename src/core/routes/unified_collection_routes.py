#!/usr/bin/env python3
"""
Unified collection routes - single endpoint for all collection operations.
Removes duplicate collection endpoints scattered across the codebase.
"""


import logging
import sqlite3
import os
from datetime import datetime

from flask import Blueprint, Flask, jsonify, redirect, render_template, request, url_for

logger = logging.getLogger(__name__)

from ..auth_manager import get_auth_manager
from ..container import get_container

unified_collection_bp = Blueprint(
    "unified_collection", __name__, url_prefix="/api/collection"
)


@unified_collection_bp.route("/status", methods=["GET"])
def get_collection_status():
    """Get unified collection status for all sources"""
    try:
        container = get_container()
        collection_mgr = container.get("collection_manager")

        # Get auth status
        auth_manager = get_auth_manager()
        auth_config = auth_manager.get_config()

        # Build comprehensive status
        status = {
            "enabled": (
                collection_mgr.is_collection_enabled() if collection_mgr else False
            ),
            "sources": {
                "regtech": {
                    "enabled": auth_config["regtech"]["enabled"],
                    "configured": auth_config["regtech"]["password_set"],
                    "username": auth_config["regtech"]["username"],
                    "last_collection": _get_last_collection_time("REGTECH"),
                },
                "secudium": {
                    "enabled": auth_config["secudium"]["enabled"],
                    "configured": auth_config["secudium"]["password_set"],
                    "username": auth_config["secudium"]["username"],
                    "last_collection": _get_last_collection_time("SECUDIUM"),
                },
            },
            "statistics": {"total_ips": 0, "active_ips": 0, "today_collected": 0},
        }

        # Get statistics from blacklist manager
        blacklist_mgr = container.get("blacklist_manager")
        if blacklist_mgr:
            active_ips = blacklist_mgr.get_active_ips()
            status["statistics"]["total_ips"] = len(active_ips) if active_ips else 0
            status["statistics"]["active_ips"] = len(active_ips) if active_ips else 0

        return jsonify(status)

    except Exception as e:
        logger.error(f"Failed to get collection status: {e}")
        return jsonify({"error": "Failed to get status", "message": str(e)}), 500


@unified_collection_bp.route("/trigger", methods=["POST"])
def trigger_collection():
    """Unified collection trigger for any source"""
    try:
        data = request.get_json() or {}
        source = data.get("source", "all")

        # Get auth manager
        auth_manager = get_auth_manager()

        results = {"success": True, "triggered": [], "failed": [], "messages": []}

        sources_to_trigger = []
        if source == "all":
            sources_to_trigger = ["regtech", "secudium"]
        elif source in ["regtech", "secudium"]:
            sources_to_trigger = [source]
        else:
            return (
                jsonify({"success": False, "error": f"Invalid source: {source}"}),
                400,
            )

        # Trigger each source
        for src in sources_to_trigger:
            credentials = auth_manager.get_credentials(src)
            if not credentials:
                results["failed"].append(src)
                results["messages"].append(f"{src}: Not configured or disabled")
                continue

            try:
                # Get collection manager
                container = get_container()
                collection_mgr = container.get("collection_manager")

                if not collection_mgr:
                    results["failed"].append(src)
                    results["messages"].append(
                        f"{src}: Collection manager not available"
                    )
                    continue

                # Trigger collection with credentials
                if src == "regtech":
                    # Call REGTECH collector with credentials
                    from ..collectors.regtech_collector import RegtechCollector

                    collector = RegtechCollector()
                    collector.username = credentials["username"]
                    collector.password = credentials["password"]

                    # Collect data
                    success, message = collector.collect()

                elif src == "secudium":
                    # Call SECUDIUM collector with credentials
                    from ..collectors.secudium_collector import SecudiumCollector

                    collector = SecudiumCollector()
                    collector.username = credentials["username"]
                    collector.password = credentials["password"]

                    # Collect data
                    success, message = collector.collect()

                if success:
                    results["triggered"].append(src)
                    results["messages"].append(
                        f"{src}: Collection triggered successfully"
                    )
                else:
                    results["failed"].append(src)
                    results["messages"].append(f"{src}: {message}")

            except Exception as e:
                results["failed"].append(src)
                results["messages"].append(f"{src}: {str(e)}")
                logger.error(f"Failed to trigger {src}: {e}")

        # Set overall success
        results["success"] = len(results["failed"]) == 0

        return jsonify(results)

    except Exception as e:
        logger.error(f"Failed to trigger collection: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@unified_collection_bp.route("/enable", methods=["POST"])
def enable_collection():
    """Enable collection system"""
    try:
        container = get_container()
        collection_mgr = container.get("collection_manager")

        if collection_mgr:
            collection_mgr.enable_collection()
            return jsonify({"success": True, "message": "Collection enabled"})
        else:
            return (
                jsonify(
                    {"success": False, "error": "Collection manager not available"}
                ),
                500,
            )

    except Exception as e:
        logger.error(f"Failed to enable collection: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@unified_collection_bp.route("/disable", methods=["POST"])
def disable_collection():
    """Disable collection system"""
    try:
        container = get_container()
        collection_mgr = container.get("collection_manager")

        if collection_mgr:
            collection_mgr.disable_collection()
            return jsonify({"success": True, "message": "Collection disabled"})
        else:
            return (
                jsonify(
                    {"success": False, "error": "Collection manager not available"}
                ),
                500,
            )

    except Exception as e:
        logger.error(f"Failed to disable collection: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@unified_collection_bp.route("/history", methods=["GET"])
def get_collection_history():
    """Get collection history"""
    try:
        # 실제 데이터베이스에서 히스토리 조회
        history = _get_collection_history_from_db()

        return jsonify(history)

    except Exception as e:
        logger.error(f"Failed to get collection history: {e}")
        return jsonify({"error": "Failed to get history", "message": str(e)}), 500


def _get_last_collection_time(source: str) -> str:
    """데이터베이스에서 마지막 수집 시간 조회

    Args:
        source: 데이터 소스 ('REGTECH' or 'SECUDIUM')

    Returns:
        ISO 형식의 마지막 수집 시간 또는 None
    """
    try:
        db_path = "instance/blacklist.db"
        if not os.path.exists(db_path):
            return None

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # collection_logs 테이블 존재 확인
            cursor.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='collection_logs'
            """
            )

            if not cursor.fetchone():
                return None

            # 마지막 성공한 수집 시간 조회
            cursor.execute(
                """
                SELECT MAX(created_at) FROM collection_logs 
                WHERE source = ? AND (status = 'success' OR result_count > 0)
            """,
                (source,),
            )

            result = cursor.fetchone()
            return result[0] if result and result[0] else None

    except Exception as e:
        logger.warning(f"Error getting last collection time for {source}: {e}")
        return None


def _get_collection_history_from_db(limit: int = 50) -> dict:
    """데이터베이스에서 수집 히스토리 조회

    Args:
        limit: 조회할 최대 레코드 수

    Returns:
        수집 히스토리 딕셔너리
    """
    try:
        db_path = "instance/blacklist.db"
        if not os.path.exists(db_path):
            return {"collections": [], "total": 0}

        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row  # dict-like access
            cursor = conn.cursor()

            # collection_logs 테이블 존재 확인
            cursor.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='collection_logs'
            """
            )

            if not cursor.fetchone():
                return {"collections": [], "total": 0}

            # 총 레코드 수 조회
            cursor.execute("SELECT COUNT(*) FROM collection_logs")
            total = cursor.fetchone()[0]

            # 최근 수집 기록 조회
            cursor.execute(
                """
                SELECT source, status, result_count, created_at, 
                       duration_seconds, error_message
                FROM collection_logs 
                ORDER BY created_at DESC 
                LIMIT ?
            """,
                (limit,),
            )

            collections = []
            for row in cursor.fetchall():
                collections.append(
                    {
                        "source": row["source"],
                        "status": row["status"],
                        "result_count": row["result_count"] or 0,
                        "created_at": row["created_at"],
                        "duration_seconds": row["duration_seconds"] or 0,
                        "error_message": row["error_message"],
                    }
                )

            return {"collections": collections, "total": total, "limit": limit}

    except Exception as e:
        logger.error(f"Error retrieving collection history: {e}")
        return {"collections": [], "total": 0, "error": str(e)}
