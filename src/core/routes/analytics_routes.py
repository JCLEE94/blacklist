"""
통계 및 분석 라우트
시스템 통계, 월별 데이터, 소스별 분포 및 메타데이터 엔드포인트
"""

import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from ..exceptions import create_error_response
from ..unified_service import get_unified_service

logger = logging.getLogger(__name__)

# 분석 라우트 블루프린트
analytics_routes_bp = Blueprint("analytics_routes", __name__)

# 통합 서비스 인스턴스
service = get_unified_service()


@analytics_routes_bp.route("/api/stats", methods=["GET"])
def get_system_stats():
    """시스템 통계"""
    try:
        stats = service.get_system_health()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"System stats error: {e}")
        return jsonify(create_error_response(e)), 500


@analytics_routes_bp.route("/api/blacklist/metadata", methods=["GET"])
def get_blacklist_with_metadata():
    """메타데이터 포함 블랙리스트 조회 - PostgreSQL 실제 데이터"""
    try:
        # 통계 서비스에서 실제 PostgreSQL 데이터 조회
        stats = service.get_statistics()

        # 페이징 정보
        page = int(request.args.get("page", 1))
        per_page = min(int(request.args.get("per_page", 10)), 100)

        # 실제 PostgreSQL에서 IP 데이터 조회
        active_ips = service.get_active_ips()

        # 실제 IP 데이터를 페이징 처리
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paged_ips = active_ips[start_idx:end_idx]

        # 만료 통계 (실제 데이터 기반)
        expiry_stats = {
            "total": stats.get("total_ips", 0),
            "active": stats.get("active_ips", 0),
            "expired": stats.get("expired_ips", 0),
            "expiring_soon": 0,  # PostgreSQL 스키마에 만료일 없음
            "expiring_warning": 0,  # PostgreSQL 스키마에 만료일 없음
        }

        return jsonify(
            {
                "success": True,
                "data": [
                    {
                        "id": idx + start_idx + 1,
                        "ip": ip_data.get("ip_address", ""),
                        "source": ip_data.get("source", "UNKNOWN"),
                        "is_expired": not ip_data.get("is_active", True),
                        "days_until_expiry": None,  # PostgreSQL 스키마에 만료일 없음
                        "expiry_status": (
                            "active" if ip_data.get("is_active", True) else "expired"
                        ),
                    }
                    for idx, ip_data in enumerate(paged_ips)
                ],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": len(active_ips),
                    "pages": (
                        ((len(active_ips) - 1) // per_page + 1) if active_ips else 0
                    ),
                },
                "expiry_stats": expiry_stats,
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Metadata error: {e}")
        return jsonify(create_error_response(e)), 500


@analytics_routes_bp.route("/api/stats/monthly", methods=["GET"])
@analytics_routes_bp.route("/api/stats/monthly-data", methods=["GET"])  # 하위 호환성
def api_monthly_data():
    """월별 블랙리스트 데이터 추이"""
    try:
        # 최근 12개월 데이터 조회
        monthly_stats = []
        # import calendar  # 현재 미사용
        from datetime import timedelta

        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)  # 1년 전

        current_date = start_date.replace(day=1)  # 월 첫날로 설정

        while current_date <= end_date:
            year = current_date.year
            month = current_date.month

            # 해당 월의 시작일과 끝일
            current_date.strftime("%Y-%m-%d")

            # 월 마지막 날 계산 (사용되지 않음)
            # last_day = calendar.monthrange(year, month)[1]
            # month_end = current_date.replace(day=last_day).strftime("%Y-%m-%d")

            # 해당 월의 통계 조회 (간소화된 버전)
            stats = service.get_system_health()

            monthly_stats.append(
                {
                    "month": current_date.strftime("%Y-%m"),
                    "label": current_date.strftime("%Y년 %m월"),
                    "total_ips": (
                        stats.get("total_ips", 0)
                        if month == datetime.now().month
                        else 0
                    ),
                    "active_ips": (
                        stats.get("active_ips", 0)
                        if month == datetime.now().month
                        else 0
                    ),
                    "regtech_count": (
                        stats.get("regtech_count", 0)
                        if month == datetime.now().month
                        else 0
                    ),
                    "secudium_count": (
                        stats.get("secudium_count", 0)
                        if month == datetime.now().month
                        else 0
                    ),
                }
            )

            # 다음 월로 이동
            if month == 12:
                current_date = current_date.replace(year=year + 1, month=1)
            else:
                current_date = current_date.replace(month=month + 1)

        return jsonify(
            {
                "success": True,
                "data": monthly_stats,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Monthly data error: {e}")
        return jsonify({"success": False, "error": str(e), "data": []}), 500


@analytics_routes_bp.route("/api/stats/sources-distribution", methods=["GET"])
def api_sources_distribution():
    """소스별 분포 데이터"""
    try:
        stats = service.get_system_health()

        sources_data = []
        total_ips = stats.get("total_ips", 0)

        if stats.get("regtech_count", 0) > 0:
            sources_data.append(
                {
                    "source": "REGTECH",
                    "count": stats["regtech_count"],
                    "percentage": (
                        round((stats["regtech_count"] / total_ips) * 100, 1)
                        if total_ips > 0
                        else 0
                    ),
                }
            )

        if stats.get("secudium_count", 0) > 0:
            sources_data.append(
                {
                    "source": "SECUDIUM",
                    "count": stats["secudium_count"],
                    "percentage": (
                        round((stats["secudium_count"] / total_ips) * 100, 1)
                        if total_ips > 0
                        else 0
                    ),
                }
            )

        if stats.get("public_count", 0) > 0:
            sources_data.append(
                {
                    "source": "PUBLIC",
                    "count": stats["public_count"],
                    "percentage": (
                        round((stats["public_count"] / total_ips) * 100, 1)
                        if total_ips > 0
                        else 0
                    ),
                }
            )

        return jsonify(
            {
                "success": True,
                "data": sources_data,
                "total_ips": total_ips,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Sources distribution error: {e}")
        return jsonify({"success": False, "error": str(e), "data": []}), 500
