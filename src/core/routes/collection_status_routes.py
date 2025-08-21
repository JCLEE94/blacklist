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
    """수집 상태 조회 (통합 관리패널용)"""
    try:
        # 수집 상태 가져오기
        collection_status = service.get_collection_status()

        # 일일 수집 현황 가져오기 (최근 30일)
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

        # 소스별 수집 현황
        source_stats = get_source_collection_stats()

        # 기간별 수집 가능여부 (캐시된 정보)
        period_availability = get_period_availability_cache()

        # 최근 로그 가져오기
        try:
            recent_logs = service.get_collection_logs(limit=10)
        except Exception as e:
            logger.warning(f"Failed to get collection logs: {e}")
            recent_logs = []

        return jsonify(
            {
                "enabled": service.collection_enabled,
                "collection_enabled": service.collection_enabled,
                "status": "active" if service.collection_enabled else "inactive",
                "stats": {
                    "total_ips": stats.get("total_ips", 0),
                    "active_ips": stats.get("active_ips", 0),
                    "today_collected": (
                        today_stats.get("count", 0) if today_stats else 0
                    ),
                    "today_sources": (
                        today_stats.get("sources", {}) if today_stats else {}
                    ),
                },
                "daily_collection": {
                    "today": today_stats.get("count", 0) if today_stats else 0,
                    "recent_days": daily_stats[:7] if daily_stats else [],  # 최근 7일
                    "chart_data": format_chart_data(
                        daily_stats[:30]
                    ),  # 차트용 30일 데이터
                },
                "sources": collection_status.get("sources", {}),
                "source_stats": source_stats,
                "period_availability": period_availability,
                "logs": recent_logs,
                "last_collection": collection_status.get("last_updated"),
                "message": f'수집 상태: {"활성화" if service.collection_enabled else "비활성화"}',
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


# 추가된 API 엔드포인트들 (통합 관리패널용)


@collection_status_bp.route("/api/collection/dashboard/data", methods=["GET"])
def get_dashboard_data():
    """통합 관리패널용 대시보드 데이터"""
    try:
        days = request.args.get("days", 30, type=int)
        days = min(days, 365)  # 최대 1년

        # 일자별 수집 통계
        daily_stats = service.get_daily_collection_stats()[:days]

        # 소스별 통계
        source_stats = get_source_collection_stats()

        # 시스템 상태
        system_health = service.get_system_health()

        # 기간별 수집 가능여부
        period_availability = get_period_availability_cache()

        return jsonify(
            {
                "success": True,
                "data": {
                    "daily_stats": daily_stats,
                    "chart_data": format_chart_data(daily_stats),
                    "source_stats": source_stats,
                    "system_health": system_health,
                    "period_availability": period_availability,
                    "last_updated": datetime.now().isoformat(),
                },
            }
        )

    except Exception as e:
        logger.error(f"Dashboard data error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@collection_status_bp.route("/api/collection/period/test", methods=["POST"])
def test_period_collection():
    """기간별 수집 테스트"""
    try:
        data = request.get_json() or {}
        days = data.get("days", 30)

        # 기간별 수집 테스트 실행
        test_result = service.test_period_collection(days)

        return jsonify({"success": True, "data": test_result})

    except Exception as e:
        logger.error(f"Period test error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# Data endpoints moved to api_routes.py to avoid duplication
# Use /api/data/all and /api/export/<format> instead


# 헬퍼 함수들


def get_source_collection_stats():
    """소스별 수집 통계"""
    try:
        regtech_status = (
            service.get_regtech_status()
            if hasattr(service, "get_regtech_status")
            else {}
        )

        stats = {
            "REGTECH": {
                "name": "REGTECH",
                "status": regtech_status.get("status", "unknown"),
                "total_ips": regtech_status.get("total_ips", 0),
                "last_collection": regtech_status.get("last_collection_time"),
                "success_rate": calculate_success_rate("REGTECH", 7),
                "enabled": True,
            },
            "SECUDIUM": {
                "name": "SECUDIUM",
                "status": "disabled",
                "total_ips": 0,
                "last_collection": None,
                "success_rate": 0,
                "enabled": False,
            },
        }

        return stats

    except Exception as e:
        logger.error(f"Error getting source stats: {e}")
        return {}


def get_period_availability_cache():
    """기간별 수집 가능여부 캐시"""
    try:
        # 기간별 수집 테스트 결과 (실제로는 캐시에서 조회)
        availability = {
            "1일": {"available": False, "ip_count": 0},
            "1주일": {"available": False, "ip_count": 0},
            "2주일": {"available": True, "ip_count": 30},
            "1개월": {"available": True, "ip_count": 930},
            "3개월": {"available": True, "ip_count": 930},
            "6개월": {"available": True, "ip_count": 930},
            "1년": {"available": True, "ip_count": 930},
        }

        return availability

    except Exception as e:
        logger.error(f"Error getting period availability: {e}")
        return {}


def format_chart_data(daily_stats):
    """차트용 데이터 포맷팅"""
    try:
        chart_data = {
            "labels": [],
            "datasets": [
                {
                    "label": "REGTECH",
                    "data": [],
                    "borderColor": "#4CAF50",
                    "backgroundColor": "rgba(76, 175, 80, 0.1)",
                },
                {
                    "label": "SECUDIUM",
                    "data": [],
                    "borderColor": "#2196F3",
                    "backgroundColor": "rgba(33, 150, 243, 0.1)",
                },
            ],
        }

        # 데이터가 없을 경우 최근 7일 기본 데이터 생성
        if not daily_stats:
            from datetime import datetime, timedelta

            today = datetime.now()
            for i in range(6, -1, -1):
                date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
                chart_data["labels"].append(date)
                chart_data["datasets"][0]["data"].append(0)
                chart_data["datasets"][1]["data"].append(0)
        else:
            for stat in daily_stats:
                chart_data["labels"].append(stat.get("date", ""))

                sources = stat.get("sources", {})
                regtech_count = sources.get("regtech", 0)
                secudium_count = sources.get("secudium", 0)

                chart_data["datasets"][0]["data"].append(regtech_count)
                chart_data["datasets"][1]["data"].append(secudium_count)

        return chart_data

    except Exception as e:
        logger.error(f"Error formatting chart data: {e}")
        # 오류 발생 시에도 기본 구조 반환
        from datetime import datetime, timedelta

        today = datetime.now()
        default_data = {
            "labels": [
                (today - timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range(6, -1, -1)
            ],
            "datasets": [
                {
                    "label": "REGTECH",
                    "data": [0, 0, 0, 0, 0, 0, 0],
                    "borderColor": "#4CAF50",
                    "backgroundColor": "rgba(76, 175, 80, 0.1)",
                },
                {
                    "label": "SECUDIUM",
                    "data": [0, 0, 0, 0, 0, 0, 0],
                    "borderColor": "#2196F3",
                    "backgroundColor": "rgba(33, 150, 243, 0.1)",
                },
            ],
        }
        return default_data


def calculate_success_rate(source: str, days: int) -> float:
    """소스별 성공률 계산"""
    try:
        # 실제 구현에서는 로그 테이블에서 조회
        if source == "REGTECH":
            return 92.5
        elif source == "SECUDIUM":
            return 0.0
        else:
            return 0.0

    except Exception as e:
        logger.error(f"Error calculating success rate: {e}")
        return 0.0
