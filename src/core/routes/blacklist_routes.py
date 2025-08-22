"""
블랙리스트 전용 라우트
api_routes.py에서 분할된 블랙리스트 관련 엔드포인트
"""

from ..common.imports import Blueprint, jsonify, request, logger

from datetime import datetime


from ..container import get_container
from ..exceptions import create_error_response
from ..unified_service import get_unified_service


# 블랙리스트 라우트 블루프린트
blacklist_routes_bp = Blueprint("blacklist_routes", __name__)

# 통합 서비스 인스턴스
service = get_unified_service()


@blacklist_routes_bp.route("/api/blacklist/active", methods=["GET"])
def get_active_blacklist():
    """활성 블랙리스트 IP 목록 반환 (텍스트 형식)"""
    try:
        # 활성 IP 목록 가져오기
        # Get blacklist manager from container and fetch active IPs
        container = get_container()
        blacklist_mgr = container.get("blacklist_manager")
        active_ips = blacklist_mgr.get_active_ips()

        if not active_ips:
            logger.warning("No active IPs found")
            return Response("", mimetype="text/plain", status=200)

        # IP 목록을 텍스트로 변환 (각 IP를 줄바꿈으로 구분)
        ip_list_text = "\n".join(active_ips)

        logger.info(f"Returned {len(active_ips)} active IPs")

        return Response(
            ip_list_text,
            mimetype="text/plain",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Total-IPs": str(len(active_ips)),
                "X-Generated-At": datetime.utcnow().isoformat(),
            },
        )

    except Exception as e:
        logger.error(f"Failed to get active blacklist: {e}")
        return create_error_response(
            "blacklist_fetch_failed", f"Failed to fetch active blacklist: {str(e)}", 500
        )


@blacklist_routes_bp.route("/api/fortigate", methods=["GET"])
def get_fortigate_format():
    """FortiGate External Connector 형식으로 블랙리스트 반환"""
    try:
        # 활성 IP 목록 가져오기
        # Get blacklist manager from container and fetch active IPs
        container = get_container()
        blacklist_mgr = container.get("blacklist_manager")
        active_ips = blacklist_mgr.get_active_ips()

        if not active_ips:
            logger.warning("No active IPs for FortiGate format")
            return Response("", mimetype="text/plain", status=200)

        # FortiGate 형식으로 변환
        fortigate_entries = []
        for ip in active_ips:
            fortigate_entries.append(f"set src {ip}")

        fortigate_text = "\n".join(fortigate_entries)

        logger.info(f"Generated FortiGate format for {len(active_ips)} IPs")

        return Response(
            fortigate_text,
            mimetype="text/plain",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Total-IPs": str(len(active_ips)),
                "X-Format": "fortigate-external-connector",
                "X-Generated-At": datetime.utcnow().isoformat(),
            },
        )

    except Exception as e:
        logger.error(f"Failed to generate FortiGate format: {e}")
        from ..exceptions import BlacklistError

        error = BlacklistError(f"Failed to generate FortiGate format: {str(e)}")
        return create_error_response(error)


@blacklist_routes_bp.route("/api/blacklist/enhanced", methods=["GET"])
@blacklist_routes_bp.route("/api/v2/blacklist/enhanced", methods=["GET"])
def get_enhanced_blacklist():
    """향상된 블랙리스트 - 메타데이터 포함"""
    try:
        
        # Get pagination parameters
        per_page = min(int(request.args.get("per_page", 100)), 1000)
        page = int(request.args.get("page", 1))

        # Get blacklist manager from container for enhanced data
        container = get_container()
        blacklist_mgr = container.get("blacklist_manager")

        # Get active IPs
        active_ips = blacklist_mgr.get_active_ips()

        # Paginate the results
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paged_ips = active_ips[start_idx:end_idx] if active_ips else []

        # Format data for JavaScript expectations
        formatted_data = []
        for idx, ip in enumerate(paged_ips):
            formatted_data.append(
                {
                    "id": idx + start_idx + 1,
                    "ip": ip,
                    "source": "REGTECH",  # Default source since we know it's from REGTECH
                    "is_expired": False,
                    "days_until_expiry": None,  # SQLite doesn't have expiration data
                    "expiry_status": "active",
                }
            )

        # Calculate expiry stats (simplified for SQLite)
        total = len(active_ips)
        expiry_stats = {
            "total": total,
            "active": total,  # All are active in SQLite
            "expired": 0,
            "expiring_soon": 0,
            "expiring_warning": 0,
        }

        # Response in the format expected by JavaScript
        response_data = {
            "success": True,
            "data": formatted_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": ((total - 1) // per_page + 1) if total > 0 else 0,
            },
            "expiry_stats": expiry_stats,
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(
            f"Generated enhanced blacklist with {len(formatted_data)} IPs (page {page})"
        )
        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Failed to get enhanced blacklist: {e}")
        from ..exceptions import BlacklistError

        error = BlacklistError(f"Failed to get enhanced blacklist: {str(e)}")
        return create_error_response(error)
