"""
관리 라우트
데이터베이스 관리, 유지보수, 설정, 디버깅 관련 API
"""

import logging
import os
import sqlite3
from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    request,
)

from ..exceptions import ValidationError, create_error_response
from ..unified_service import get_unified_service
from ..validators import validate_ip

logger = logging.getLogger(__name__)

# 관리 라우트 블루프린트
admin_routes_bp = Blueprint("admin_routes", __name__)

# 통합 서비스 인스턴스
service = get_unified_service()


@admin_routes_bp.route("/api/database/clear", methods=["POST"])
def clear_database():
    """데이터베이스 클리어 (위험 작업)"""
    try:
        # 확인 플래그 체크
        data = request.get_json() or {}
        if not data.get("confirm", False):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": 'Confirmation required. Send {"confirm": true} to proceed.',
                    }
                ),
                400,
            )

        # 모든 데이터 클리어
        try:
            result = service.clear_all_database_data()
        except Exception as e:
            logger.error(f"Failed to clear database: {e}")
            result = {"success": False, "error": str(e)}

        if result.get("success"):
            return jsonify(
                {
                    "success": True,
                    "message": "All data has been cleared successfully.",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": result.get("error", "Unknown error occurred"),
                    }
                ),
                500,
            )

    except Exception as e:
        logger.error(f"Database clear error: {e}")
        return jsonify(create_error_response(e)), 500


