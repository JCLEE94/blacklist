#!/usr/bin/env python3
"""
V2 Blacklist API Routes
"""


from flask import Flask, Blueprint, jsonify, request, redirect, url_for, render_template
import logging

logger = logging.getLogger(__name__)

from ...utils.unified_decorators import (
    unified_cache,
    unified_rate_limit,
    unified_validation,
)
from .service import V2APIService

blacklist_v2_bp = Blueprint("blacklist_v2", __name__)

# Service instance will be initialized by the main app
service: V2APIService = None


def init_service(api_service: V2APIService):
    """Initialize the service instance"""
    global service
    service = api_service


@blacklist_v2_bp.route("/blacklist/enhanced", methods=["GET"])
@unified_cache(ttl=300, key_prefix="v2:blacklist:enhanced")
def get_blacklist_enhanced():
    """향상된 블랙리스트 조회 (V2)"""
    try:
        # 요청 파라미터 추출
        filters = {
            "limit": request.args.get("limit", 1000, type=int),
            "offset": request.args.get("offset", 0, type=int),
            "country": request.args.get("country"),
            "source": request.args.get("source"),
            "threat_type": request.args.get("threat_type"),
        }

        result = service.get_blacklist_with_metadata(filters)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@blacklist_v2_bp.route("/blacklist/metadata", methods=["GET"])
@unified_cache(ttl=300, key_prefix="v2:blacklist")
def get_blacklist_with_metadata_v2_route():
    """메타데이터 포함 블랙리스트 조회 (V2)"""
    try:
        filters = {
            "limit": request.args.get("limit", 100, type=int),
            "offset": request.args.get("offset", 0, type=int),
            "country": request.args.get("country"),
            "source": request.args.get("source"),
        }

        result = service.get_blacklist_with_metadata(filters)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@blacklist_v2_bp.route("/blacklist/batch-check", methods=["POST"])
@unified_validation(validate_json=True)
@unified_rate_limit(limit=100, per=3600)  # 100 requests per hour
def batch_ip_check():
    """배치 IP 검사 (V2)"""
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        ips = data.get("ips", [])
        include_metadata = data.get("include_metadata", True)

        if not ips or not isinstance(ips, list):
            return jsonify({"error": "IPs list is required"}), 400

        if len(ips) > 1000:  # 배치 처리 한도
            return jsonify({"error": "Maximum 1000 IPs per request"}), 400

        result = service.batch_ip_check(ips, include_metadata)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@blacklist_v2_bp.route("/blacklist/search", methods=["POST"])
@unified_validation(validate_json=True)
def search_blacklist():
    """블랙리스트 검색 (V2)"""
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()

        query = data.get("query", "")
        search_type = data.get("type", "ip")  # ip, country, source
        limit = data.get("limit", 100)

        if search_type == "ip":
            # IP 검색
            result = service.batch_ip_check([query], include_metadata=True)
        else:
            # 메타데이터 기반 검색
            filters = {search_type: query, "limit": limit}
            result = service.get_blacklist_with_metadata(filters)

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@blacklist_v2_bp.route("/blacklist/stats", methods=["GET"])
@unified_cache(ttl=600, key_prefix="v2:blacklist:stats")
def get_blacklist_stats():
    """블랙리스트 통계 (V2)"""
    try:
        period_days = request.args.get("period", 30, type=int)

        # 전체 통계 데이터 조회
        summary = service.get_analytics_summary(period_days)

        # 블랙리스트 특화 통계 추가
        result = {
            "blacklist_statistics": {
                "total_active_ips": summary.get("summary", {}).get(
                    "total_active_ips", 0
                ),
                "countries_represented": summary.get("summary", {}).get(
                    "unique_countries", 0
                ),
                "data_sources": summary.get("summary", {}).get("active_sources", 0),
                "threat_categories": summary.get("summary", {}).get("threat_types", 0),
            },
            "period_info": summary.get("period", {}),
            "top_countries": summary.get("top_countries", []),
            "system_status": summary.get("system_health", {}).get("status", "unknown"),
            "generated_at": summary.get("generated_at"),
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
