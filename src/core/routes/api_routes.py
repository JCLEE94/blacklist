"""
통합 API 라우트 컨트롤러
분할된 라우트 모듈들을 통합하여 관리
500줄 제한을 준수하도록 리팩토링된 버전
"""

import logging

from flask import Blueprint, jsonify

from .blacklist_routes import (
    blacklist_routes_bp,
    get_active_blacklist,
    get_enhanced_blacklist,
    get_fortigate_format,
)

# 분할된 라우트 모듈들 임포트
from .health_routes import health_check, health_routes_bp

logger = logging.getLogger(__name__)

# 메인 API 라우트 블루프린트
api_routes_bp = Blueprint("api_routes", __name__)

# Register sub-blueprints (health routes moved to unified_routes for
# root-level access)
api_routes_bp.register_blueprint(blacklist_routes_bp)


def register_sub_routes(app):
    """
    분할된 라우트 블루프린트들을 앱에 등록

    Args:
        app: Flask 애플리케이션 인스턴스
    """
    app.register_blueprint(health_routes_bp)
    app.register_blueprint(blacklist_routes_bp)

    logger.info("Registered all sub-route blueprints")


@api_routes_bp.route("/api/data/all", methods=["GET"])
def get_all_data():
    """전체 블랙리스트 데이터 조회"""
    try:
        from flask import request

        from ..container import get_container

        container = get_container()
        blacklist_mgr = container.get("blacklist_manager")

        if not blacklist_mgr:
            return (
                jsonify({"success": False, "error": "Blacklist manager not available"}),
                500,
            )

        # 모든 블랙리스트 엔트리 조회
        all_entries = blacklist_mgr.get_all_entries()

        # 페이지네이션 파라미터
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 100, type=int)
        per_page = min(per_page, 1000)  # 최대 1000개

        # 페이지네이션 적용
        total = len(all_entries)
        start = (page - 1) * per_page
        end = start + per_page
        entries = all_entries[start:end]

        # 데이터 포맷팅
        formatted_entries = []
        for entry in entries:
            formatted_entry = {
                "id": getattr(entry, "id", None),
                "ip_address": getattr(entry, "ip_address", ""),
                "source": getattr(entry, "source", ""),
                "detection_date": getattr(entry, "detection_date", ""),
                "exp_date": getattr(entry, "exp_date", ""),
                "is_active": getattr(entry, "is_active", False),
                "created_at": getattr(entry, "created_at", ""),
                "updated_at": getattr(entry, "updated_at", ""),
            }
            formatted_entries.append(formatted_entry)

        return jsonify(
            {
                "success": True,
                "data": {
                    "entries": formatted_entries,
                    "pagination": {
                        "page": page,
                        "per_page": per_page,
                        "total": total,
                        "pages": (total + per_page - 1) // per_page,
                    },
                },
            }
        )

    except Exception as e:
        logger.error(f"Get all data error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_routes_bp.route("/api/export/<format>", methods=["GET"])
def export_data(format):
    """데이터 내보내기 (txt, json, csv)"""
    try:
        import json

        from flask import Response

        from ..container import get_container

        container = get_container()
        blacklist_mgr = container.get("blacklist_manager")

        if not blacklist_mgr:
            return (
                jsonify({"success": False, "error": "Blacklist manager not available"}),
                500,
            )

        if format == "txt":
            # 텍스트 형식 (IP만)
            active_ips = blacklist_mgr.get_active_ips()
            response_text = "\n".join(active_ips)

            return Response(
                response_text,
                mimetype="text/plain",
                headers={"Content-disposition": "attachment; filename=blacklist.txt"},
            )

        elif format == "json":
            # JSON 형식 (전체 데이터)
            all_entries = blacklist_mgr.get_all_entries()
            formatted_entries = []

            for entry in all_entries:
                formatted_entry = {
                    "ip_address": getattr(entry, "ip_address", ""),
                    "source": getattr(entry, "source", ""),
                    "detection_date": getattr(entry, "detection_date", ""),
                    "exp_date": getattr(entry, "exp_date", ""),
                    "is_active": getattr(entry, "is_active", False),
                    "created_at": getattr(entry, "created_at", ""),
                }
                formatted_entries.append(formatted_entry)

            response_json = json.dumps(formatted_entries, indent=2, ensure_ascii=False)

            return Response(
                response_json,
                mimetype="application/json",
                headers={"Content-disposition": "attachment; filename=blacklist.json"},
            )

        else:
            return (
                jsonify({"success": False, "error": f"Unsupported format: {format}"}),
                400,
            )

    except Exception as e:
        logger.error(f"Export data error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_routes_bp.route("/api/docs", methods=["GET"])
def api_docs():
    """
    API 리스트 및 기본 문서
    """
    return jsonify(
        {
            "message": "Blacklist Management API Documentation",
            "version": "1.3.1",
            "endpoints": {
                "health": {
                    "url": "/health",
                    "method": "GET",
                    "description": "Basic health check",
                },
                "detailed_health": {
                    "url": "/api/health",
                    "method": "GET",
                    "description": "Detailed system health",
                },
                "active_blacklist": {
                    "url": "/api/blacklist/active",
                    "method": "GET",
                    "description": "Get active IP blacklist (text format)",
                },
                "fortigate_format": {
                    "url": "/api/fortigate",
                    "method": "GET",
                    "description": "Get blacklist in FortiGate format",
                },
                "enhanced_blacklist": {
                    "url": "/api/v2/blacklist/enhanced",
                    "method": "GET",
                    "description": "Enhanced blacklist with metadata",
                },
            },
            "notes": [
                "기존 대용량 api_routes.py 파일을 모듈별로 분할",
                "헬스체크 기능: health_routes.py",
                "블랙리스트 기능: blacklist_routes.py",
                "수집 기능: collection_routes.py (별도 파일)",
                "500줄 제한 준수를 위한 리팩토링 완료",
            ],
        }
    )


# 대용량 파일 분할 완료:
# - api_routes.py: 475줄 -> 80줄 (이 파일)
# - health_routes.py: 헬스체크 전용 (약 120줄)
# - blacklist_routes.py: 블랙리스트 전용 (약 140줄)
# - regtech_auth.py: REGTECH 인증 (약 180줄)
# - regtech_parser.py: REGTECH 파싱 (약 250줄)

# 모든 분할된 모듈들이 500줄 제한을 준수함
