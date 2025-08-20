#!/usr/bin/env python3
"""
Collection Database Query Operations Module

Provides read-only database query operations for collection history and analytics.

Sample input: source_name="regtech", date_range parameters
Expected output: Historical data, statistics, and calendar information
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


class DatabaseQueryOperations:
    """Read-only database query operations for collection data"""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)

    def get_collection_calendar(self, year: int, month: int) -> Dict[str, Any]:
        """Get collection calendar data for a specific month"""
        try:
            # Calculate month boundaries
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, month + 1, 1)

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Get daily collection counts
                cursor = conn.execute(
                    """
                    SELECT
                        DATE(collected_at) as collection_date,
                        COUNT(*) as total_collections,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_collections,
                        SUM(collected_count) as total_collected_count
                    FROM collection_history
                    WHERE collected_at >= ? AND collected_at < ?
                    GROUP BY DATE(collected_at)
                    ORDER BY collection_date
                """,
                    (start_date.isoformat(), end_date.isoformat()),
                )

                daily_stats = {}
                for row in cursor.fetchall():
                    daily_stats[row["collection_date"]] = {
                        "total_collections": row["total_collections"],
                        "successful_collections": row["successful_collections"],
                        "total_collected_count": row["total_collected_count"] or 0,
                        "success_rate": (
                            row["successful_collections"]
                            / max(row["total_collections"], 1)
                            * 100
                        ),
                    }

                return {
                    "year": year,
                    "month": month,
                    "daily_stats": daily_stats,
                    "month_summary": {
                        "total_days_with_collections": len(daily_stats),
                        "total_collections": sum(
                            stats["total_collections"] for stats in daily_stats.values()
                        ),
                        "total_successful": sum(
                            stats["successful_collections"]
                            for stats in daily_stats.values()
                        ),
                        "total_collected_count": sum(
                            stats["total_collected_count"]
                            for stats in daily_stats.values()
                        ),
                    },
                }

        except Exception as e:
            print(f"Calendar data retrieval failed: {e}")
            return {
                "year": year,
                "month": month,
                "daily_stats": {},
                "month_summary": {
                    "total_days_with_collections": 0,
                    "total_collections": 0,
                    "total_successful": 0,
                    "total_collected_count": 0,
                },
            }

    def get_collection_history(
        self, source_name: str = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get collection history with optional filtering"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                if source_name:
                    cursor = conn.execute(
                        """
                        SELECT * FROM collection_history
                        WHERE source_name = ?
                        ORDER BY collected_at DESC
                        LIMIT ? OFFSET ?
                    """,
                        (source_name, limit, offset),
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT * FROM collection_history
                        ORDER BY collected_at DESC
                        LIMIT ? OFFSET ?
                    """,
                        (limit, offset),
                    )

                results = []
                for row in cursor.fetchall():
                    result = {
                        "id": row["id"],
                        "source_name": row["source_name"],
                        "success": bool(row["success"]),
                        "collected_count": row["collected_count"],
                        "error_message": row["error_message"],
                        "collected_at": row["collected_at"],
                    }

                    # Parse metadata JSON if present
                    if row["metadata_json"]:
                        try:
                            import json

                            result["metadata"] = json.loads(row["metadata_json"])
                        except:
                            result["metadata"] = {}
                    else:
                        result["metadata"] = {}

                    results.append(result)

                return results

        except Exception as e:
            print(f"History retrieval failed: {e}")
            return []

    def get_error_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get summary of collection errors in the last N days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Get error counts by source
                error_cursor = conn.execute(
                    """
                    SELECT
                        source_name,
                        COUNT(*) as error_count,
                        error_message
                    FROM collection_history
                    WHERE success = 0 AND collected_at >= ?
                    GROUP BY source_name, error_message
                    ORDER BY error_count DESC
                """,
                    (cutoff_date.isoformat(),),
                )

                errors_by_source = {}
                for row in error_cursor.fetchall():
                    source = row["source_name"]
                    if source not in errors_by_source:
                        errors_by_source[source] = []

                    errors_by_source[source].append(
                        {
                            "error_message": row["error_message"],
                            "count": row["error_count"],
                        }
                    )

                # Get total error rate
                total_cursor = conn.execute(
                    """
                    SELECT
                        COUNT(*) as total_attempts,
                        SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as total_errors
                    FROM collection_history
                    WHERE collected_at >= ?
                """,
                    (cutoff_date.isoformat(),),
                )

                total_row = total_cursor.fetchone()
                error_rate = 0.0
                if total_row["total_attempts"] > 0:
                    error_rate = (
                        total_row["total_errors"] / total_row["total_attempts"]
                    ) * 100

                return {
                    "period_days": days,
                    "total_attempts": total_row["total_attempts"],
                    "total_errors": total_row["total_errors"],
                    "error_rate_percent": round(error_rate, 2),
                    "errors_by_source": errors_by_source,
                }

        except Exception as e:
            print(f"Error summary retrieval failed: {e}")
            return {
                "period_days": days,
                "total_attempts": 0,
                "total_errors": 0,
                "error_rate_percent": 0.0,
                "errors_by_source": {},
            }

    def get_source_performance(self, days: int = 30) -> Dict[str, Any]:
        """Get performance metrics by source for the last N days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                cursor = conn.execute(
                    """
                    SELECT
                        source_name,
                        COUNT(*) as total_collections,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_collections,
                        SUM(collected_count) as total_collected_count,
                        AVG(collected_count) as avg_collected_count,
                        MAX(collected_at) as last_collection,
                        MIN(collected_at) as first_collection
                    FROM collection_history
                    WHERE collected_at >= ?
                    GROUP BY source_name
                    ORDER BY total_collections DESC
                """,
                    (cutoff_date.isoformat(),),
                )

                source_performance = {}
                for row in cursor.fetchall():
                    source = row["source_name"]
                    success_rate = 0.0
                    if row["total_collections"] > 0:
                        success_rate = (
                            row["successful_collections"] / row["total_collections"]
                        ) * 100

                    source_performance[source] = {
                        "total_collections": row["total_collections"],
                        "successful_collections": row["successful_collections"],
                        "success_rate_percent": round(success_rate, 2),
                        "total_collected_count": row["total_collected_count"] or 0,
                        "avg_collected_count": round(
                            row["avg_collected_count"] or 0, 2
                        ),
                        "last_collection": row["last_collection"],
                        "first_collection": row["first_collection"],
                    }

                return {"period_days": days, "sources": source_performance}

        except Exception as e:
            print(f"Source performance retrieval failed: {e}")
            return {"period_days": days, "sources": {}}

    def get_recent_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent collection activity"""
        return self.get_collection_history(limit=limit, offset=0)


if __name__ == "__main__":
    # Validation function
    import os
    import tempfile

    # Create test database
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_db:
        db_path = tmp_db.name

    try:
        # Create test table
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS collection_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_name TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    collected_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    metadata_json TEXT,
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Insert test data
            conn.execute(
                """
                INSERT INTO collection_history
                (source_name, success, collected_count, collected_at)
                VALUES (?, ?, ?, ?)
                """,
                ("regtech", True, 100, datetime.now().isoformat()),
            )

        # Test query operations
        query_ops = DatabaseQueryOperations(db_path)

        # Test 1: Get collection history
        history = query_ops.get_collection_history(limit=5)
        assert len(history) > 0, "No history retrieved"
        assert "source_name" in history[0], "Missing source_name in history"

        # Test 2: Get source performance
        performance = query_ops.get_source_performance(days=30)
        assert "sources" in performance, "Missing sources in performance data"

        # Test 3: Get error summary
        error_summary = query_ops.get_error_summary(days=7)
        assert (
            "total_attempts" in error_summary
        ), "Missing total_attempts in error summary"

        print("✅ Database query operations validation complete")

    finally:
        # Clean up test database
        os.unlink(db_path)
