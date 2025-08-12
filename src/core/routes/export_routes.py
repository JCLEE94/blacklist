"""
데이터 내보내기 라우트
데이터 내보내기 관련 API 엔드포인트
"""

import json
import logging
from datetime import datetime

from flask import Blueprint, Response, jsonify

from ..exceptions import create_error_response
from ..unified_service import get_unified_service

logger = logging.getLogger(__name__)

# 내보내기 라우트 블루프린트
export_routes_bp = Blueprint("export_routes", __name__)

# 통합 서비스 인스턴스
service = get_unified_service()


@export_routes_bp.route("/api/export/json", methods=["GET"])
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


@export_routes_bp.route("/api/export/txt", methods=["GET"])
def export_txt():
    """텍스트 형식으로 내보내기"""
    try:
        ips = service.get_active_blacklist_ips()

        # 헤더 정보 포함한 텍스트 파일
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = "# Blacklist Export\n"
        header += "# Generated: {timestamp}\n"
        header += "# Total IPs: {len(ips)}\n"
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


@export_routes_bp.route("/export/<format>", methods=["GET"])
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
