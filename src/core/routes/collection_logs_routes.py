"""Collection logs routes.

This module provides API endpoints for accessing and managing collection logs.
Includes real-time logs, collection history, and detailed log retrieval.
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
    """수집 로그 조회 - 의미있는 데이터 포함"""
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

        # unified_service에서 최근 로그 가져오기 - 의미있는 데이터 추출
        try:
            memory_logs = service.get_collection_logs(limit=50)
            for log_entry in memory_logs:
                details = log_entry.get("details", {})

                # 수집 날짜 포맷
                timestamp = log_entry.get("timestamp", "")
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                        date_str = dt.strftime("%m월 %d일")
                        time_str = dt.strftime("%H:%M")
                    except Exception:
                        date_str = "날짜 불명"
                        time_str = ""
                else:
                    date_str = "날짜 불명"
                    time_str = ""

                # 의미있는 메시지 생성
                source = log_entry.get("source", "unknown").upper()
                action = log_entry.get("action", "")

                # 기본 메시지 구성
                if "completed" in action:
                    icon = "✅"
                    status = "수집 완료"
                elif "started" in action:
                    icon = "🔄"
                    status = "수집 시작"
                elif "error" in action or "failed" in action:
                    icon = "❌"
                    status = "수집 실패"
                elif "enabled" in action:
                    icon = "🟢"
                    status = "수집 활성화"
                elif "disabled" in action:
                    icon = "🔴"
                    status = "수집 비활성화"
                else:
                    icon = "ℹ️"
                    status = action

                # 상세 정보 구성
                info_parts = []

                # 수집 날짜
                if details.get("start_date"):
                    start = details["start_date"]
                    end = details.get("end_date", start)
                    if start == end:
                        info_parts.append(f"📅 {start}")
                    else:
                        info_parts.append(f"📅 {start} ~ {end}")
                else:
                    info_parts.append(f"📅 {date_str}")

                # 수집 개수
                if details.get("ips_collected") is not None:
                    count = details["ips_collected"]
                    info_parts.append(f"📊 {count}개 수집")
                elif details.get("ip_count") is not None:
                    count = details["ip_count"]
                    info_parts.append(f"📊 {count}개 수집")
                elif details.get("total_ips") is not None:
                    count = details["total_ips"]
                    info_parts.append(f"📊 총 {count}개")

                # 중복 개수
                if details.get("duplicates") is not None:
                    dup_count = details["duplicates"]
                    info_parts.append(f"🔁 중복 {dup_count}개")
                elif details.get("duplicate_count") is not None:
                    dup_count = details["duplicate_count"]
                    info_parts.append(f"🔁 중복 {dup_count}개")
                elif (
                    details.get("new_ips") is not None
                    and details.get("total_ips") is not None
                ):
                    # 신규 IP로부터 중복 계산
                    total = details.get("total_ips", 0)
                    new = details.get("new_ips", 0)
                    dup_count = total - new
                    if dup_count > 0:
                        info_parts.append(f"🔁 중복 {dup_count}개")

                # 신규 IP
                if details.get("new_ips") is not None:
                    new_count = details["new_ips"]
                    info_parts.append(f"✨ 신규 {new_count}개")

                # 에러 정보
                if details.get("error"):
                    info_parts.append(f"⚠️ {details['error'][:50]}")

                # 최종 메시지 조합
                message = f"{icon} [{source}] {status}"
                if info_parts:
                    message += " | " + " | ".join(info_parts)

                formatted_log = {
                    "timestamp": log_entry.get("timestamp"),
                    "source": source,
                    "action": action,
                    "message": message,
                    "date": date_str,
                    "time": time_str,
                    "details": details,
                }

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


@collection_logs_bp.route("/api/collection/logs/detailed", methods=["GET"])
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


@collection_logs_bp.route("/api/collection/history", methods=["GET"])
def get_collection_history():
    """수집 실행 히스토리 조회 - 페이지네이션 지원"""
    try:
        # URL 파라미터 파싱
        limit = min(int(request.args.get("limit", 50)), 100)  # 최대 100개
        offset = max(int(request.args.get("offset", 0)), 0)

        # 최근 로그 조회 (limit + offset)
        total_logs = service.get_collection_logs(limit + offset)

        # 페이지네이션 적용
        paginated_logs = total_logs[offset : offset + limit] if total_logs else []

        # 히스토리 형태로 포맷팅
        history = []
        for log in paginated_logs:
            history_entry = {
                # Simple ID based on timestamp
                "id": hash(log.get("timestamp", "")),
                "timestamp": log.get("timestamp"),
                "source": log.get("source", "unknown").upper(),
                "action": log.get("action", "unknown"),
                "status": (
                    "success"
                    if "completed" in log.get("action", "")
                    else "running" if "started" in log.get("action", "") else "failed"
                ),
                "duration": None,  # Can't calculate without start/end times
                "ips_collected": log.get("details", {}).get("ips_collected")
                or log.get("details", {}).get("ip_count"),
                "details": log.get("details", {}),
                "message": log.get("message", ""),
            }
            history.append(history_entry)

        return jsonify(
            {
                "success": True,
                "history": history,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total": len(total_logs) if total_logs else 0,
                    "has_more": (
                        len(total_logs) > (offset + limit) if total_logs else False
                    ),
                },
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Collection history error: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "history": [],
                    "pagination": {
                        "limit": 0,
                        "offset": 0,
                        "total": 0,
                        "has_more": False,
                    },
                }
            ),
            500,
        )
