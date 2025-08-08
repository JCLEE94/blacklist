#!/usr/bin/env python3
"""
Statistics Service for Unified Blacklist Manager
"""

import logging
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ...utils.advanced_cache import EnhancedSmartCache
from ...utils.unified_decorators import unified_cache, unified_monitoring
from ..database import DatabaseManager

logger = logging.getLogger(__name__)


class StatisticsService:
    """Handles statistics operations for the blacklist manager"""

    def __init__(
        self, data_dir: str, db_manager: DatabaseManager, cache: EnhancedSmartCache
    ):
        self.data_dir = data_dir
        self.db_manager = db_manager
        self.cache = cache

        # Set database path for direct SQLite access
        if (
            hasattr(db_manager, "db_url")
            and db_manager.db_url
            and "sqlite:///" in db_manager.db_url
        ):
            self.db_path = db_manager.db_url.replace("sqlite:///", "")
        else:
            self.db_path = os.path.join(self.data_dir, "database.db")

    @unified_cache(ttl=1800)  # 30 minute cache
    def get_stats_for_period(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a date range"""
        try:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Base query for the period
                base_query = """
                    FROM ip_detections 
                    WHERE detection_date BETWEEN ? AND ? 
                      AND is_active = 1
                """

                # Total IPs in period
                cursor.execute(
                    f"SELECT COUNT(DISTINCT ip_address) {base_query}",
                    (start_date, end_date),
                )
                total_ips = cursor.fetchone()[0]

                # IPs by source
                cursor.execute(
                    f"""
                    SELECT source, COUNT(DISTINCT ip_address) as count 
                    {base_query}
                    GROUP BY source 
                    ORDER BY count DESC
                    """,
                    (start_date, end_date),
                )
                sources = [
                    {"source": row["source"], "count": row["count"]}
                    for row in cursor.fetchall()
                ]

                # IPs by country
                cursor.execute(
                    f"""
                    SELECT country, COUNT(DISTINCT ip_address) as count 
                    {base_query}
                    AND country IS NOT NULL 
                    GROUP BY country 
                    ORDER BY count DESC 
                    LIMIT 20
                    """,
                    (start_date, end_date),
                )
                countries = [
                    {"country": row["country"], "count": row["count"]}
                    for row in cursor.fetchall()
                ]

                # Daily trend
                cursor.execute(
                    f"""
                    SELECT detection_date, COUNT(DISTINCT ip_address) as count 
                    {base_query}
                    GROUP BY detection_date 
                    ORDER BY detection_date
                    """,
                    (start_date, end_date),
                )
                daily_trend = [
                    {"date": row["detection_date"], "count": row["count"]}
                    for row in cursor.fetchall()
                ]

                # Threat types
                cursor.execute(
                    f"""
                    SELECT threat_type, COUNT(DISTINCT ip_address) as count 
                    {base_query}
                    AND threat_type IS NOT NULL 
                    GROUP BY threat_type 
                    ORDER BY count DESC
                    """,
                    (start_date, end_date),
                )
                threat_types = [
                    {"type": row["threat_type"], "count": row["count"]}
                    for row in cursor.fetchall()
                ]

                return {
                    "period": {"start": start_date, "end": end_date},
                    "total_ips": total_ips,
                    "sources": sources,
                    "countries": countries,
                    "daily_trend": daily_trend,
                    "threat_types": threat_types,
                    "generated_at": datetime.now().isoformat(),
                }

        except sqlite3.Error as e:
            logger.error(f"Database error getting stats for period: {e}")
            return {
                "error": f"Database error: {e}",
                "period": {"start": start_date, "end": end_date},
                "total_ips": 0,
                "sources": [],
                "countries": [],
                "daily_trend": [],
                "threat_types": [],
            }

    @unified_cache(ttl=900)  # 15 minute cache
    def get_country_statistics(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get country statistics for active IPs"""
        try:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT 
                        country,
                        COUNT(DISTINCT ip_address) as ip_count,
                        COUNT(*) as total_detections,
                        AVG(confidence_score) as avg_confidence
                    FROM ip_detections 
                    WHERE is_active = 1 
                      AND country IS NOT NULL 
                      AND country != ''
                    GROUP BY country 
                    ORDER BY ip_count DESC 
                    LIMIT ?
                    """,
                    (limit,),
                )

                results = []
                for row in cursor.fetchall():
                    results.append(
                        {
                            "country": row[0],
                            "ip_count": row[1],
                            "total_detections": row[2],
                            "avg_confidence": round(row[3] or 0, 2),
                        }
                    )

                return results

        except sqlite3.Error as e:
            logger.error(f"Database error getting country stats: {e}")
            return []

    @unified_cache(ttl=900)  # 15 minute cache
    def get_daily_trend_data(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily trend data for the specified number of days"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        try:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT 
                        DATE(detection_date) as day,
                        COUNT(DISTINCT ip_address) as unique_ips,
                        COUNT(*) as total_detections,
                        COUNT(DISTINCT source) as sources_count
                    FROM ip_detections 
                    WHERE detection_date >= ? 
                      AND detection_date <= ?
                      AND is_active = 1
                    GROUP BY DATE(detection_date) 
                    ORDER BY day
                    """,
                    (start_date, end_date),
                )

                results = []
                for row in cursor.fetchall():
                    results.append(
                        {
                            "date": row[0],
                            "unique_ips": row[1],
                            "total_detections": row[2],
                            "sources_count": row[3],
                        }
                    )

                # Fill in missing dates with zero values
                date_range = []
                current_date = start_date
                while current_date <= end_date:
                    date_range.append(current_date.isoformat())
                    current_date += timedelta(days=1)

                # Create lookup for existing data
                data_lookup = {r["date"]: r for r in results}

                # Fill complete range
                complete_results = []
                for date_str in date_range:
                    if date_str in data_lookup:
                        complete_results.append(data_lookup[date_str])
                    else:
                        complete_results.append(
                            {
                                "date": date_str,
                                "unique_ips": 0,
                                "total_detections": 0,
                                "sources_count": 0,
                            }
                        )

                return complete_results

        except sqlite3.Error as e:
            logger.error(f"Database error getting daily trend: {e}")
            return []

    @unified_cache(ttl=600)  # 10 minute cache
    def get_system_health(self) -> Dict[str, Any]:
        """Get system health statistics"""
        try:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                cursor = conn.cursor()

                # Basic counts
                cursor.execute(
                    "SELECT COUNT(DISTINCT ip_address) FROM ip_detections WHERE is_active = 1"
                )
                active_ips = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT COUNT(DISTINCT source) FROM ip_detections WHERE is_active = 1"
                )
                active_sources = cursor.fetchone()[0]

                # Recent activity (last 24 hours)
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT ip_address) 
                    FROM ip_detections 
                    WHERE created_at > datetime('now', '-1 day') 
                      AND is_active = 1
                    """
                )
                recent_ips = cursor.fetchone()[0]

                # Database size (approximate)
                cursor.execute("SELECT COUNT(*) FROM ip_detections")
                total_records = cursor.fetchone()[0]

                # Cache statistics
                cache_stats = (
                    self.cache.get_stats() if hasattr(self.cache, "get_stats") else {}
                )

                return {
                    "database": {
                        "active_ips": active_ips,
                        "active_sources": active_sources,
                        "total_records": total_records,
                        "recent_ips_24h": recent_ips,
                    },
                    "cache": cache_stats,
                    "timestamp": datetime.now().isoformat(),
                    "status": "healthy" if active_ips > 0 else "no_data",
                }

        except sqlite3.Error as e:
            logger.error(f"Database error getting system health: {e}")
            return {
                "error": f"Database error: {e}",
                "status": "error",
                "timestamp": datetime.now().isoformat(),
            }

    @unified_cache(ttl=1800)  # 30 minute cache
    def get_expiration_stats(self) -> Dict[str, Any]:
        """Get expiration statistics for IPs"""
        try:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                cursor = conn.cursor()

                # Total active IPs
                cursor.execute(
                    "SELECT COUNT(DISTINCT ip_address) FROM ip_detections WHERE is_active = 1"
                )
                total_active = cursor.fetchone()[0]

                # IPs with expiration set
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT ip_address) 
                    FROM ip_detections 
                    WHERE is_active = 1 
                      AND expires_at IS NOT NULL
                    """
                )
                with_expiration = cursor.fetchone()[0]

                # IPs expiring soon (next 7 days)
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT ip_address) 
                    FROM ip_detections 
                    WHERE is_active = 1 
                      AND expires_at IS NOT NULL 
                      AND expires_at BETWEEN datetime('now') AND datetime('now', '+7 days')
                    """
                )
                expiring_soon = cursor.fetchone()[0]

                # Already expired but still active (cleanup needed)
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT ip_address) 
                    FROM ip_detections 
                    WHERE is_active = 1 
                      AND expires_at IS NOT NULL 
                      AND expires_at < datetime('now')
                    """
                )
                expired_active = cursor.fetchone()[0]

                return {
                    "total_active_ips": total_active,
                    "ips_with_expiration": with_expiration,
                    "ips_without_expiration": total_active - with_expiration,
                    "expiring_soon_7days": expiring_soon,
                    "expired_but_active": expired_active,
                    "expiration_coverage_percent": round(
                        (with_expiration / total_active * 100)
                        if total_active > 0
                        else 0,
                        1,
                    ),
                    "timestamp": datetime.now().isoformat(),
                }

        except sqlite3.Error as e:
            logger.error(f"Database error getting expiration stats: {e}")
            return {
                "error": f"Database error: {e}",
                "timestamp": datetime.now().isoformat(),
            }

    def get_expiring_ips(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get IPs that will expire within the specified days"""
        try:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT DISTINCT
                        ip_address,
                        source,
                        detection_date,
                        expires_at,
                        country,
                        threat_type
                    FROM ip_detections 
                    WHERE is_active = 1 
                      AND expires_at IS NOT NULL 
                      AND expires_at BETWEEN datetime('now') AND datetime('now', '+' || ? || ' days')
                    ORDER BY expires_at
                    """,
                    (days,),
                )

                results = []
                for row in cursor.fetchall():
                    # Calculate days until expiration
                    expires_at = datetime.fromisoformat(row["expires_at"])
                    days_until_expiry = (expires_at - datetime.now()).days

                    results.append(
                        {
                            "ip": row["ip_address"],
                            "source": row["source"],
                            "detection_date": row["detection_date"],
                            "expires_at": row["expires_at"],
                            "days_until_expiry": days_until_expiry,
                            "country": row["country"],
                            "threat_type": row["threat_type"],
                        }
                    )

                return results

        except sqlite3.Error as e:
            logger.error(f"Database error getting expiring IPs: {e}")
            return []
