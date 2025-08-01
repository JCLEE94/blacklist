#!/usr/bin/env python3
"""
V2 API Routes - Enhanced endpoints with advanced features
고도화된 V2 API 엔드포인트 (Blueprint 중복 등록 이슈 해결)
"""

import json
import logging
import os
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from flask import Blueprint, Response, jsonify, request, stream_with_context

from ..core.blacklist_unified import UnifiedBlacklistManager
from ..utils.cache import CacheManager
from ..utils.performance_optimizer import optimizer, validate_ips_batch
from ..utils.security import SecurityManager
from ..utils.unified_decorators import (
    unified_cache,
    unified_monitoring,
    unified_rate_limit,
    unified_validation,
)

logger = logging.getLogger(__name__)

# V2 API Blueprint
v2_bp = Blueprint("v2_api", __name__, url_prefix="/api/v2")


class V2APIService:
    """V2 API 서비스 클래스"""

    def __init__(
        self, blacklist_manager: UnifiedBlacklistManager, cache_manager: CacheManager
    ):
        self.blacklist_manager = blacklist_manager
        self.cache = cache_manager
        self.security = SecurityManager(
            secret_key=os.getenv("API_SECRET_KEY", "v2-api-security-key-2024")
        )
        self.executor = ThreadPoolExecutor(max_workers=10)

    @optimizer.measure_performance("v2_get_blacklist_with_metadata")
    def get_blacklist_with_metadata(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """메타데이터 포함 블랙리스트 조회"""
        # 필터 파싱
        limit = filters.get("limit", 1000)
        offset = filters.get("offset", 0)
        source = filters.get("source")
        country = filters.get("country")
        min_risk_score = filters.get("min_risk_score", 0)

        # 캐시 키 생성
        cache_key = f"v2:blacklist_metadata:{json.dumps(filters, sort_keys=True)}"

        # 캐시 확인
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return cached_data

        # 데이터베이스에서 직접 조회 (소스 정보 포함)
        import sqlite3

        db_path = "instance/blacklist.db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 소스 필터 적용한 쿼리
        query = """
            SELECT ip, source, country, attack_type, detection_date, created_at,
                   threat_level, reason, extra_data, is_active
            FROM blacklist_ip
            WHERE is_active = 1
        """
        params = []

        if source:
            query += " AND source = ?"
            params.append(source)
        if country:
            query += " AND country = ?"
            params.append(country)

        query += " ORDER BY created_at DESC"

        if offset:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        else:
            query += " LIMIT ?"
            params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # 총 개수 조회
        count_query = "SELECT COUNT(*) FROM blacklist_ip WHERE is_active = 1"
        count_params = []
        if source:
            count_query += " AND source = ?"
            count_params.append(source)
        if country:
            count_query += " AND country = ?"
            count_params.append(country)

        cursor.execute(count_query, count_params)
        total = cursor.fetchone()[0]

        conn.close()

        # 결과 변환
        filtered_ips = []
        for row in rows:
            ip_data = {
                "ip": row["ip"],
                "source": row["source"] or "unknown",
                "country": row["country"] or "Unknown",
                "attack_type": row["attack_type"] or "Unknown",
                "detection_date": row["detection_date"],
                "added_date": row["created_at"],
                "threat_level": row["threat_level"] or "high",
                "reason": row["reason"] or row["attack_type"] or "Unknown",
                "extra_data": row["extra_data"],
                "risk_score": 0.8,
                "category": "financial" if row["source"] == "REGTECH" else "malicious",
                "is_active": bool(row["is_active"]),
            }

            # 위험점수 필터링
            if ip_data.get("risk_score", 0) >= min_risk_score:
                filtered_ips.append(ip_data)

        # 메타데이터 추가
        result = {
            "data": {
                "data": filtered_ips,
                "page": (offset // limit) + 1 if limit > 0 else 1,
                "per_page": limit,
                "total": total,
                "pages": (total + limit - 1) // limit if limit > 0 else 1,
                "metadata_included": True,
            },
            "success": True,
        }

        # 캐시 저장
        self.cache.set(cache_key, result, ttl=300)

        return result

    @optimizer.measure_performance("v2_batch_ip_check")
    def batch_ip_check(self, ips: List[str]) -> Dict[str, Any]:
        """대량 IP 확인"""
        # IP 유효성 검증
        validations = validate_ips_batch(ips)
        valid_ips = [ip for ip, valid in zip(ips, validations) if valid]
        invalid_ips = [ip for ip, valid in zip(ips, validations) if not valid]

        # 블랙리스트 확인
        results = {}
        blacklist_data = self.blacklist_manager.get_all_active_ips()
        blacklist_set = {item["ip"] for item in blacklist_data}

        for ip in valid_ips:
            results[ip] = {
                "is_blacklisted": ip in blacklist_set,
                "checked_at": datetime.utcnow().isoformat(),
            }

        return {
            "results": results,
            "invalid_ips": invalid_ips,
            "stats": {
                "total_checked": len(ips),
                "valid_ips": len(valid_ips),
                "invalid_ips": len(invalid_ips),
                "blacklisted": sum(1 for r in results.values() if r["is_blacklisted"]),
            },
        }

    @optimizer.measure_performance("v2_get_analytics")
    def get_analytics(self, period: str = "7d") -> Dict[str, Any]:
        """고급 분석 데이터"""
        # 기간 파싱
        period_map = {"1d": 1, "7d": 7, "30d": 30, "90d": 90}
        days = period_map.get(period, 7)

        # 캐시 확인
        cache_key = f"v2:analytics:{period}"
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return cached_data

        # 데이터 분석
        all_data = self.blacklist_manager.get_all_active_ips()

        # 소스별 통계
        source_stats = {}
        country_stats = {}
        daily_stats = {}

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        for item in all_data:
            # 소스별
            source = item.get("source", "unknown")
            source_stats[source] = source_stats.get(source, 0) + 1

            # 국가별
            country = item.get("country", "unknown")
            country_stats[country] = country_stats.get(country, 0) + 1

            # 일별 (최근 기간만)
            if "detected_at" in item:
                try:
                    detected_date = datetime.fromisoformat(item["detected_at"]).date()
                    if detected_date >= cutoff_date.date():
                        date_str = detected_date.isoformat()
                        daily_stats[date_str] = daily_stats.get(date_str, 0) + 1
                except Exception:
                    pass

        # 트렌드 계산
        trend_data = []
        for i in range(days):
            date = (datetime.utcnow() - timedelta(days=i)).date().isoformat()
            trend_data.append({"date": date, "count": daily_stats.get(date, 0)})
        trend_data.reverse()

        result = {
            "period": period,
            "total_ips": len(all_data),
            "source_distribution": source_stats,
            "country_distribution": dict(
                sorted(country_stats.items(), key=lambda x: x[1], reverse=True)[:20]
            ),  # Top 20 countries
            "trend": trend_data,
            "generated_at": datetime.utcnow().isoformat(),
        }

        # 캐시 저장
        self.cache.set(cache_key, result, ttl=3600)  # 1시간

        return result

    def get_analytics_summary(self) -> Dict[str, Any]:
        """분석 요약 데이터"""
        # 캐시 확인
        cache_key = "v2:analytics:summary"
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return cached_data

        # 기본 통계 가져오기
        stats = self.blacklist_manager.get_statistics()
        all_data = self.blacklist_manager.get_all_active_ips()

        # 요약 데이터 생성
        result = {
            "total_ips": stats.get("total_ips", 0),
            "active_ips": stats.get("active_ips", 0),
            "regtech_count": stats.get("regtech_count", 0),
            "secudium_count": stats.get("secudium_count", 0),
            "public_count": stats.get("public_count", 0),
            "last_update": stats.get("last_update"),
            "source_distribution": {
                "regtech": {
                    "count": stats.get("regtech_count", 0),
                    "percentage": round(
                        (
                            stats.get("regtech_count", 0)
                            / max(stats.get("total_ips", 1), 1)
                        )
                        * 100,
                        1,
                    ),
                },
                "secudium": {
                    "count": stats.get("secudium_count", 0),
                    "percentage": round(
                        (
                            stats.get("secudium_count", 0)
                            / max(stats.get("total_ips", 1), 1)
                        )
                        * 100,
                        1,
                    ),
                },
                "public": {
                    "count": stats.get("public_count", 0),
                    "percentage": round(
                        (
                            stats.get("public_count", 0)
                            / max(stats.get("total_ips", 1), 1)
                        )
                        * 100,
                        1,
                    ),
                },
            },
            "status": "healthy" if stats.get("total_ips", 0) > 0 else "no_data",
            "generated_at": datetime.utcnow().isoformat(),
        }

        # 캐시 저장 (5분)
        self.cache.set(cache_key, result, ttl=300)

        return result


# 서비스 인스턴스 (Flask app context에서 초기화됨)
v2_service = None


# Blueprint 라우트들을 모듈 레벨에서 정의
@v2_bp.route("/blacklist/enhanced", methods=["GET"])
@unified_cache(ttl=300, key_prefix="v2:blacklist:enhanced")
def get_blacklist_enhanced():
    """향상된 블랙리스트 조회 (메타데이터 포함)"""
    if not v2_service:
        return jsonify({"error": "Service not initialized"}), 503

    filters = {
        "limit": request.args.get("limit", 1000, type=int),
        "offset": request.args.get("offset", 0, type=int),
        "source": request.args.get("source"),
        "country": request.args.get("country"),
        "min_risk_score": request.args.get("min_risk_score", 0, type=float),
    }

    result = v2_service.get_blacklist_with_metadata(filters)
    return jsonify(result)


@v2_bp.route("/blacklist/metadata", methods=["GET"])
@unified_cache(ttl=300, key_prefix="v2:blacklist")
def get_blacklist_with_metadata_v2_route():
    """메타데이터 포함 블랙리스트 조회"""
    if not v2_service:
        return jsonify({"error": "Service not initialized"}), 503

    filters = {
        "limit": request.args.get("limit", 1000, type=int),
        "offset": request.args.get("offset", 0, type=int),
        "source": request.args.get("source"),
        "country": request.args.get("country"),
        "min_risk_score": request.args.get("min_risk_score", 0, type=float),
    }

    result = v2_service.get_blacklist_with_metadata(filters)
    return jsonify(result)


@v2_bp.route("/blacklist/batch-check", methods=["POST"])
@unified_validation
@unified_rate_limit(limit=100, per=3600)  # 100 requests per hour
def batch_ip_check():
    """대량 IP 확인"""
    if not v2_service:
        return jsonify({"error": "Service not initialized"}), 503

    data = request.get_json()
    ips = data.get("ips", [])

    if not ips:
        return jsonify({"error": "No IPs provided"}), 400

    if len(ips) > 10000:
        return jsonify({"error": "Too many IPs (max 10000)"}), 400

    result = v2_service.batch_ip_check(ips)
    return jsonify(result)


@v2_bp.route("/analytics/summary", methods=["GET"])
@unified_cache(ttl=300, key_prefix="v2:analytics:summary")
def get_analytics_summary():
    """분석 요약 데이터"""
    if not v2_service:
        return jsonify({"error": "Service not initialized"}), 503

    result = v2_service.get_analytics_summary()
    return jsonify(result)


@v2_bp.route("/analytics/<period>", methods=["GET"])
@unified_cache(ttl=3600, key_prefix="v2:analytics")
def get_analytics(period):
    """고급 분석 데이터"""
    if not v2_service:
        return jsonify({"error": "Service not initialized"}), 503

    if period not in ["1d", "7d", "30d", "90d"]:
        return jsonify({"error": "Invalid period"}), 400

    result = v2_service.get_analytics(period)
    return jsonify(result)


@v2_bp.route("/export/<format>", methods=["GET"])
def export_data(format):
    """데이터 내보내기"""
    if not v2_service:
        return jsonify({"error": "Service not initialized"}), 503

    if format not in ["json", "csv", "txt"]:
        return jsonify({"error": "Invalid format"}), 400

    filters = {
        "limit": request.args.get("limit", 10000, type=int),
        "source": request.args.get("source"),
        "country": request.args.get("country"),
    }

    try:
        data = v2_service.get_blacklist_with_metadata(filters)["data"]

        if format == "json":
            return jsonify(data)
        elif format == "csv":
            import csv
            import io

            output = io.StringIO()
            if data:
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=blacklist.{format}"
                },
            )
        elif format == "txt":
            ip_list = "\n".join([item["ip"] for item in data])
            return Response(
                ip_list,
                mimetype="text/plain",
                headers={
                    "Content-Disposition": f"attachment; filename=blacklist.{format}"
                },
            )
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@v2_bp.route("/health", methods=["GET"])
def health_check():
    """V2 헬스체크"""
    if not v2_service:
        return (
            jsonify(
                {
                    "status": "unhealthy",
                    "error": "Service not initialized",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            503,
        )

    checks = {"database": False, "cache": False, "performance": False}

    # 데이터베이스 체크
    try:
        v2_service.blacklist_manager.get_stats()
        checks["database"] = True
    except Exception:
        pass

    # 캐시 체크
    try:
        v2_service.cache.set("health_check", "ok", ttl=1)
        checks["cache"] = v2_service.cache.get("health_check") == "ok"
    except Exception:
        pass

    # 성능 체크
    try:
        from ..utils.performance_optimizer import optimizer

        report = optimizer.get_performance_report()
        checks["performance"] = True
    except Exception:
        pass

    result = {
        "status": "healthy" if all(checks.values()) else "unhealthy",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }

    status_code = 200 if result["status"] == "healthy" else 503
    return jsonify(result), status_code


@v2_bp.route("/analytics/threat-levels", methods=["GET"])
def get_threat_levels():
    """위협 레벨별 분포"""
    try:
        from src.core.database import get_db_path

        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 위협 레벨별 카운트
        cursor.execute(
            """
            SELECT
                CASE
                    WHEN threat_level IS NULL OR threat_level = '' THEN 'medium'
                    ELSE LOWER(threat_level)
                END as level,
                COUNT(*) as count
            FROM blacklist_ip
            WHERE is_active = 1
            GROUP BY level
        """
        )

        level_data = cursor.fetchall()
        conn.close()

        # 기본 레벨 구조
        levels = {"low": 0, "medium": 0, "high": 0, "critical": 0}

        # 데이터 채우기
        for level, count in level_data:
            if level in levels:
                levels[level] = count
            else:
                # 알 수 없는 레벨은 medium으로 분류
                levels["medium"] += count

        return jsonify(
            {
                "success": True,
                "threat_levels": levels,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"위협 레벨 조회 실패: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "threat_levels": {"low": 0, "medium": 0, "high": 0, "critical": 0},
                }
            ),
            500,
        )


@v2_bp.route("/performance", methods=["GET"])
def get_performance_metrics():
    """성능 메트릭 조회"""
    if not v2_service:
        return jsonify({"error": "Service not initialized"}), 503

    try:
        report = optimizer.get_performance_report()
        return jsonify(
            {
                "metrics": report,
                "system": {
                    "cpu_count": optimizer.max_workers,
                    "memory_usage_mb": optimizer.metrics.get("memory_usage", 0),
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@v2_bp.route("/cache/warm", methods=["POST"])
def warm_cache():
    """캐시 워밍"""
    if not v2_service:
        return jsonify({"error": "Service not initialized"}), 503

    # 주요 데이터 미리 로드
    periods = ["1d", "7d", "30d"]
    warmed = []

    for period in periods:
        try:
            v2_service.get_analytics(period)
            warmed.append(f"analytics:{period}")
        except Exception:
            pass

    # 기본 블랙리스트
    try:
        v2_service.get_blacklist_with_metadata({"limit": 1000, "offset": 0})
        warmed.append("blacklist:default")
    except Exception:
        pass

    return jsonify(
        {
            "status": "success",
            "warmed_keys": warmed,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


@v2_bp.route("/stream/blacklist", methods=["GET"])
def stream_blacklist():
    """블랙리스트 스트리밍"""
    if not v2_service:
        return jsonify({"error": "Service not initialized"}), 503

    def generate():
        all_ips = v2_service.blacklist_manager.get_all_active_ips()

        # 청크 단위로 스트리밍
        chunk_size = 100
        for i in range(0, len(all_ips), chunk_size):
            chunk = all_ips[i : i + chunk_size]
            yield json.dumps(chunk) + "\n"
            time.sleep(0.01)  # Rate limiting

    return Response(stream_with_context(generate()), mimetype="application/x-ndjson")


# === 통계 대시보드용 추가 API ===


@v2_bp.route("/sources/distribution", methods=["GET"])
def get_sources_distribution():
    """소스별 분포 조회"""
    if not v2_service:
        return jsonify({"error": "Service not initialized"}), 503

    try:
        import sqlite3

        db_path = "instance/blacklist.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT source, COUNT(*) as count
            FROM blacklist_ip
            WHERE is_active = 1
            GROUP BY source
            ORDER BY count DESC
        """
        )

        results = cursor.fetchall()
        conn.close()

        sources = [{"name": row[0], "count": row[1]} for row in results]

        return jsonify(
            {
                "success": True,
                "sources": sources,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Sources distribution error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@v2_bp.route("/analytics/summary-data", methods=["GET"])
def get_analytics_summary_data():
    """분석 요약 정보 (통계 대시보드용)"""
    if not v2_service:
        return jsonify({"error": "Service not initialized"}), 503

    try:
        import sqlite3

        db_path = "instance/blacklist.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 기본 통계
        cursor.execute("SELECT COUNT(*) FROM blacklist_ip WHERE is_active = 1")
        total_threats = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM blacklist_ip WHERE is_active = 1 AND created_at > datetime('now', '-24 hours')"
        )
        new_threats_24h = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(DISTINCT country) FROM blacklist_ip WHERE is_active = 1"
        )
        countries_affected = cursor.fetchone()[0]

        conn.close()

        summary = {
            "total_threats": total_threats,
            "active_threats": total_threats,  # 현재는 모든 활성 IP가 위협
            "new_threats_24h": new_threats_24h,
            "countries_affected": countries_affected,
            "block_rate": 99.5,  # 예상 차단률
            "avg_response_time": 2.3,  # 예상 평균 대응 시간 (분)
        }

        return jsonify(
            {
                "success": True,
                "summary": summary,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Analytics summary error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@v2_bp.route("/analytics/ip-types", methods=["GET"])
def get_ip_types_distribution():
    """IP 유형별 분포"""
    if not v2_service:
        return jsonify({"error": "Service not initialized"}), 503

    try:
        import ipaddress
        import sqlite3

        db_path = "instance/blacklist.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT ip FROM blacklist_ip WHERE is_active = 1")
        ips = [row[0] for row in cursor.fetchall()]
        conn.close()

        ipv4_count = 0
        ipv6_count = 0
        cidr_count = 0

        for ip in ips:
            try:
                if "/" in ip:
                    cidr_count += 1
                elif ":" in ip:
                    ipv6_count += 1
                else:
                    ipv4_count += 1
            except Exception:
                pass

        return jsonify(
            {
                "success": True,
                "ip_types": {
                    "ipv4": ipv4_count,
                    "ipv6": ipv6_count,
                    "cidr": cidr_count,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"IP types distribution error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@v2_bp.route("/analytics/geographic", methods=["GET"])
def get_geographic_distribution():
    """지리적 분포"""
    if not v2_service:
        return jsonify({"error": "Service not initialized"}), 503

    try:
        import sqlite3

        db_path = "instance/blacklist.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT country, COUNT(*) as count
            FROM blacklist_ip
            WHERE is_active = 1 AND country IS NOT NULL AND country != ''
            GROUP BY country
            ORDER BY count DESC
            LIMIT 20
        """
        )

        results = cursor.fetchall()
        conn.close()

        countries = [{"country": row[0], "count": row[1]} for row in results]

        return jsonify(
            {
                "success": True,
                "countries": countries,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Geographic distribution error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@v2_bp.route("/analytics/detection-trend", methods=["GET"])
def get_detection_trend():
    """탐지 트렌드"""
    if not v2_service:
        return jsonify({"error": "Service not initialized"}), 503

    try:
        import sqlite3
        from datetime import datetime, timedelta

        period = request.args.get("period", "30d")
        days = int(period.replace("d", "")) if period.endswith("d") else 30

        db_path = "instance/blacklist.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM blacklist_ip
            WHERE created_at >= datetime('now', '-{} days')
            GROUP BY DATE(created_at)
            ORDER BY date
        """.format(
                days
            )
        )

        results = cursor.fetchall()
        conn.close()

        trend_data = [{"date": row[0], "count": row[1]} for row in results]

        return jsonify(
            {
                "success": True,
                "trend": trend_data,
                "period": period,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Detection trend error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@v2_bp.route("/analytics/hourly-activity", methods=["GET"])
def get_hourly_activity():
    """시간대별 활동"""
    if not v2_service:
        return jsonify({"error": "Service not initialized"}), 503

    try:
        import sqlite3

        db_path = "instance/blacklist.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT strftime('%H', created_at) as hour, COUNT(*) as count
            FROM blacklist_ip
            WHERE created_at >= datetime('now', '-7 days')
            GROUP BY strftime('%H', created_at)
            ORDER BY hour
        """
        )

        results = cursor.fetchall()
        conn.close()

        # 24시간 전체 데이터 생성 (없는 시간대는 0으로)
        hourly_data = {str(i).zfill(2): 0 for i in range(24)}
        for row in results:
            hourly_data[row[0]] = row[1]

        activity = [
            {"hour": hour, "count": count} for hour, count in hourly_data.items()
        ]

        return jsonify(
            {
                "success": True,
                "activity": activity,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Hourly activity error: {str(e)}")
        return jsonify({"error": str(e)}), 500


def register_v2_routes(
    app, blacklist_manager: UnifiedBlacklistManager, cache_manager: CacheManager
):
    """V2 라우트 등록 (Blueprint 중복 등록 방지)"""
    global v2_service

    # 서비스 인스턴스 초기화
    v2_service = V2APIService(blacklist_manager, cache_manager)

    # Blueprint 등록 (한 번만)
    if "v2_api" not in app.blueprints:
        app.register_blueprint(v2_bp)
        logger.info("V2 API routes registered successfully")
    else:
        logger.info("V2 API routes already registered, skipping")
