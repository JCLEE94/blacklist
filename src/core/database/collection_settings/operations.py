#!/usr/bin/env python3
"""
Collection Settings Database Operations - Compact Version

Streamlined database operations with delegation to specialized modules.

Sample input: collection_result data, query parameters
Expected output: Database operations with minimal overhead
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class DatabaseOperations:
    """Compact database operations with delegation pattern"""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._ensure_database_exists()

    def _ensure_database_exists(self):
        """Ensure database and tables exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
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

                # Create index for performance
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_collected_at ON collection_history(collected_at)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_source_name ON collection_history(source_name)"
                )
        except Exception as e:
            print(f"Database initialization failed: {e}")

    def save_collection_result(
        self,
        source_name: str,
        success: bool,
        collected_count: int = 0,
        error_message: str = None,
        metadata: Dict[str, Any] = None,
    ) -> bool:
        """Save collection result to history"""
        try:
            import json

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO collection_history
                    (source_name, success, collected_count, error_message, metadata_json, collected_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        source_name,
                        success,
                        collected_count,
                        error_message,
                        json.dumps(metadata) if metadata else None,
                        datetime.now(),
                    ),
                )
                return True

        except Exception as e:
            print(f"Failed to save collection result: {e}")
            return False

    def get_collection_statistics(self) -> Dict[str, Any]:
        """Get comprehensive collection statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Get overall statistics
                cursor = conn.execute(
                    """
                    SELECT
                        COUNT(*) as total_collections,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_collections,
                        SUM(collected_count) as total_collected_count,
                        COUNT(DISTINCT source_name) as active_sources,
                        MAX(collected_at) as last_collection
                    FROM collection_history
                """
                )
                overall_stats = cursor.fetchone()

                # Get source-specific statistics
                cursor = conn.execute(
                    """
                    SELECT
                        source_name,
                        COUNT(*) as collections,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                        SUM(collected_count) as total_count,
                        MAX(collected_at) as last_collection
                    FROM collection_history
                    GROUP BY source_name
                    ORDER BY collections DESC
                """
                )
                source_stats = {}
                for row in cursor.fetchall():
                    success_rate = 0.0
                    if row["collections"] > 0:
                        success_rate = (row["successful"] / row["collections"]) * 100

                    source_stats[row["source_name"]] = {
                        "collections": row["collections"],
                        "successful": row["successful"],
                        "success_rate": round(success_rate, 2),
                        "total_count": row["total_count"] or 0,
                        "last_collection": row["last_collection"],
                    }

                # Calculate overall success rate
                overall_success_rate = 0.0
                if overall_stats["total_collections"] > 0:
                    overall_success_rate = (
                        overall_stats["successful_collections"]
                        / overall_stats["total_collections"]
                        * 100
                    )

                return {
                    "total_collections": overall_stats["total_collections"],
                    "successful_collections": overall_stats["successful_collections"],
                    "total_collected_count": overall_stats["total_collected_count"]
                    or 0,
                    "active_sources": overall_stats["active_sources"],
                    "last_collection": overall_stats["last_collection"],
                    "success_rate": round(overall_success_rate, 2),
                    "source_statistics": source_stats,
                }

        except Exception as e:
            print(f"Statistics retrieval failed: {e}")
            return {
                "total_collections": 0,
                "successful_collections": 0,
                "total_collected_count": 0,
                "active_sources": 0,
                "last_collection": None,
                "success_rate": 0.0,
                "source_statistics": {},
            }

    def cleanup_old_history(self, days_to_keep: int = 90) -> bool:
        """Clean up old history entries"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM collection_history WHERE collected_at < ?",
                    (cutoff_date.isoformat(),),
                )
                deleted_count = cursor.rowcount

            print(f"Cleaned up {deleted_count} old history entries")
            return True

        except Exception as e:
            print(f"History cleanup failed: {e}")
            return False

    # Delegation methods for complex queries
    def get_collection_calendar(self, year: int, month: int) -> Dict[str, Any]:
        """Get collection calendar - delegated to query operations"""
        from .query_operations import DatabaseQueryOperations

        query_ops = DatabaseQueryOperations(str(self.db_path))
        return query_ops.get_collection_calendar(year, month)

    def get_collection_history(
        self, source_name: str = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get collection history - delegated to query operations"""
        from .query_operations import DatabaseQueryOperations

        query_ops = DatabaseQueryOperations(str(self.db_path))
        return query_ops.get_collection_history(source_name, limit, offset)

    def get_error_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get error summary - delegated to query operations"""
        from .query_operations import DatabaseQueryOperations

        query_ops = DatabaseQueryOperations(str(self.db_path))
        return query_ops.get_error_summary(days)

    def get_source_performance(self, days: int = 30) -> Dict[str, Any]:
        """Get source performance - delegated to query operations"""
        from .query_operations import DatabaseQueryOperations

        query_ops = DatabaseQueryOperations(str(self.db_path))
        return query_ops.get_source_performance(days)


if __name__ == "__main__":
    # Validation function
    import os
    import tempfile
    from datetime import timedelta

    # Create test database
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_db:
        db_path = tmp_db.name

    try:
        # Test database operations
        db_ops = DatabaseOperations(db_path)

        # Test 1: Save collection result
        result_saved = db_ops.save_collection_result(
            "test_source", True, 100, None, {"test": "data"}
        )
        assert result_saved, "Failed to save collection result"

        # Test 2: Get statistics
        stats = db_ops.get_collection_statistics()
        assert stats["total_collections"] > 0, "No collections in statistics"
        assert "source_statistics" in stats, "Missing source statistics"

        # Test 3: Get history
        history = db_ops.get_collection_history(limit=5)
        assert len(history) > 0, "No history retrieved"

        print("✅ Database operations validation complete")

    finally:
        # Clean up test database
        os.unlink(db_path)
