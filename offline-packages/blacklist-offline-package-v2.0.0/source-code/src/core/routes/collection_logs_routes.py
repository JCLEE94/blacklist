"""
수집 로그 라우트
수집 로그 조회, 실시간 로그 API
"""

import logging
import os
from datetime import datetime

from flask import Blueprint, jsonify, request

from ..exceptions import create_error_response
from ..unified_service import get_unified_service

logger = logging.getLogger(__name__)

# 수집 로그 라우트 블루프린트
collection_logs_bp = Blueprint("collection_logs", __name__)

# 통합 서비스 인스턴스
service = get_unified_service()


@collection_logs_bp.route("/api/collection/logs", methods=["GET"])
def api_collection_logs():
    """수집 로그 조회 (지속성 있는)"""
    try:
        # 로그 파일 경로들
        log_paths = ["/app/logs/collection.log", "/app/instance/collection_history.log"]

        logs = []

        # 각 로그 파일에서 수집 관련 로그 추출
        for log_path in log_paths:
            if os.path.exists(log_path):
                try:
                    with open(log_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()[-100:]  # 최근 100줄
                        for line in lines:
                            if any(
                                keyword in line.lower()
                                for keyword in [
                                    "collection",
                                    "regtech",
                                    "secudium",
                                    "수집",
                                    "완료",
                                ]
                            ):
                                logs.append(
                                    {
                                        "timestamp": (
                                            line.split(" - ")[0]
                                            if " - " in line
                                            else datetime.now().isoformat()
                                        ),
                                        "message": line.strip(),
                                        "source": "file",
                                    }
                                )
                except Exception as e:
                    logger.warning(f"Failed to read log file {log_path}: {e}")

        # unified_service에서 최근 로그 가져오기
        try:
            memory_logs = service.get_collection_logs(limit=50)
            for log_entry in memory_logs:
                formatted_log = {
                    "timestamp": log_entry.get("timestamp"),
                    "source": log_entry.get("source", "unknown"),
                    "action": log_entry.get("action", ""),
                    "message": "[{log_entry.get('source')}] {log_entry.get('action')}",
                }

                # 상세 정보 추가
                details = log_entry.get("details", {})
                if details:
                    if details.get("is_daily"):
                        formatted_log["message"] += " (일일 수집)"
                    if details.get("ips_collected") is not None:
                        formatted_log[
                            "message"
                        ] += " - {details['ips_collected']}개 IP 수집"
                    if details.get("start_date"):
                        formatted_log[
                            "message"
                        ] += " - 기간: {details['start_date']}~{details.get('end_date', details['start_date'])}"

                logs.append(formatted_log)
        except Exception as e:
            logger.warning(f"Failed to get memory logs: {e}")

        # 시간순 정렬
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return jsonify(
            {
                "success": True,
                "logs": logs[:100],  # 최대 100개
                "count": len(logs),
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Collection logs error: {e}")
        return jsonify({"success": False, "error": str(e), "logs": []}), 500


@collection_logs_bp.route("/api/collection/logs/realtime", methods=["GET"])
def get_realtime_logs():
    """실시간 수집 로그 조회 - 최근 20개"""
    try:
        # 최근 20개 로그만 조회
        logs = service.get_collection_logs(20)

        # 메시지만 간단하게 추출
        simple_logs = []
        for log in logs:
            simple_logs.append(
                {
                    "time": (
                        log.get("timestamp", "").split("T")[1][:8]
                        if "T" in log.get("timestamp", "")
                        else ""
                    ),  # HH:MM:SS만
                    "message": log.get("message", ""),
                    "source": log.get("source", "").upper(),
                }
            )

        return jsonify(
            {
                "success": True,
                "logs": simple_logs,
                "count": len(simple_logs),
                "last_update": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Realtime logs error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@collection_logs_bp.route("/api/collection/logs", methods=["GET"])
def get_collection_logs():
    """수집 로그 조회 - 상세 정보 포함"""
    try:
        # 최근 로그 조회 (기본 50개, 최대 200개)
        limit = min(int(request.args.get("limit", 50)), 200)
        logs = service.get_collection_logs(limit)

        # 로그를 읽기 쉽게 포맷팅
        formatted_logs = []
        for log in logs:
            formatted_log = {
                "timestamp": log.get("timestamp"),
                "source": log.get("source"),
                "action": log.get("action"),
                "message": log.get("message"),
                "details": log.get("details", {}),
            }

            # 상세 정보 추가
            details = log.get("details", {})
            if details.get("ip_count"):
                formatted_log["ip_count"] = details["ip_count"]
            if details.get("error"):
                formatted_log["error"] = details["error"]

            formatted_logs.append(formatted_log)

        return jsonify(
            {
                "success": True,
                "logs": formatted_logs,
                "count": len(formatted_logs),
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Collection logs error: {e}")
        return jsonify(create_error_response(e)), 500
