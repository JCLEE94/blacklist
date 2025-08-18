"""
블랙리스트 전용 라우트
api_routes.py에서 분할된 블랙리스트 관련 엔드포인트
"""

import logging
from datetime import datetime

from flask import Blueprint, Response, jsonify

from ..exceptions import create_error_response
from ..unified_service import get_unified_service
from ..container import get_container

logger = logging.getLogger(__name__)

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
        blacklist_mgr = container.get('blacklist_manager')
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
        blacklist_mgr = container.get('blacklist_manager')
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


@blacklist_routes_bp.route("/api/v2/blacklist/enhanced", methods=["GET"])
def get_enhanced_blacklist():
    """향상된 블랙리스트 - 메타데이터 포함"""
    try:
        # Get blacklist manager from container for enhanced data
        container = get_container()
        blacklist_mgr = container.get('blacklist_manager')
        
        # Get enhanced blacklist data
        if hasattr(service, 'get_enhanced_blacklist'):
            enhanced_data = service.get_enhanced_blacklist()
        else:
            # Fallback to basic active IPs
            active_ips = blacklist_mgr.get_active_ips()
            enhanced_data = {
                "ips": [{"ip": ip, "source": "unknown"} for ip in active_ips],
                "sources": {},
                "threat_levels": {},
                "last_updated": datetime.utcnow().isoformat(),
                "expiry_info": {}
            }

        if not enhanced_data:
            logger.warning("No enhanced blacklist data found")
            return jsonify(
                {
                    "ips": [],
                    "total_count": 0,
                    "generated_at": datetime.utcnow().isoformat(),
                    "version": "v2",
                }
            )

        # 응답 데이터 구성
        response_data = {
            "ips": enhanced_data.get("ips", []),
            "total_count": len(enhanced_data.get("ips", [])),
            "metadata": {
                "sources": enhanced_data.get("sources", {}),
                "threat_levels": enhanced_data.get("threat_levels", {}),
                "last_updated": enhanced_data.get("last_updated"),
                "expiry_info": enhanced_data.get("expiry_info", {}),
            },
            "generated_at": datetime.utcnow().isoformat(),
            "version": "v2",
        }

        total_count = response_data["total_count"]
        logger.info(f"Generated enhanced blacklist with {total_count} IPs")

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Failed to get enhanced blacklist: {e}")
        from ..exceptions import BlacklistError
        error = BlacklistError(f"Failed to get enhanced blacklist: {str(e)}")
        return create_error_response(error)
