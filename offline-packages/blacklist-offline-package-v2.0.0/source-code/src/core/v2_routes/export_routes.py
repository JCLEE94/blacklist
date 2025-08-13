#!/usr/bin/env python3
"""
V2 Export API Routes
"""

from flask import Blueprint, Response, jsonify, request

from ...utils.unified_decorators import unified_monitoring, unified_rate_limit
from .service import V2APIService

export_v2_bp = Blueprint("export_v2", __name__)

# Service instance will be initialized by the main app
service: V2APIService = None


def init_service(api_service: V2APIService):
    """Initialize the service instance"""
    global service
    service = api_service


@export_v2_bp.route("/export/<format>", methods=["GET"])
@unified_rate_limit(limit=50, per=3600)  # 50 exports per hour
def export_data(format):
    """데이터 내보내기 (V2)"""
    try:
        # 필터 파라미터 추출
        filters = {
            "limit": request.args.get("limit", 10000, type=int),
            "offset": request.args.get("offset", 0, type=int),
            "country": request.args.get("country"),
            "source": request.args.get("source"),
            "threat_type": request.args.get("threat_type"),
        }

        result = service.export_data(format, filters)

        if "error" in result:
            return jsonify(result), 400

        # 형식에 따른 응답 처리
        if format.lower() == "json":
            return jsonify(result)

        elif format.lower() == "csv":
            return Response(
                result["data"],
                mimetype="text/csv",
                headers={
                    "Content-disposition": "attachment; filename=blacklist_export.csv"
                },
            )

        elif format.lower() == "txt":
            return Response(
                result["data"],
                mimetype="text/plain",
                headers={
                    "Content-disposition": "attachment; filename=blacklist_export.txt"
                },
            )

        else:
            return jsonify({"error": "Unsupported format: {format}"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@export_v2_bp.route("/export/fortigate", methods=["GET"])
@unified_monitoring("v2_export_fortigate")
def export_fortigate_format():
    """FortiGate 형식 내보내기 (V2)"""
    try:
        # 활성 IP 목록 조회
        active_ips = service.blacklist_manager.get_active_ips()

        # FortiGate JSON 형식으로 변환
        fortigate_data = []
        for ip in active_ips:
            fortigate_data.append({"ip": ip, "type": "malicious", "confidence": "high"})

        result = {
            "format": "fortigate_json",
            "count": len(fortigate_data),
            "data": fortigate_data,
            "exported_at": service.blacklist_manager.get_system_health().get(
                "timestamp"
            ),
            "version": "2.0",
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@export_v2_bp.route("/export/bulk", methods=["POST"])
@unified_rate_limit(limit=10, per=3600)  # 10 bulk exports per hour
def bulk_export():
    """대량 데이터 내보내기 (V2)"""
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()

        export_format = data.get("format", "json")
        batch_size = data.get("batch_size", 5000)
        include_metadata = data.get("include_metadata", True)

        # 대량 데이터 내보내기
        filters = {
            "limit": batch_size,
            "offset": 0,
        }

        if include_metadata:
            all_data = service.get_blacklist_with_metadata(filters)
        else:
            # 단순 IP 목록만
            all_ips = service.blacklist_manager.get_active_ips()
            all_data = {
                "data": [{"ip": ip} for ip in all_ips[:batch_size]],
                "metadata": {"total_count": len(all_ips)},
            }

        # 형식 맞춰 변환
        export_result = service.export_data(export_format, {})

        # 배치 내보내기 메타데이터 추가
        export_result["bulk_export"] = True
        export_result["batch_info"] = {
            "batch_size": batch_size,
            "total_available": all_data.get("metadata", {}).get("total_count", 0),
            "include_metadata": include_metadata,
        }

        return jsonify(export_result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@export_v2_bp.route("/export/formats", methods=["GET"])
def get_supported_formats():
    """지원되는 내보내기 형식 목록 (V2)"""
    return jsonify(
        {
            "supported_formats": [
                {
                    "format": "json",
                    "description": "JSON format with full metadata",
                    "mime_type": "application/json",
                    "extension": ".json",
                },
                {
                    "format": "csv",
                    "description": "CSV format for spreadsheet applications",
                    "mime_type": "text/csv",
                    "extension": ".csv",
                },
                {
                    "format": "txt",
                    "description": "Plain text IP list (one per line)",
                    "mime_type": "text/plain",
                    "extension": ".txt",
                },
                {
                    "format": "fortigate",
                    "description": "FortiGate External Connector format",
                    "mime_type": "application/json",
                    "endpoint": "/api/v2/export/fortigate",
                },
            ],
            "limits": {
                "standard_export": "50 requests per hour",
                "bulk_export": "10 requests per hour",
                "max_records_per_request": 10000,
            },
        }
    )
