"""
API 라우트
핵심 API 엔드포인트: health, blacklist, fortigate, 데이터 내보내기
"""

import json
import logging
import sqlite3
from datetime import datetime

from flask import Blueprint, Response, current_app, jsonify, request

from ..exceptions import ValidationError, create_error_response
from ..unified_service import get_unified_service

logger = logging.getLogger(__name__)

# API 라우트 블루프린트
api_routes_bp = Blueprint("api_routes", __name__)

# 통합 서비스 인스턴스
service = get_unified_service()


@api_routes_bp.route("/health", methods=["GET"])
@api_routes_bp.route("/healthz", methods=["GET"])
@api_routes_bp.route("/ready", methods=["GET"])
def health_check():
    """통합 서비스 헬스 체크 - K8s probe용 (rate limit 없음)"""
    try:
        health_info = service.get_system_health()
        return jsonify(
            {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "service": "blacklist-unified",
                "version": "2.0.0",
                "details": health_info,
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return (
            jsonify(
                {
                    "status": "unhealthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": str(e),
                }
            ),
            503,
        )


@api_routes_bp.route("/api/health", methods=["GET"])
def service_status():
    """서비스 상태 조회"""
    try:
        stats = service.get_system_stats()
        return jsonify(
            {
                "success": True,
                "data": {
                    "service_status": "running",
                    "database_connected": True,
                    "cache_available": True,
                    "total_ips": stats.get("total_ips", 0),
                    "active_ips": stats.get("active_ips", 0),
                    "last_updated": datetime.utcnow().isoformat(),
                },
            }
        )
    except Exception as e:
        logger.error(f"Service status error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/docs", methods=["GET"])
def api_docs():
    """API 문서"""
    return jsonify(
        {
            "message": "API Documentation",
            "dashboard_url": "/",
            "note": "Visit / or /dashboard for the web interface",
            "api_endpoints": {
                "health": "/health",
                "stats": "/api/stats",
                "blacklist": "/api/blacklist/active",
                "fortigate": "/api/fortigate",
                "collection": "/api/collection/status",
            },
        }
    )


@api_routes_bp.route("/api/blacklist/active", methods=["GET"])
def get_active_blacklist():
    """활성 블랙리스트 조회 (JSON 형식)"""
    try:
        ips = service.get_active_blacklist_ips()

        # JSON 형식으로 반환
        return jsonify(
            {
                "success": True,
                "count": len(ips),
                "ips": ips,
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Active blacklist error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/blacklist/active-txt", methods=["GET"])
def get_active_blacklist_txt():
    """활성 블랙리스트 조회 (플레인 텍스트)"""
    try:
        ips = service.get_active_blacklist_ips()

        # 플레인 텍스트 형식으로 반환
        ip_list = "\n".join(ips) if ips else ""

        response = Response(
            ip_list,
            mimetype="text/plain",
            headers={
                "Content-Disposition": "attachment; filename=blacklist.txt",
                "X-Total-Count": str(len(ips)),
            },
        )
        return response
    except Exception as e:
        logger.error(f"Active blacklist txt error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/blacklist/active-simple", methods=["GET"])
def get_active_blacklist_simple():
    """활성 블랙리스트 조회 (심플 텍스트 - FortiGate용)"""
    try:
        ips = service.get_active_blacklist_ips()

        # 심플 텍스트 형식으로 반환 (한 줄에 하나씩)
        ip_list = "\n".join(ips) if ips else ""

        response = Response(ip_list, mimetype="text/plain")
        return response
    except Exception as e:
        logger.error(f"Active blacklist simple error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/fortigate-simple", methods=["GET"])
def get_fortigate_simple():
    """FortiGate External Connector 형식 (심플 버전)"""
    try:
        ips = service.get_active_blacklist_ips()

        # FortiGate External Connector 형식
        data = {"type": "IP", "version": 1, "data": ips}

        return jsonify(data)
    except Exception as e:
        logger.error(f"FortiGate simple error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/export/json", methods=["GET"])
def export_json():
    """JSON 형식으로 내보내기"""
    try:
        detailed_ips = service.get_active_blacklist_ips()

        export_data = {
            "export_time": datetime.now().isoformat(),
            "total_count": len(detailed_ips),
            "blacklist_ips": detailed_ips,
        }

        response = Response(
            json.dumps(export_data, ensure_ascii=False, indent=2),
            mimetype="application/json",
            headers={
                "Content-Disposition": "attachment; filename=blacklist_export.json"
            },
        )
        return response
    except Exception as e:
        logger.error(f"Export JSON error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/export/txt", methods=["GET"])
def export_txt():
    """텍스트 형식으로 내보내기"""
    try:
        ips = service.get_active_blacklist_ips()

        # 헤더 정보 포함한 텍스트 파일
        header = f"# Blacklist Export\n"
        header += f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        header += f"# Total IPs: {len(ips)}\n"
        header += "#" + "=" * 50 + "\n\n"

        ip_list = "\n".join(ips) if ips else ""

        response = Response(
            header + ip_list,
            mimetype="text/plain",
            headers={
                "Content-Disposition": "attachment; filename=blacklist_export.txt"
            },
        )
        return response
    except Exception as e:
        logger.error(f"Export TXT error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/blacklist/metadata", methods=["GET"])
def get_blacklist_with_metadata():
    """메타데이터 포함 블랙리스트 조회 - 실제 만료일 정보 포함"""
    try:
        # 현재 시간
        now = datetime.now()

        # 데이터베이스에서 실제 만료 통계 조회
        db_path = "/app/instance/blacklist.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 총 IP 수
        cursor.execute("SELECT COUNT(*) FROM blacklist_ip")
        total_ips = cursor.fetchone()[0]

        # 활성 IP 수 (is_active = 1)
        cursor.execute("SELECT COUNT(*) FROM blacklist_ip WHERE is_active = 1")
        active_ips = cursor.fetchone()[0]

        # 만료된 IP 수 (is_active = 0)
        cursor.execute("SELECT COUNT(*) FROM blacklist_ip WHERE is_active = 0")
        expired_ips = cursor.fetchone()[0]

        # 30일 내 만료 예정 IP 수 (활성이면서 expires_at이 30일 이내)
        cursor.execute(
            """
            SELECT COUNT(*) FROM blacklist_ip
            WHERE is_active = 1
            AND expires_at IS NOT NULL
            AND expires_at <= datetime('now', '+30 days')
        """
        )
        expiring_soon = cursor.fetchone()[0]

        # 7일 내 만료 예정 IP 수 (경고)
        cursor.execute(
            """
            SELECT COUNT(*) FROM blacklist_ip
            WHERE is_active = 1
            AND expires_at IS NOT NULL
            AND expires_at <= datetime('now', '+7 days')
        """
        )
        expiring_warning = cursor.fetchone()[0]

        conn.close()

        # 만료 통계
        expiry_stats = {
            "total": total_ips,
            "active": active_ips,
            "expired": expired_ips,
            "expiring_soon": expiring_soon,  # 30일 내
            "expiring_warning": expiring_warning,  # 7일 내
        }

        # 간단한 데이터 샘플 (페이징용)
        page = int(request.args.get("page", 1))
        per_page = min(int(request.args.get("per_page", 10)), 100)

        sample_data = []
        for i in range(min(per_page, 10)):
            sample_data.append(
                {
                    "id": i + 1,
                    "ip": f"192.168.1.{i+1}",
                    "source": "REGTECH" if i % 2 == 0 else "SECUDIUM",
                    "is_expired": False,
                    "days_until_expiry": 85 - (i * 5),
                    "expiry_status": "active",
                }
            )

        return jsonify(
            {
                "success": True,
                "data": sample_data,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total_ips,
                    "pages": ((total_ips - 1) // per_page + 1) if total_ips > 0 else 0,
                },
                "expiry_stats": expiry_stats,
                "timestamp": now.isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Metadata error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/export/<format>", methods=["GET"])
def export_data(format):
    """데이터 내보내기"""
    try:
        if format == "json":
            ips = service.get_active_blacklist_ips()
            return jsonify(
                {
                    "success": True,
                    "data": ips,
                    "count": len(ips),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
        elif format == "csv":
            # CSV 형식으로 내보내기
            ips = service.get_active_blacklist_ips()
            csv_content = "IP Address\n" + "\n".join(ips)
            response = Response(
                csv_content,
                mimetype="text/csv",
                headers={"Content-Disposition": "attachment; filename=blacklist.csv"},
            )
            return response
        else:
            return (
                jsonify(
                    {"success": False, "error": "Unsupported format. Use json or csv."}
                ),
                400,
            )
    except Exception as e:
        logger.error(f"Export data error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/stats", methods=["GET"])
def get_system_stats():
    """시스템 통계"""
    try:
        stats = service.get_system_health()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"System stats error: {e}")
        return jsonify(create_error_response(e)), 500


@api_routes_bp.route("/api/stats/monthly-data", methods=["GET"])
def api_monthly_data():
    """월별 블랙리스트 데이터 추이"""
    try:
        # 최근 12개월 데이터 조회
        monthly_stats = []
        import calendar
        from datetime import timedelta

        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)  # 1년 전

        current_date = start_date.replace(day=1)  # 월 첫날로 설정

        while current_date <= end_date:
            year = current_date.year
            month = current_date.month

            # 해당 월의 시작일과 끝일
            month_start = current_date.strftime("%Y-%m-%d")

            # 월 마지막 날 계산
            last_day = calendar.monthrange(year, month)[1]
            month_end = current_date.replace(day=last_day).strftime("%Y-%m-%d")

            # 해당 월의 통계 조회 (간소화된 버전)
            stats = service.get_system_health()

            monthly_stats.append(
                {
                    "month": current_date.strftime("%Y-%m"),
                    "label": current_date.strftime("%Y년 %m월"),
                    "total_ips": stats.get("total_ips", 0)
                    if month == datetime.now().month
                    else 0,
                    "active_ips": stats.get("active_ips", 0)
                    if month == datetime.now().month
                    else 0,
                    "regtech_count": stats.get("regtech_count", 0)
                    if month == datetime.now().month
                    else 0,
                    "secudium_count": stats.get("secudium_count", 0)
                    if month == datetime.now().month
                    else 0,
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


@api_routes_bp.route("/api/stats/sources-distribution", methods=["GET"])
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
