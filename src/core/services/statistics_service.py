#!/usr/bin/env python3
"""
통합 블랙리스트 서비스 - 통계 및 분석 기능
통계, 분석, 리포트 등의 통계 전용 기능
"""

import sqlite3
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import Optional


# Statistics service mixin for UnifiedBlacklistService
class StatisticsServiceMixin:
    """
    통계 및 분석 기능을 제공하는 믹스인 클래스
    UnifiedBlacklistService에서 사용됨
    """

    async def get_statistics(self) -> Dict[str, Any]:
        """통합 시스템 통계"""
        try:
            # Check if blacklist_manager is available
            if not self.blacklist_manager:
                return {
                    "success": False,
                    "error": "Blacklist manager not initialized",
                    "timestamp": datetime.now().isoformat(),
                }

            # Get system health which includes stats
            health_data = self.blacklist_manager.get_system_health()

            # Extract stats from health data
            stats = {
                "total_ips": len(self.blacklist_manager.get_active_ips()),
                "sources": health_data.get("sources", {}),
                "status": health_data.get("status", "unknown"),
                "last_update": health_data.get("last_update", None),
            }

            # 서비스 상태 추가
            stats["service"] = {
                "name": self.config["service_name"],
                "version": self.config["version"],
                "running": self._running,
                "components": list(self._components.keys()),
                "auto_collection": self.config["auto_collection"],
                "collection_interval": self.config["collection_interval"],
            }

            return {
                "success": True,
                "statistics": stats,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"통계 조회 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def get_blacklist_summary(self) -> Dict[str, Any]:
        """블랙리스트 요약 정보"""
        try:
            if not self.blacklist_manager:
                return {"success": False, "error": "Blacklist manager not available"}

            # Get basic stats
            active_ips = self.blacklist_manager.get_active_ips()
            total_count = len(active_ips)

            # Get source breakdown
            source_counts = self._get_source_counts_from_db()

            return {
                "success": True,
                "summary": {
                    "total_active_ips": total_count,
                    "sources": source_counts,
                    "last_updated": datetime.now().isoformat(),
                    "collection_enabled": self.collection_enabled,
                },
            }
        except Exception as e:
            self.logger.error(f"블랙리스트 요약 조회 실패: {e}")
            return {"success": False, "error": str(e)}

    def _get_source_counts_from_db(self) -> Dict[str, int]:
        """데이터베이스에서 소스별 아이피 수 조회"""
        try:
            if not self.blacklist_manager or not hasattr(
                self.blacklist_manager, "db_path"
            ):
                return {}

            conn = sqlite3.connect(self.blacklist_manager.db_path)
            cursor = conn.cursor()

            # 소스별 아이피 수 조회
            cursor.execute(
                "SELECT source, COUNT(*) as count FROM blacklist_ip WHERE is_active = 1 GROUP BY source"
            )
            results = cursor.fetchall()
            conn.close()

            return {source: count for source, count in results}
        except Exception as e:
            self.logger.error(f"소스별 수 조회 실패: {e}")
            return {}

    def get_analytics_summary(self, days: int = 7) -> Dict[str, Any]:
        """분석 요약"""
        try:
            summary = {
                "period_days": days,
                "current_stats": self.get_blacklist_summary(),
                "daily_trends": self.get_daily_stats(days),
                "source_breakdown": self.get_source_statistics(),
                "timestamp": datetime.now().isoformat(),
            }
            return summary
        except Exception as e:
            self.logger.error(f"분석 요약 실패: {e}")
            return {"success": False, "error": str(e)}

    def get_daily_stats(self, days: int = 30) -> list:
        """일별 통계"""
        try:
            if not self.blacklist_manager or not hasattr(
                self.blacklist_manager, "db_path"
            ):
                return []

            conn = sqlite3.connect(self.blacklist_manager.db_path)
            cursor = conn.cursor()

            # 지난 N일간의 데이터 조회
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            cursor.execute(
                """
                SELECT DATE(created_at) as date,
                       COUNT(*) as new_ips,
                       source
                FROM blacklist_ip
                WHERE created_at >= ?
                GROUP BY DATE(created_at), source
                ORDER BY date DESC
                """,
                (start_date,),
            )

            results = cursor.fetchall()
            conn.close()

            # 날짜별로 그룹화
            daily_data = {}
            for date, count, source in results:
                if date not in daily_data:
                    daily_data[date] = {"date": date, "total": 0, "sources": {}}

                daily_data[date]["sources"][source] = count
                daily_data[date]["total"] += count

            return list(daily_data.values())
        except Exception as e:
            self.logger.error(f"일별 통계 실패: {e}")
            return []

    def get_monthly_stats(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """월별 통계"""
        try:
            if not self.blacklist_manager or not hasattr(
                self.blacklist_manager, "db_path"
            ):
                return {"success": False, "error": "Database not available"}

            conn = sqlite3.connect(self.blacklist_manager.db_path)
            cursor = conn.cursor()

            # 월별 데이터 집계
            cursor.execute(
                """
                SELECT strftime('%Y-%m', created_at) as month,
                       COUNT(*) as total_ips,
                       source
                FROM blacklist_ip
                WHERE created_at BETWEEN ? AND ?
                GROUP BY month, source
                ORDER BY month DESC
                """,
                (start_date, end_date),
            )

            results = cursor.fetchall()
            conn.close()

            # 월별로 그룹화
            monthly_data = {}
            for month, count, source in results:
                if month not in monthly_data:
                    monthly_data[month] = {"month": month, "total": 0, "sources": {}}

                monthly_data[month]["sources"][source] = count
                monthly_data[month]["total"] += count

            return {
                "success": True,
                "period": f"{start_date} ~ {end_date}",
                "monthly_stats": list(monthly_data.values()),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"월별 통계 실패: {e}")
            return {"success": False, "error": str(e)}

    def get_source_statistics(self) -> dict:
        """소스별 상세 통계"""
        try:
            if not self.blacklist_manager or not hasattr(
                self.blacklist_manager, "db_path"
            ):
                return {}

            conn = sqlite3.connect(self.blacklist_manager.db_path)
            cursor = conn.cursor()

            # 소스별 상세 통계
            cursor.execute(
                """
                SELECT source,
                       COUNT(*) as total_count,
                       COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_count,
                       MIN(created_at) as first_seen,
                       MAX(created_at) as last_seen
                FROM blacklist_ip
                GROUP BY source
                ORDER BY total_count DESC
                """
            )

            results = cursor.fetchall()
            conn.close()

            source_stats = {}
            for source, total, active, first_seen, last_seen in results:
                source_stats[source] = {
                    "total_ips": total,
                    "active_ips": active,
                    "inactive_ips": total - active,
                    "first_collection": first_seen,
                    "last_collection": last_seen,
                    "active_percentage": (
                        round((active / total) * 100, 2) if total > 0 else 0
                    ),
                }

            return source_stats
        except Exception as e:
            self.logger.error(f"소스 통계 실패: {e}")
            return {}

    def get_daily_collection_stats(self) -> list:
        """일별 수집 통계"""
        try:
            # 지난 30일간의 수집 로그를 기반으로 통계 생성
            logs = self.get_collection_logs(limit=1000)

            daily_stats = {}
            for log in logs:
                try:
                    log_date = datetime.fromisoformat(log["timestamp"]).date()
                    date_str = log_date.strftime("%Y-%m-%d")

                    if date_str not in daily_stats:
                        daily_stats[date_str] = {
                            "date": date_str,
                            "collections": 0,
                            "successful": 0,
                            "failed": 0,
                            "sources": set(),
                        }

                    daily_stats[date_str]["collections"] += 1
                    if "error" not in log:
                        daily_stats[date_str]["successful"] += 1
                    else:
                        daily_stats[date_str]["failed"] += 1

                    daily_stats[date_str]["sources"].add(log.get("source", "unknown"))
                except Exception:
                    continue

            # Set을 list로 변환
            result = []
            for date_str, stats in sorted(daily_stats.items(), reverse=True):
                stats["sources"] = list(stats["sources"])
                result.append(stats)

            return result[:30]  # 최대 30일
        except Exception as e:
            self.logger.error(f"일별 수집 통계 실패: {e}")
            return []

    def get_blacklist_with_metadata(
        self, limit: int = 1000, offset: int = 0, source_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """메타데이터와 함께 블랙리스트 조회"""
        try:
            if not self.blacklist_manager or not hasattr(
                self.blacklist_manager, "db_path"
            ):
                return {"success": False, "error": "Database not available"}

            conn = sqlite3.connect(self.blacklist_manager.db_path)
            cursor = conn.cursor()

            # 기본 쿼리
            query = """
                SELECT ip, created_at, detection_date, attack_type,
                       country, source, is_active, updated_at
                FROM blacklist_ip
                WHERE is_active = 1
            """

            params = []

            # 소스 필터 적용
            if source_filter:
                query += " AND source = ?"
                params.append(source_filter)

            # 정렬 및 페이징
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            results = cursor.fetchall()

            # 전체 갯수 계산
            count_query = "SELECT COUNT(*) FROM blacklist_ip WHERE is_active = 1"
            count_params = []
            if source_filter:
                count_query += " AND source = ?"
                count_params.append(source_filter)

            cursor.execute(count_query, count_params)
            total_count = cursor.fetchone()[0]

            conn.close()

            # 결과 정리
            ips_with_metadata = []
            for row in results:
                ip_data = {
                    "ip": row[0],
                    "created_at": row[1],
                    "detection_date": row[2],
                    "attack_type": row[3],
                    "country": row[4],
                    "source": row[5],
                    "is_active": bool(row[6]),
                    "updated_at": row[7],
                }
                ips_with_metadata.append(ip_data)

            return {
                "success": True,
                "ips": ips_with_metadata,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total": total_count,
                    "has_more": (offset + limit) < total_count,
                },
                "filter": {"source": source_filter},
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"메타데이터 블랙리스트 조회 실패: {e}")
            return {"success": False, "error": str(e)}

    def search_ip(self, ip: str) -> Dict[str, Any]:
        """아이피 검색 (동기 버전)"""
        try:
            if not self.blacklist_manager:
                return {"success": False, "error": "Blacklist manager not available"}

            # 블랙리스트 매니저를 통한 검색
            result = self.blacklist_manager.search_ip(ip)

            return {
                "success": True,
                "ip": ip,
                "result": result,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"아이피 검색 실패 ({ip}): {e}")
            return {
                "success": False,
                "ip": ip,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def search_batch_ips(self, ips: list) -> Dict[str, Any]:
        """대량 아이피 검색"""
        results = {}
        for ip in ips:
            results[ip] = self.search_ip(ip)
        return results

    def format_for_fortigate(self, ips: list) -> Dict[str, Any]:
        """FortiGate용 형식으로 변환"""
        try:
            entries = []
            for ip in ips:
                entries.append({"ip": ip, "type": "blacklist", "action": "deny"})

            fortigate_format = {
                "version": "1.0",
                "timestamp": datetime.now().isoformat(),
                "total_entries": len(entries),
                "entries": entries,
            }

            return fortigate_format
        except Exception as e:
            self.logger.error(f"FortiGate 형식 변환 실패: {e}")
            return {"success": False, "error": str(e)}

    def get_blacklist_paginated(
        self, page: int = 1, per_page: int = 100, source_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """페이지 단위 블랙리스트 조회"""
        try:
            offset = (page - 1) * per_page
            return self.get_blacklist_with_metadata(
                limit=per_page, offset=offset, source_filter=source_filter
            )
        except Exception as e:
            self.logger.error(f"페이지 블랙리스트 조회 실패: {e}")
            return {"success": False, "error": str(e)}
