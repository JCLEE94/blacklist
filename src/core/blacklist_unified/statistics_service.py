#!/usr/bin/env python3
"""
통합 블랙리스트 서비스 - 통계 서비스
blacklist_unified 모듈용 통계 서비스 클래스
"""

import logging
import sqlite3
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class StatisticsService:
    """통계 서비스 - blacklist_unified 전용"""

    def __init__(self, data_dir=None, db_manager=None, cache_manager=None):
        """통계 서비스 초기화"""
        self.data_dir = data_dir
        self.db_manager = db_manager
        self.cache_manager = cache_manager

    def get_stats_for_period(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """기간별 통계 (실제 DB 데이터 조회)"""
        try:
            with sqlite3.connect(self.db_manager.db_path, timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # 전체 IP 수
                cursor.execute(
                    "SELECT COUNT(*) FROM blacklist_entries WHERE is_active = 1"
                )
                total_ips = cursor.fetchone()[0]

                # 기간별 새로운 IP
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM blacklist_entries 
                    WHERE is_active = 1 
                    AND created_at BETWEEN ? AND ?
                """,
                    (start_date, end_date),
                )
                new_ips = cursor.fetchone()[0]

                # 소스별 통계
                cursor.execute(
                    """
                    SELECT source, COUNT(*) as count 
                    FROM blacklist_entries 
                    WHERE is_active = 1 
                    GROUP BY source
                """
                )
                sources = {row[0]: row[1] for row in cursor.fetchall()}

                # 국가별 통계
                cursor.execute(
                    """
                    SELECT country, COUNT(*) as count 
                    FROM blacklist_entries 
                    WHERE is_active = 1 AND country IS NOT NULL 
                    GROUP BY country 
                    ORDER BY count DESC 
                    LIMIT 10
                """
                )
                countries = {row[0]: row[1] for row in cursor.fetchall()}

                return {
                    "period": {"start": start_date, "end": end_date},
                    "total_ips": total_ips,
                    "new_ips": new_ips,
                    "sources": sources,
                    "countries": countries,
                }
        except Exception as e:
            logger.error(f"Error getting period stats: {e}")
            return {
                "period": {"start": start_date, "end": end_date},
                "total_ips": 0,
                "new_ips": 0,
                "sources": {},
                "countries": {},
            }

    def get_country_statistics(self, limit: int = 10) -> List[Dict[str, Any]]:
        """국가별 통계 (실제 DB 데이터 조회)"""
        try:
            with sqlite3.connect(self.db_manager.db_path, timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT 
                        country,
                        COUNT(*) as ip_count,
                        COUNT(DISTINCT source) as source_count
                    FROM blacklist_entries 
                    WHERE is_active = 1 AND country IS NOT NULL
                    GROUP BY country 
                    ORDER BY ip_count DESC 
                    LIMIT ?
                """,
                    (limit,),
                )

                return [
                    {
                        "country": row["country"],
                        "ip_count": row["ip_count"],
                        "source_count": row["source_count"],
                        "percentage": 0,  # 계산 후 설정
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Error getting country statistics: {e}")
            return []

    def get_daily_trend_data(self, days: int = 7) -> Dict[str, Any]:
        """일일 트렌드 데이터 (실제 DB 데이터 조회)"""
        try:
            with sqlite3.connect(self.db_manager.db_path, timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # 최근 N일간 일별 IP 추가 수
                cursor.execute(
                    """
                    SELECT 
                        DATE(created_at) as date,
                        COUNT(*) as count
                    FROM blacklist_entries 
                    WHERE created_at >= date('now', '-' || ? || ' days')
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                """,
                    (days,),
                )

                trend_data = [
                    {"date": row["date"], "count": row["count"]}
                    for row in cursor.fetchall()
                ]

                total_changes = sum(item["count"] for item in trend_data)

                return {
                    "days": days,
                    "trend_data": trend_data,
                    "total_changes": total_changes,
                }
        except Exception as e:
            logger.error(f"Error getting trend data: {e}")
            return {"days": days, "trend_data": [], "total_changes": 0}

    def get_system_health(self) -> Dict[str, Any]:
        """시스템 상태 with real database data"""
        try:
            with sqlite3.connect(self.db_manager.db_path, timeout=10) as conn:
                cursor = conn.cursor()

                # Get active IPs count
                cursor.execute("SELECT COUNT(*) FROM blacklist_ip WHERE is_active = 1")
                active_ips = cursor.fetchone()[0]

                # Get total IPs count
                cursor.execute("SELECT COUNT(*) FROM blacklist_ip")
                total_ips = cursor.fetchone()[0]

                # Get source counts
                cursor.execute(
                    """
                    SELECT source, COUNT(*) as count 
                    FROM blacklist_ip 
                    WHERE is_active = 1 
                    GROUP BY source
                """
                )
                source_counts = dict(cursor.fetchall())

                return {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "uptime": "0d 0h 0m",
                    "memory_usage": "0MB",
                    "db_status": "connected",
                    "database": {
                        "active_ips": active_ips,
                        "total_ips": total_ips,
                        "regtech_count": source_counts.get("REGTECH", 0),
                        "secudium_count": source_counts.get("SECUDIUM", 0),
                        "public_count": source_counts.get("PUBLIC", 0),
                    },
                }
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "uptime": "0d 0h 0m",
                "memory_usage": "0MB",
                "db_status": "error",
                "database": {
                    "active_ips": 0,
                    "total_ips": 0,
                    "regtech_count": 0,
                    "secudium_count": 0,
                    "public_count": 0,
                },
            }

    def get_expiration_stats(self) -> Dict[str, Any]:
        """만료 통계"""
        return {"total_expiring": 0, "expired_today": 0, "expiring_soon": 0}

    def get_expiring_ips(self, days: int = 7) -> List[Dict[str, Any]]:
        """곧 만료될 IP 목록"""
        return []

    def get_statistics(self) -> Dict[str, Any]:
        """통합 통계 정보 (동기 버전)"""
        try:
            # 기본 통계 데이터 반환
            return {
                "total_ips": 0,
                "active_ips": 0,
                "expired_ips": 0,
                "unique_countries": 0,
                "sources": {},
                "last_update": datetime.now().isoformat(),
                "database_size": "0 MB",
                "status": "healthy",
            }
        except Exception as e:
            return {
                "total_ips": 0,
                "active_ips": 0,
                "expired_ips": 0,
                "unique_countries": 0,
                "sources": {},
                "last_update": None,
                "database_size": "0 MB",
                "status": "error",
                "error": str(e),
            }
