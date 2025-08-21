#!/usr/bin/env python3
"""
수집 대시보드 및 일별 추적 시스템
Collection Dashboard with Daily Tracking System
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class CollectionDashboard:
    """수집 대시보드 및 일별 추적 관리"""

    def __init__(self, db_path: str = "instance/blacklist.db"):
        self.db_path = db_path
        import tempfile

        self.regtech_dir = Path(tempfile.gettempdir()) / "regtech_data"

    def create_daily_tracking_table(self):
        """일별 수집 추적 테이블 생성"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_collection_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collection_date DATE NOT NULL UNIQUE,
                    source TEXT NOT NULL,
                    total_collected INTEGER DEFAULT 0,
                    new_ips INTEGER DEFAULT 0,
                    updated_ips INTEGER DEFAULT 0,
                    failed_attempts INTEGER DEFAULT 0,
                    collection_status TEXT DEFAULT 'pending', -- pending, success, failed, partial
                    collection_time_ms REAL DEFAULT 0.0,
                    data_quality_score REAL DEFAULT 0.0,
                    error_message TEXT,
                    file_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # 인덱스 생성
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_daily_collection_date
                ON daily_collection_tracking(collection_date)
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_daily_collection_source
                ON daily_collection_tracking(source)
            """
            )

            conn.commit()
            conn.close()
            logger.info("일별 수집 추적 테이블 생성 완료")

        except Exception as e:
            logger.error(f"테이블 생성 오류: {e}")

    def record_daily_collection(
        self,
        collection_date: str,
        source: str,
        total_collected: int,
        new_ips: int = 0,
        updated_ips: int = 0,
        status: str = "success",
        collection_time_ms: float = 0.0,
        error_message: str = None,
    ) -> bool:
        """일별 수집 기록"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 기존 기록 확인
            cursor.execute(
                """
                SELECT id FROM daily_collection_tracking
                WHERE collection_date = ? AND source = ?
            """,
                (collection_date, source),
            )

            existing = cursor.fetchone()

            if existing:
                # 업데이트
                cursor.execute(
                    """
                    UPDATE daily_collection_tracking
                    SET total_collected = ?, new_ips = ?, updated_ips = ?,
                        collection_status = ?, collection_time_ms = ?,
                        error_message = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE collection_date = ? AND source = ?
                """,
                    (
                        total_collected,
                        new_ips,
                        updated_ips,
                        status,
                        collection_time_ms,
                        error_message,
                        collection_date,
                        source,
                    ),
                )
            else:
                # 새 기록 삽입
                cursor.execute(
                    """
                    INSERT INTO daily_collection_tracking (
                        collection_date, source, total_collected, new_ips,
                        updated_ips, collection_status, collection_time_ms,
                        error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        collection_date,
                        source,
                        total_collected,
                        new_ips,
                        updated_ips,
                        status,
                        collection_time_ms,
                        error_message,
                    ),
                )

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"일별 수집 기록 오류: {e}")
            return False

    def get_collection_calendar(self, days: int = 30) -> Dict[str, Any]:
        """수집 캘린더 데이터 생성"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 최근 N일 날짜 범위
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days - 1)

            # 일별 수집 데이터 조회
            cursor.execute(
                """
                SELECT collection_date, source, total_collected,
                       collection_status, collection_time_ms
                FROM daily_collection_tracking
                WHERE collection_date BETWEEN ? AND ?
                ORDER BY collection_date DESC
            """,
                (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")),
            )

            collection_data = cursor.fetchall()

            # 캘린더 구조 생성
            calendar_data = {}
            missing_days = []

            # 모든 날짜 초기화
            for i in range(days):
                date = end_date - timedelta(days=i)
                date_str = date.strftime("%Y-%m-%d")
                calendar_data[date_str] = {
                    "date": date_str,
                    "status": "missing",
                    "sources": {},
                    "total_collected": 0,
                    "collection_time": 0.0,
                }

            # 실제 수집 데이터 매핑
            for row in collection_data:
                date, source, collected, status, time_ms = row

                if date in calendar_data:
                    calendar_data[date]["sources"][source] = {
                        "collected": collected,
                        "status": status,
                        "time_ms": time_ms,
                    }
                    calendar_data[date]["total_collected"] += collected
                    calendar_data[date]["collection_time"] += time_ms or 0

                    # 상태 업데이트 (우선순위: success > partial > failed > missing)
                    if status == "success":
                        calendar_data[date]["status"] = "success"
                    elif (
                        status == "partial"
                        and calendar_data[date]["status"] != "success"
                    ):
                        calendar_data[date]["status"] = "partial"
                    elif (
                        status == "failed"
                        and calendar_data[date]["status"] == "missing"
                    ):
                        calendar_data[date]["status"] = "failed"

            # 누락된 날짜 찾기
            for date_str, data in calendar_data.items():
                if data["status"] == "missing":
                    missing_days.append(date_str)

            # 통계 계산
            total_days = len(calendar_data)
            successful_days = sum(
                1 for d in calendar_data.values() if d["status"] == "success"
            )
            failed_days = sum(
                1 for d in calendar_data.values() if d["status"] == "failed"
            )
            missing_days_count = len(missing_days)

            success_rate = (successful_days / total_days * 100) if total_days > 0 else 0

            conn.close()

            return {
                "calendar": calendar_data,
                "missing_days": missing_days,
                "statistics": {
                    "total_days": total_days,
                    "successful_days": successful_days,
                    "failed_days": failed_days,
                    "missing_days": missing_days_count,
                    "success_rate": round(success_rate, 1),
                },
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"캘린더 데이터 생성 오류: {e}")
            return {}

    def get_collection_trends(self, days: int = 7) -> Dict[str, Any]:
        """수집 트렌드 분석"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days - 1)

            # 일별 트렌드 데이터
            cursor.execute(
                """
                SELECT collection_date,
                       SUM(total_collected) as daily_total,
                       SUM(new_ips) as daily_new,
                       AVG(collection_time_ms) as avg_time,
                       COUNT(DISTINCT source) as active_sources
                FROM daily_collection_tracking
                WHERE collection_date BETWEEN ? AND ?
                GROUP BY collection_date
                ORDER BY collection_date
            """,
                (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")),
            )

            trend_data = []
            for row in cursor.fetchall():
                date, total, new, avg_time, sources = row
                trend_data.append(
                    {
                        "date": date,
                        "total_collected": total or 0,
                        "new_ips": new or 0,
                        "avg_collection_time": round(avg_time or 0, 2),
                        "active_sources": sources or 0,
                    }
                )

            # 소스별 성능
            cursor.execute(
                """
                SELECT source,
                       COUNT(*) as collection_days,
                       SUM(total_collected) as total_collected,
                       AVG(total_collected) as avg_daily,
                       AVG(collection_time_ms) as avg_time
                FROM daily_collection_tracking
                WHERE collection_date BETWEEN ? AND ?
                GROUP BY source
            """,
                (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")),
            )

            source_performance = {}
            for row in cursor.fetchall():
                source, days_count, total, avg_daily, avg_time = row
                source_performance[source] = {
                    "collection_days": days_count,
                    "total_collected": total,
                    "avg_daily": round(avg_daily or 0, 1),
                    "avg_time_ms": round(avg_time or 0, 2),
                }

            conn.close()

            return {
                "trend_data": trend_data,
                "source_performance": source_performance,
                "period": {
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "days": days,
                },
            }

        except Exception as e:
            logger.error(f"트렌드 분석 오류: {e}")
            return {}

    def identify_missing_collections(self, days_back: int = 30) -> List[str]:
        """미수집 날짜 식별"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days_back)

            # 수집된 날짜들 조회
            cursor.execute(
                """
                SELECT DISTINCT collection_date
                FROM daily_collection_tracking
                WHERE collection_date BETWEEN ? AND ?
                  AND collection_status = 'success'
            """,
                (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")),
            )

            collected_dates = {row[0] for row in cursor.fetchall()}

            # 전체 날짜 범위와 비교
            missing_dates = []
            current = start_date

            while current <= end_date:
                date_str = current.strftime("%Y-%m-%d")

                # 주말 제외 (선택적)
                if current.weekday() < 5:  # 월-금만
                    if date_str not in collected_dates:
                        missing_dates.append(date_str)

                current += timedelta(days=1)

            conn.close()
            return missing_dates

        except Exception as e:
            logger.error(f"미수집 날짜 식별 오류: {e}")
            return []

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """대시보드 요약 정보"""
        try:
            calendar_data = self.get_collection_calendar(30)
            trends = self.get_collection_trends(7)
            missing_days = self.identify_missing_collections(30)

            # 최근 수집 상태
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT MAX(collection_date) as last_collection,
                       SUM(total_collected) as total_today
                FROM daily_collection_tracking
                WHERE collection_date = DATE('now')
            """
            )

            today_data = cursor.fetchone()
            last_collection = today_data[0] if today_data else None
            total_today = today_data[1] if today_data and today_data[1] else 0

            # 총 IP 수
            cursor.execute("SELECT COUNT(*) FROM blacklist_entries")
            total_ips = cursor.fetchone()[0]

            conn.close()

            return {
                "summary": {
                    "total_ips": total_ips,
                    "total_today": total_today,
                    "last_collection": last_collection,
                    "missing_days_count": len(missing_days),
                    "success_rate": calendar_data.get("statistics", {}).get(
                        "success_rate", 0
                    ),
                },
                "calendar": calendar_data,
                "trends": trends,
                "missing_days": missing_days[:10],  # 최근 10개만
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"대시보드 요약 생성 오류: {e}")
            return {}


if __name__ == "__main__":
    # 대시보드 시스템 테스트
    dashboard = CollectionDashboard()

    print("🔄 일별 추적 테이블 생성...")
    dashboard.create_daily_tracking_table()

    print("📊 오늘 수집 기록...")
    today = datetime.now().strftime("%Y-%m-%d")
    dashboard.record_daily_collection(
        collection_date=today,
        source="REGTECH",
        total_collected=2364,
        new_ips=2364,
        status="success",
        collection_time_ms=5000.0,
    )

    print("📅 수집 캘린더 생성...")
    calendar_data = dashboard.get_collection_calendar(30)
    if calendar_data:
        stats = calendar_data["statistics"]
        print(f"  - 총 {stats['total_days']}일 중 {stats['successful_days']}일 성공")
        print(f"  - 성공률: {stats['success_rate']}%")
        print(f"  - 누락일: {stats['missing_days']}일")

    print("📈 수집 트렌드 분석...")
    trends = dashboard.get_collection_trends(7)
    if trends and trends["trend_data"]:
        latest = trends["trend_data"][-1]
        print(f"  - 최근 수집: {latest['total_collected']}개 IP")
        print(f"  - 평균 수집 시간: {latest['avg_collection_time']}ms")

    print("❌ 미수집 날짜 확인...")
    missing = dashboard.identify_missing_collections(14)
    print(f"  - 최근 14일 중 {len(missing)}일 미수집")
    if missing:
        print(f"  - 미수집 날짜: {missing[:5]}")
