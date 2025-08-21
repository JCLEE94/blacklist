#!/usr/bin/env python3
"""
V2 API Service - Core service class for V2 API endpoints
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Dict, List

from ...core.blacklist_unified import UnifiedBlacklistManager
from ...core.common.ip_utils import IPUtils
from ...utils.advanced_cache import EnhancedSmartCache as CacheManager
# Performance optimizer removed for optimization
from ...utils.security import SecurityManager
from ...utils.unified_decorators import unified_cache

logger = logging.getLogger(__name__)


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

    # Performance measurement removed
    def get_blacklist_with_metadata(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """메타데이터 포함 블랙리스트 조회"""
        try:
            # 기본 필터 설정
            limit = filters.get("limit", 1000)
            offset = filters.get("offset", 0)
            country = filters.get("country")
            source = filters.get("source")
            threat_type = filters.get("threat_type")

            # 활성 IP 목록 조회
            all_ips = self.blacklist_manager.get_all_active_ips()

            # 필터 적용
            filtered_ips = all_ips
            if country:
                filtered_ips = [
                    ip for ip in filtered_ips if ip.get("country") == country
                ]
            if source:
                filtered_ips = [ip for ip in filtered_ips if ip.get("source") == source]
            if threat_type:
                filtered_ips = [
                    ip for ip in filtered_ips if ip.get("threat_type") == threat_type
                ]

            # 페이지네이션 적용
            total_count = len(filtered_ips)
            paginated_ips = filtered_ips[offset : offset + limit]

            return {
                "data": paginated_ips,
                "metadata": {
                    "total_count": total_count,
                    "returned_count": len(paginated_ips),
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + limit < total_count,
                    "filters_applied": {
                        "country": country,
                        "source": source,
                        "threat_type": threat_type,
                    },
                },
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting blacklist with metadata: {e}")
            return {
                "error": str(e),
                "data": [],
                "metadata": {"total_count": 0, "returned_count": 0},
            }

    # Performance measurement removed
    def batch_ip_check(
        self, ips: List[str], include_metadata: bool = True
    ) -> Dict[str, Any]:
        """배치 IP 검사"""
        try:
            # IP 유효성 검사
            # Simple IP validation instead of performance optimizer
            valid_ips = [ip for ip in ips if self._is_valid_ip(ip)]
            invalid_ips = [ip for ip in ips if not self._is_valid_ip(ip)]

            if not valid_ips:
                return {
                    "results": [],
                    "summary": {
                        "total_submitted": len(ips),
                        "valid_ips": 0,
                        "invalid_ips": len(invalid_ips),
                        "found_count": 0,
                        "not_found_count": 0,
                    },
                    "invalid_ips": invalid_ips,
                    "processed_at": datetime.now().isoformat(),
                }

            # 배치 검색 실행
            search_result = self.blacklist_manager.search_ips(
                valid_ips, max_workers=10, include_geo=include_metadata
            )

            # 결과 처리
            results = []
            found_count = 0

            for result in search_result.get("results", []):
                if result.get("found", False):
                    found_count += 1
                results.append(result)

            return {
                "results": results,
                "summary": {
                    "total_submitted": len(ips),
                    "valid_ips": len(valid_ips),
                    "invalid_ips": len(invalid_ips),
                    "found_count": found_count,
                    "not_found_count": len(valid_ips) - found_count,
                    "processing_time_seconds": search_result.get(
                        "processing_time_seconds", 0
                    ),
                },
                "invalid_ips": invalid_ips,
                "processed_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error in batch IP check: {e}")
            return {
                "error": str(e),
                "results": [],
                "summary": {
                    "total_submitted": len(ips),
                    "valid_ips": 0,
                    "found_count": 0,
                },
            }

    @unified_cache(ttl=600)
    def get_analytics_summary(self, period_days: int = 30) -> Dict[str, Any]:
        """분석 요약 정보 조회"""
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=period_days)

            # 기간별 통계 조회
            stats = self.blacklist_manager.get_stats_for_period(
                start_date.isoformat(), end_date.isoformat()
            )

            # 국가별 통계
            country_stats = self.blacklist_manager.get_country_statistics(limit=10)

            # 일일 트렌드
            daily_trend = self.blacklist_manager.get_daily_trend_data(days=7)

            # 시스템 건강도
            system_health = self.blacklist_manager.get_system_health()

            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": period_days,
                },
                "summary": {
                    "total_active_ips": stats.get("total_ips", 0),
                    "unique_countries": len(stats.get("countries", [])),
                    "active_sources": len(stats.get("sources", [])),
                    "threat_types": len(stats.get("threat_types", [])),
                },
                "top_countries": country_stats[:5],
                "daily_trend": daily_trend,
                "system_health": system_health,
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting analytics summary: {e}")
            return {
                "error": str(e),
                "summary": {"total_active_ips": 0, "unique_countries": 0},
                "generated_at": datetime.now().isoformat(),
            }

    def get_threat_level_analysis(self) -> Dict[str, Any]:
        """위협 레벨 분석"""
        try:
            # 활성 IP 목록 조회
            all_ips = self.blacklist_manager.get_all_active_ips()

            # 위협 레벨별 분류
            threat_levels = {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "unknown": 0,
            }

            threat_details = []

            for ip_info in all_ips:
                confidence = ip_info.get("confidence_score", 0)
                threat_type = ip_info.get("threat_type", "unknown")

                # 위협 레벨 결정
                if confidence >= 0.9:
                    level = "critical"
                elif confidence >= 0.7:
                    level = "high"
                elif confidence >= 0.5:
                    level = "medium"
                elif confidence > 0:
                    level = "low"
                else:
                    level = "unknown"

                threat_levels[level] += 1

                # 상위 위협 IP 수집 (critical/high만)
                if level in ["critical", "high"]:
                    threat_details.append(
                        {
                            "ip": ip_info.get("ip"),
                            "threat_level": level,
                            "threat_type": threat_type,
                            "confidence_score": confidence,
                            "country": ip_info.get("country"),
                            "source": ip_info.get("source"),
                            "detection_date": ip_info.get("detection_date"),
                        }
                    )

            # 위험도 점수 계산
            risk_score = (
                threat_levels["critical"] * 10
                + threat_levels["high"] * 5
                + threat_levels["medium"] * 2
                + threat_levels["low"] * 1
            )

            total_ips = sum(threat_levels.values())

            return {
                "threat_levels": threat_levels,
                "total_ips": total_ips,
                "risk_score": risk_score,
                "average_confidence": (
                    sum(ip.get("confidence_score", 0) for ip in all_ips) / len(all_ips)
                    if all_ips
                    else 0
                ),
                "high_priority_threats": sorted(
                    threat_details, key=lambda x: x["confidence_score"], reverse=True
                )[
                    :20
                ],  # 상위 20개
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error analyzing threat levels: {e}")
            return {
                "error": str(e),
                "threat_levels": {
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                    "unknown": 0,
                },
                "total_ips": 0,
                "risk_score": 0,
            }

    def export_data(
        self, format_type: str, filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """데이터 내보내기"""
        try:
            # 필터 적용하여 데이터 조회
            filters = filters or {}
            data = self.get_blacklist_with_metadata(filters)

            if format_type.lower() == "json":
                return {
                    "format": "json",
                    "data": data,
                    "exported_at": datetime.now().isoformat(),
                }

            elif format_type.lower() == "csv":
                # CSV 형식으로 변환
                csv_data = self._convert_to_csv(data.get("data", []))
                return {
                    "format": "csv",
                    "data": csv_data,
                    "exported_at": datetime.now().isoformat(),
                }

            elif format_type.lower() == "txt":
                # 단순 IP 목록
                ip_list = [ip_info.get("ip") for ip_info in data.get("data", [])]
                return {
                    "format": "txt",
                    "data": "\n".join(ip_list),
                    "exported_at": datetime.now().isoformat(),
                }

            else:
                return {
                    "error": "Unsupported export format: {format_type}",
                    "supported_formats": ["json", "csv", "txt"],
                }

        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return {"error": str(e)}

    def _convert_to_csv(self, data: List[Dict[str, Any]]) -> str:
        """데이터를 CSV 형식으로 변환"""
        if not data:
            return ""

        # CSV 헤더 생성
        headers = [
            "ip",
            "source",
            "detection_date",
            "country",
            "threat_type",
            "confidence_score",
        ]
        csv_lines = [",".join(headers)]

        # 데이터 행 생성
        for item in data:
            row = [
                str(item.get("ip", "")),
                str(item.get("source", "")),
                str(item.get("detection_date", "")),
                str(item.get("country", "")),
                str(item.get("threat_type", "")),
                str(item.get("confidence_score", "")),
            ]
            csv_lines.append(",".join(row))

        return "\n".join(csv_lines)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """성능 메트릭 조회"""
        try:
            # 옵티마이저에서 성능 데이터 조회
            metrics = {"performance_optimization": "disabled"}

            # 캐시 통계
            cache_stats = {
                "hit_rate": 0.0,
                "total_requests": 0,
                "cache_size": 0,
            }

            if hasattr(self.cache, "get_stats"):
                cache_stats = self.cache.get_stats()

            # 시스템 건강도
            system_health = self.blacklist_manager.get_system_health()

            return {
                "performance": metrics,
                "cache": cache_stats,
                "database": system_health.get("database", {}),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {"error": str(e)}

    def _is_valid_ip(self, ip: str) -> bool:
        """IP address validation using centralized utility"""
        return IPUtils.validate_ip(ip)
