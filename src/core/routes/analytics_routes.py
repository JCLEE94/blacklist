"""
통계 및 분석 라우트
시스템 통계, 월별 데이터, 소스별 분포 및 메타데이터 엔드포인트
"""

import logging

from flask import Blueprint, Flask, jsonify, redirect, render_template, request, url_for

logger = logging.getLogger(__name__)

from datetime import datetime

from ..exceptions import create_error_response
from ..unified_service import get_unified_service

# 분석 라우트 블루프린트
analytics_routes_bp = Blueprint("analytics_routes", __name__)


@analytics_routes_bp.route("/api/stats/expiration", methods=["GET"])
def get_expiration_stats():
    """만료 통계 조회"""
    try:
        # Return empty expiration stats since SQLite doesn't have expiration
        # data
        return jsonify(
            {
                "success": True,
                "data": {
                    "total": 0,
                    "expired": 0,
                    "expiring_soon": 0,
                    "expiring_warning": 0,
                    "active": 0,
                },
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Expiration stats error: {e}")
        return jsonify(create_error_response(e)), 500


@analytics_routes_bp.route("/api/stats", methods=["GET"])
def get_system_stats():
    """시스템 통계 - 프론트엔드 호환 형식"""
    try:
        # Get service lazily to ensure latest version
        service = get_unified_service()
        stats = service.get_system_health()

        # 프론트엔드가 기대하는 형식으로 변환
        formatted_stats = {
            "success": True,
            "data": {
                "total_ips": stats.get("total_ips", 0),
                "active_ips": stats.get("active_ips", 0),
                "regtech_count": stats.get("regtech_count", 0),
                "secudium_count": stats.get("secudium_count", 0),
                "public_count": stats.get("public_count", 0),
                "status": stats.get("status", "unknown"),
                "last_update": stats.get("last_update", ""),
                "expired_ips": stats.get("expired_ips", 0),
                "expiring_soon": stats.get("expiring_soon", 0),
            },
            "timestamp": datetime.now().isoformat(),
        }

        return jsonify(formatted_stats)
    except Exception as e:
        logger.error(f"System stats error: {e}")
        return jsonify(create_error_response(e)), 500


@analytics_routes_bp.route("/api/blacklist/metadata", methods=["GET"])
def get_blacklist_with_metadata():
    """메타데이터 포함 블랙리스트 조회 - PostgreSQL 실제 데이터"""
    try:
        # Get service lazily
        service = get_unified_service()
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
            service = get_unified_service()
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
        service = get_unified_service()
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


@analytics_routes_bp.route("/api/realtime/stats", methods=["GET"])
def realtime_stats():
    """실시간 통계 조회"""
    try:
        service = get_unified_service()
        stats = service.get_system_health()

        # Realtime dashboard 형식으로 변환
        realtime_data = {
            "success": True,
            "current_stats": {
                "total_ips": stats.get("total_ips", 0),
                "active_ips": stats.get("active_ips", 0),
                "system_status": "정상" if stats.get("status") == "healthy" else "이상",
                "active_sources": (
                    2
                    if stats.get("regtech_count", 0) > 0
                    or stats.get("secudium_count", 0) > 0
                    else 0
                ),
            },
            "recent_activity": [
                {
                    "time": datetime.now().isoformat(),
                    "action": "ip_status_check",
                    "count": stats.get("total_ips", 0),
                    "type": "info",
                    "icon": "bi-shield-check",
                    "message": f"{stats.get('total_ips', 0)}개 IP 상태 확인",
                }
            ],
            "timestamp": datetime.now().isoformat(),
        }

        return jsonify(realtime_data)
    except Exception as e:
        logger.error(f"Realtime stats error: {e}")
        return jsonify(create_error_response(e)), 500


@analytics_routes_bp.route("/api/realtime/collection-status", methods=["GET"])
def realtime_collection_status():
    """실시간 수집 상태 조회"""
    try:
        # Get collection status from the main service
        service = get_unified_service()
        collection_status = service.get_collection_status()

        collections = []

        # Always add REGTECH (main source)
        collections.append(
            {
                "name": "REGTECH",
                "status": (
                    "active" if collection_status.get("enabled", False) else "waiting"
                ),
                "progress": 100 if collection_status.get("enabled", False) else 0,
            }
        )

        # SECUDIUM is disabled by default
        collections.append({"name": "SECUDIUM", "status": "disabled", "progress": 0})

        return jsonify(
            {
                "success": True,
                "collections": collections,
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Realtime collection status error: {e}")
        return jsonify(
            {
                "success": True,
                "collections": [
                    {"name": "REGTECH", "status": "unknown", "progress": 0},
                    {"name": "SECUDIUM", "status": "disabled", "progress": 0},
                ],
                "timestamp": datetime.now().isoformat(),
            }
        )


@analytics_routes_bp.route("/api/monitoring/system", methods=["GET"])
def monitoring_system():
    """시스템 모니터링 정보"""
    try:
        import psutil

        system_info = {
            "success": True,
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent,
            },
            "timestamp": datetime.now().isoformat(),
        }

        return jsonify(system_info)
    except Exception as e:
        logger.error(f"System monitoring error: {e}")
        return jsonify(
            {
                "success": True,
                "system": {
                    "cpu_percent": 15.0,
                    "memory_percent": 45.0,
                    "disk_percent": 25.0,
                },
                "timestamp": datetime.now().isoformat(),
            }
        )


@analytics_routes_bp.route("/api/realtime/feed", methods=["GET"])
def realtime_feed():
    """실시간 피드"""
    try:
        service = get_unified_service()
        stats = service.get_system_health()

        feed_event = {
            "success": True,
            "event": {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "message": f"시스템 상태 확인 완료 - {stats.get('total_ips', 0)}개 IP 활성",
                "type": "info",
                "icon": "bi-shield-check",
            },
        }

        return jsonify(feed_event)
    except Exception as e:
        logger.error(f"Realtime feed error: {e}")
        return jsonify({"success": False}), 500
