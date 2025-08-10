#!/usr/bin/env python3
"""
V2 Analytics API Routes
"""

from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from ...utils.unified_decorators import unified_cache
from .service import V2APIService

analytics_v2_bp = Blueprint("analytics_v2", __name__)

# Service instance will be initialized by the main app
service: V2APIService = None


def init_service(api_service: V2APIService):
    """Initialize the service instance"""
    global service
    service = api_service


@analytics_v2_bp.route("/analytics/summary", methods=["GET"])
@unified_cache(ttl=300, key_prefix="v2:analytics:summary")
def get_analytics_summary():
    """분석 요약 정보 (V2)"""
    try:
        period_days = request.args.get("period", 30, type=int)
        result = service.get_analytics_summary(period_days)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@analytics_v2_bp.route("/analytics/<period>", methods=["GET"])
@unified_cache(ttl=3600, key_prefix="v2:analytics")
def get_analytics(period):
    """기간별 분석 데이터 (V2)"""
    try:
        # 기간 파싱
        period_days = {"week": 7, "month": 30, "quarter": 90, "year": 365}.get(
            period, 30
        )

        result = service.get_analytics_summary(period_days)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@analytics_v2_bp.route("/analytics/threat-levels", methods=["GET"])
@unified_cache(ttl=600, key_prefix="v2:threat:levels")
def get_threat_levels():
    """위협 레벨 분석 (V2)"""
    try:
        result = service.get_threat_level_analysis()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@analytics_v2_bp.route("/analytics/trends", methods=["GET"])
@unified_cache(ttl=1800, key_prefix="v2:analytics:trends")
def get_trend_analysis():
    """트렌드 분석 (V2)"""
    try:
        days = request.args.get("days", 30, type=int)

        # 일일 트렌드 데이터 조회
        daily_data = service.blacklist_manager.get_daily_trend_data(days)

        # 트렌드 분석
        if len(daily_data) > 1:
            recent_avg = (
                sum(d["unique_ips"] for d in daily_data[-7:]) / 7
            )  # 최근 7일 평균
            previous_avg = (
                sum(d["unique_ips"] for d in daily_data[-14:-7]) / 7
                if len(daily_data) >= 14
                else recent_avg
            )

            trend_direction = (
                "increasing"
                if recent_avg > previous_avg
                else "decreasing" if recent_avg < previous_avg else "stable"
            )
            change_percent = (
                ((recent_avg - previous_avg) / previous_avg * 100)
                if previous_avg > 0
                else 0
            )
        else:
            trend_direction = "insufficient_data"
            change_percent = 0

        result = {
            "trend_analysis": {
                "direction": trend_direction,
                "change_percent": round(change_percent, 2),
                "recent_7day_avg": (
                    round(recent_avg, 1) if "recent_avg" in locals() else 0
                ),
                "previous_7day_avg": (
                    round(previous_avg, 1) if "previous_avg" in locals() else 0
                ),
            },
            "daily_data": daily_data,
            "period_days": days,
            "generated_at": datetime.now().isoformat(),
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@analytics_v2_bp.route("/analytics/sources", methods=["GET"])
@unified_cache(ttl=900, key_prefix="v2:analytics:sources")
def get_source_analysis():
    """데이터 소스별 분석 (V2)"""
    try:
        # 기간 설정
        days = request.args.get("days", 30, type=int)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        # 소스별 통계 조회
        stats = service.blacklist_manager.get_stats_for_period(
            start_date.isoformat(), end_date.isoformat()
        )

        # 소스별 상세 분석
        source_details = []
        for source_info in stats.get("sources", []):
            source_name = source_info.get("source")
            ip_count = source_info.get("count")

            # 해당 소스의 전체 IP 대비 비율 계산
            total_ips = stats.get("total_ips", 0)
            percentage = (ip_count / total_ips * 100) if total_ips > 0 else 0

            source_details.append(
                {
                    "source": source_name,
                    "ip_count": ip_count,
                    "percentage": round(percentage, 2),
                    "status": "active" if ip_count > 0 else "inactive",
                }
            )

        result = {
            "source_analysis": {
                "total_sources": len(source_details),
                "active_sources": len(
                    [s for s in source_details if s["status"] == "active"]
                ),
                "total_ips": stats.get("total_ips", 0),
            },
            "sources": sorted(
                source_details, key=lambda x: x["ip_count"], reverse=True
            ),
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days,
            },
            "generated_at": datetime.now().isoformat(),
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@analytics_v2_bp.route("/analytics/geo", methods=["GET"])
@unified_cache(ttl=1800, key_prefix="v2:analytics:geo")
def get_geo_analysis():
    """지리적 분석 (V2)"""
    try:
        limit = request.args.get("limit", 20, type=int)

        # 국가별 통계 조회
        country_stats = service.blacklist_manager.get_country_statistics(limit)

        # 지리적 분포 분석
        total_ips = sum(stat["ip_count"] for stat in country_stats)
        geo_analysis = []

        for stat in country_stats:
            country = stat["country"]
            ip_count = stat["ip_count"]
            percentage = (ip_count / total_ips * 100) if total_ips > 0 else 0

            geo_analysis.append(
                {
                    "country": country,
                    "ip_count": ip_count,
                    "percentage": round(percentage, 2),
                    "avg_confidence": stat.get("avg_confidence", 0),
                    "total_detections": stat.get("total_detections", 0),
                }
            )

        # 대륙별 그룹화 (간단한 버전)
        continent_mapping = {
            "KR": "Asia",
            "CN": "Asia",
            "JP": "Asia",
            "IN": "Asia",
            "US": "North America",
            "CA": "North America",
            "MX": "North America",
            "DE": "Europe",
            "FR": "Europe",
            "GB": "Europe",
            "IT": "Europe",
            "BR": "South America",
            "AR": "South America",
            "AU": "Oceania",
            "NZ": "Oceania",
            "EG": "Africa",
            "ZA": "Africa",
            "NG": "Africa",
        }

        continents = {}
        for analysis in geo_analysis:
            continent = continent_mapping.get(analysis["country"], "Unknown")
            if continent not in continents:
                continents[continent] = {"ip_count": 0, "countries": 0}
            continents[continent]["ip_count"] += analysis["ip_count"]
            continents[continent]["countries"] += 1

        result = {
            "geographic_analysis": {
                "total_countries": len(country_stats),
                "total_ips": total_ips,
                "top_countries": geo_analysis[:10],
            },
            "continental_distribution": continents,
            "detailed_countries": geo_analysis,
            "generated_at": datetime.now().isoformat(),
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
