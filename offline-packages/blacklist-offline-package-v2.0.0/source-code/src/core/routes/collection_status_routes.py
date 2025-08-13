"""
수집 상태 관리 라우트
수집 상태 조회, 활성화/비활성화 API
"""

import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from ..container import get_container
from ..exceptions import create_error_response
from ..unified_service import get_unified_service

logger = logging.getLogger(__name__)

# 수집 상태 라우트 블루프린트
collection_status_bp = Blueprint("collection_status", __name__)

# 통합 서비스 인스턴스
service = get_unified_service()


@collection_status_bp.route("/api/collection/status", methods=["GET"])
def get_collection_status():
    """수집 상태 조회"""
    try:
        # 수집 상태 가져오기
        collection_status = service.get_collection_status()

        # 일일 수집 현황 가져오기
        daily_stats = service.get_daily_collection_stats()

        # 오늘 수집 통계 계산
        today = datetime.now().strftime("%Y-%m-%d")
        today_stats = None
        if daily_stats:
            today_stats = next(
                (stat for stat in daily_stats if stat.get("date") == today), None
            )

        # 시스템 통계 가져오기
        try:
            stats = service.get_system_health()
        except Exception as e:
            logger.warning(f"Failed to get system health: {e}")
            stats = {"total_ips": 0, "active_ips": 0}

        # 최근 로그 가져오기
        try:
            recent_logs = service.get_collection_logs(limit=10)
        except Exception as e:
            logger.warning(f"Failed to get collection logs: {e}")
            recent_logs = []

        return jsonify(
            {
                "enabled": service.collection_enabled,
                "status": "active" if service.collection_enabled else "inactive",
                "stats": {
                    "total_ips": stats.get("total_ips", 0),
                    "active_ips": stats.get("active_ips", 0),
                    "today_collected": today_stats.get("count", 0)
                    if today_stats
                    else 0,
                    "today_sources": (
                        today_stats.get("sources", {}) if today_stats else {}
                    ),
                },
                "daily_collection": {
                    "today": today_stats.get("count", 0) if today_stats else 0,
                    "recent_days": daily_stats[:7] if daily_stats else [],  # 최근 7일
                },
                "sources": collection_status.get("sources", {}),
                "logs": recent_logs,
                "last_collection": collection_status.get("last_updated"),
                "message": '수집 상태: {"활성화" if service.collection_enabled else "비활성화"}',
            }
        )
    except Exception as e:
        logger.error(f"Collection status error: {e}")
        return (
            jsonify(
                {
                    "enabled": False,
                    "status": "error",
                    "error": str(e),
                    "stats": {"total_ips": 0, "active_ips": 0, "today_collected": 0},
                    "daily_collection": {"today": 0, "recent_days": []},
                    "sources": {},
                }
            ),
            500,
        )


@collection_status_bp.route("/api/collection/enable", methods=["POST"])
def enable_collection():
    """수집 활성화 - 선택적으로 기존 데이터 클리어"""
    try:
        container = get_container()
        collection_manager = container.get("collection_manager")

        if not collection_manager:
            return (
                jsonify(
                    {"success": False, "error": "Collection manager not available"}
                ),
                500,
            )

        # 요청에서 clear_data 파라미터 확인
        try:
            data = request.get_json() or {}
        except Exception as e:
            data = {}
        clear_data = data.get("clear_data", False)

        # 수집 활성화 (선택적 데이터 클리어)
        result = collection_manager.enable_collection(clear_data_first=clear_data)

        # UnifiedService의 상태도 동기화
        service.collection_enabled = True

        # 로그 추가
        service.add_collection_log(
            source="system",
            action="collection_enabled",
            details={
                "enabled_by": "manual",
                "cleared_data": result.get("cleared_data", False),
                "timestamp": datetime.now().isoformat(),
            },
        )

        return jsonify(
            {
                "success": True,
                "message": result.get("message", "수집이 활성화되었습니다."),
                "collection_enabled": True,
                "cleared_data": result.get("cleared_data", False),
                "sources": result.get("sources", {}),
            }
        )
    except Exception as e:
        logger.error(f"Enable collection error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@collection_status_bp.route("/api/collection/disable", methods=["POST"])
def disable_collection():
    """수집 비활성화"""
    try:
        container = get_container()
        collection_manager = container.get("collection_manager")

        if not collection_manager:
            return (
                jsonify(
                    {"success": False, "error": "Collection manager not available"}
                ),
                500,
            )

        # 수집 비활성화
        result = collection_manager.disable_collection()

        # UnifiedService의 상태도 동기화
        service.collection_enabled = False

        # 로그 추가
        service.add_collection_log(
            source="system",
            action="collection_disabled",
            details={"disabled_by": "manual", "timestamp": datetime.now().isoformat()},
        )

        return jsonify(
            {
                "success": True,
                "message": result.get("message", "수집이 비활성화되었습니다."),
                "collection_enabled": result.get("enabled", service.collection_enabled),
                "warning": result.get("warning"),
                "sources": result.get("sources", {}),
            }
        )
    except Exception as e:
        logger.error(f"Disable collection error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@collection_status_bp.route("/api/collection/statistics", methods=["GET"])
def collection_statistics():
    """수집 통계 상세 정보"""
    try:
        # 날짜별 수집 통계
        daily_stats = service.get_daily_collection_stats()

        # 소스별 통계
        source_stats = service.get_source_statistics()

        return jsonify(
            {
                "success": True,
                "daily_stats": daily_stats,
                "source_stats": source_stats,
                "summary": {
                    "total_days_collected": len(daily_stats),
                    "total_ips": sum(day.get("count", 0) for day in daily_stats),
                    "regtech_total": source_stats.get("regtech", {}).get("total", 0),
                    "secudium_total": source_stats.get("secudium", {}).get("total", 0),
                },
            }
        )
    except Exception as e:
        logger.error(f"Collection statistics error: {e}")
        return jsonify(create_error_response(e)), 500


@collection_status_bp.route("/api/collection/intervals", methods=["GET"])
def get_collection_intervals():
    """수집 간격 설정 조회"""
    try:
        intervals = service.get_collection_intervals()

        return jsonify(
            {
                "success": True,
                "intervals": intervals,
                "regtech_days": intervals.get("regtech_days", 90),  # 3개월
                "secudium_days": intervals.get("secudium_days", 3),  # 3일
            }
        )
    except Exception as e:
        logger.error(f"Get collection intervals error: {e}")
        return jsonify(create_error_response(e)), 500


@collection_status_bp.route("/api/collection/intervals", methods=["POST"])
def update_collection_intervals():
    """수집 간격 설정 업데이트"""
    try:
        data = request.get_json() or {}

        regtech_days = data.get("regtech_days", 90)
        secudium_days = data.get("secudium_days", 3)

        # 유효성 검사
        if not (1 <= regtech_days <= 365):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "REGTECH 수집 간격은 1-365일 사이여야 합니다.",
                    }
                ),
                400,
            )

        if not (1 <= secudium_days <= 30):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "SECUDIUM 수집 간격은 1-30일 사이여야 합니다.",
                    }
                ),
                400,
            )

        service.update_collection_intervals(regtech_days, secudium_days)

        return jsonify(
            {
                "success": True,
                "message": "수집 간격이 업데이트되었습니다.",
                "intervals": {
                    "regtech_days": regtech_days,
                    "secudium_days": secudium_days,
                },
            }
        )
    except Exception as e:
        logger.error(f"Update collection intervals error: {e}")
        return jsonify(create_error_response(e)), 500