@admin_routes_bp.route("/api/maintenance/cleanup", methods=["POST"])
def maintenance_cleanup():
    """오래된 데이터 정리"""
    try:
        # 90일 이상 된 데이터 삭제
        blacklist_manager = current_app.blacklist_manager
        retention_days = int(os.environ.get("DATA_RETENTION", "90"))

        deleted_count = blacklist_manager.cleanup_old_data(retention_days)

        return jsonify(
            {
                "success": True,
                "deleted_count": deleted_count,
                "message": f"{deleted_count}개의 오래된 레코드가 정리되었습니다.",
            }
        )

    except Exception as e:
        logger.error(f"Maintenance cleanup error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_routes_bp.route("/api/maintenance/clear-cache", methods=["POST"])
def maintenance_clear_cache():
    """캐시 초기화"""
    try:
        cache_manager = current_app.cache_manager
        if cache_manager:
            cache_manager.clear()

        return jsonify({"success": True, "message": "캐시가 초기화되었습니다."})

    except Exception as e:
        logger.error(f"Clear cache error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_routes_bp.route("/raw-data")
def raw_data_page():
    """Raw data 페이지"""
    return render_template("raw_data_modern.html")


@admin_routes_bp.route("/api/raw-data", methods=["GET"])
def get_raw_data():
    """Raw blacklist data API endpoint with pagination and filters"""
    try:
        # Get query parameters
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 100, type=int)
        date_filter = request.args.get("date")
        source_filter = request.args.get("source")
        attack_type_filter = request.args.get("attack_type")
        ip_search = request.args.get("ip_search")

        # Calculate offset
        offset = (page - 1) * limit

        # Get database connection
        db_path = os.path.join(
            "/app" if os.path.exists("/app") else ".", "instance/blacklist.db"
        )
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Build WHERE clause
        where_conditions = []
        params = []

        if date_filter:
            where_conditions.append("DATE(detection_date) = ?")
            params.append(date_filter)

        if source_filter:
            where_conditions.append("source = ?")
            params.append(source_filter)

        if attack_type_filter:
            where_conditions.append("attack_type = ?")
            params.append(attack_type_filter)

        if ip_search:
            where_conditions.append("ip LIKE ?")
            params.append(f"%{ip_search}%")

        where_clause = (
            " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        )

        # Get total count
        count_query = f"SELECT COUNT(*) FROM blacklist_ip{where_clause}"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]

        # Get paginated data
        data_query = f"""
        SELECT
            id,
            ip,
            source,
            country,
            attack_type,
            detection_date,
            created_at,
            extra_data
        FROM blacklist_ip
        {where_clause}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """

        cursor.execute(data_query, params + [limit, offset])
        rows = cursor.fetchall()

        # Convert to list of dicts
        data = []
        for row in rows:
            data.append(
                {
                    "id": row["id"],
                    "ip": row["ip"],
                    "source": row["source"],
                    "country": row["country"],
                    "attack_type": row["attack_type"],
                    "detection_date": row["detection_date"],  # 원본 등록일 (엑셀 기준)
                    "created_at": row["created_at"],  # 수집일
                    "extra_data": row["extra_data"],
                }
            )

        conn.close()

        return jsonify(
            {
                "success": True,
                "data": data,
                "total": total_count,
                "page": page,
                "limit": limit,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Failed to get raw data: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


@admin_routes_bp.route("/api/expiring-ips", methods=["GET"])
def get_expiring_ips():
    """만료 예정인 IP 목록 조회"""
    try:
        # 파라미터로 기간 받기 (기본값: 30일)
        days = request.args.get("days", 30, type=int)
        if days > 90:
            days = 90  # 최대 90일

        blacklist_manager = current_app.blacklist_manager
        expiring_ips = blacklist_manager.get_expiring_ips(days=days)

        return jsonify(
            {
                "success": True,
                "days": days,
                "count": len(expiring_ips),
                "ips": expiring_ips,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Get expiring IPs error: {e}")
        return jsonify(create_error_response(e)), 500


@admin_routes_bp.route("/api/ip/<ip>/expiration", methods=["PUT"])
def set_ip_expiration(ip):
    """특정 IP의 만료 날짜 설정"""
    try:
        # IP 유효성 검증
        validate_ip(ip)

        # Request body에서 만료 날짜 가져오기
        data = request.get_json() or {}
        expires_at_str = data.get("expires_at")

        if not expires_at_str:
            return (
                jsonify({"success": False, "error": "expires_at field is required"}),
                400,
            )

        # 날짜 형식 파싱
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        except Exception:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)",
                    }
                ),
                400,
            )

        # 과거 날짜 검증
        if expires_at < datetime.now():
            return (
                jsonify(
                    {"success": False, "error": "Expiration date cannot be in the past"}
                ),
                400,
            )

        blacklist_manager = current_app.blacklist_manager
        result = blacklist_manager.set_ip_expiration(ip, expires_at)

        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 404

    except ValidationError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Set IP expiration error: {e}")
        return jsonify(create_error_response(e)), 500


@admin_routes_bp.route("/api/expiration/update", methods=["POST"])
def update_expiration_status():
    """만료 상태 업데이트"""
    try:
        # Get blacklist manager from service
        blacklist_manager = service.blacklist_manager
        if not blacklist_manager:
            return (
                jsonify({"success": False, "error": "Blacklist manager not available"}),
                500,
            )

        # Update expiration status
        result = blacklist_manager.update_expiration_status()

        return jsonify(result)
    except Exception as e:
        logger.error(f"Update expiration status error: {e}")
        return jsonify(create_error_response(e)), 500


@admin_routes_bp.route("/api/search/<ip>", methods=["GET"])
def search_single_ip(ip: str):
    """단일 IP 검색"""
    try:
        # IP 유효성 검증
        if not validate_ip(ip):
            return (
                jsonify({"success": False, "error": "Invalid IP address format"}),
                400,
            )

        # IP 검색
        result = service.search_ip(ip)

        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error(f"Single IP search error: {e}")
        return jsonify(create_error_response(e)), 500


@admin_routes_bp.route("/api/search", methods=["POST"])
def search_batch_ips():
    """배치 IP 검색"""
    try:
        data = request.get_json()
        if not data or "ips" not in data:
            return (
                jsonify(
                    {"success": False, "error": "Missing ips field in request body"}
                ),
                400,
            )

        ips = data["ips"]
        if not isinstance(ips, list):
            return jsonify({"success": False, "error": "ips must be a list"}), 400

        # 최대 100개로 제한
        if len(ips) > 100:
            return (
                jsonify(
                    {"success": False, "error": "Maximum 100 IPs allowed per request"}
                ),
                400,
            )

        # 각 IP 검증 및 검색
        results = []
        for ip in ips:
            if not validate_ip(ip):
                results.append(
                    {"ip": ip, "found": False, "error": "Invalid IP format"}
                )
                continue

            try:
                search_result = service.search_ip(ip)
                results.append({"ip": ip, "found": True, "data": search_result})
            except Exception as e:
                results.append(
                    {"ip": ip, "found": False, "error": str(e)}
                )

        return jsonify({"success": True, "results": results})
    except Exception as e:
        logger.error(f"Batch IP search error: {e}")
        return jsonify(create_error_response(e)), 500


@admin_routes_bp.route("/auth-settings")
def auth_settings_page():
    """인증 설정 페이지"""
    return render_template("auth_settings.html")


@admin_routes_bp.route("/system-settings")
def system_settings_page():
    """시스템 설정 페이지"""
    return render_template("system_settings.html")


# Error handlers
@admin_routes_bp.errorhandler(404)
def not_found_error(error):
    """404 에러 핸들러"""
    return (
        jsonify(
            {
                "success": False,
                "error": "Not found",
                "message": "The requested resource was not found",
            }
        ),
        404,
    )


@admin_routes_bp.errorhandler(500)
def internal_error(error):
    """500 에러 핸들러"""
    logger.error(f"Internal server error: {error}")
    return (
        jsonify(
            {
                "success": False,
                "error": "Internal server error",
                "message": "An unexpected error occurred",
            }
        ),
        500,
    )
