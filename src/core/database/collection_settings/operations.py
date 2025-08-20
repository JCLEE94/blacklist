#!/usr/bin/env python3
"""
Collection Settings Database Operations Module
Provides database operations for collection history and statistics

Third-party packages:
- sqlite3: https://docs.python.org/3/library/sqlite3.html

Sample input: collection results, query parameters
Expected output: statistics, historical data
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


class DatabaseOperations:
    """Handles database operations for collection settings and history"""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)

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
                conn.commit()

            return True

        except Exception as e:
            print(f"Collection result save failed: {e}")
            return False

    def get_collection_statistics(self) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Overall statistics
                cursor = conn.execute(
                    """
                    SELECT 
                        COUNT(*) as total_collections,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_collections,
                        SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_collections,
                        SUM(collected_count) as total_collected_count,
                        MAX(collected_at) as last_collection
                    FROM collection_history
                """
                )
                overall_stats = cursor.fetchone()
                
                # Statistics by source
                cursor = conn.execute(
                    """
                    SELECT 
                        source_name,
                        COUNT(*) as total_collections,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_collections,
                        SUM(collected_count) as total_collected_count,
                        MAX(collected_at) as last_collection,
                        AVG(collected_count) as avg_collected_count
                    FROM collection_history
                    GROUP BY source_name
                    ORDER BY last_collection DESC
                """
                )
                source_stats = cursor.fetchall()
                
                # Recent collections (last 24 hours)
                cursor = conn.execute(
                    """
                    SELECT 
                        source_name,
                        success,
                        collected_count,
                        collected_at,
                        error_message
                    FROM collection_history
                    WHERE collected_at >= datetime('now', '-1 day')
                    ORDER BY collected_at DESC
                    LIMIT 50
                """
                )
                recent_collections = cursor.fetchall()
                
                return {
                    "overall": {
                        "total_collections": overall_stats["total_collections"] or 0,
                        "successful_collections": overall_stats["successful_collections"] or 0,
                        "failed_collections": overall_stats["failed_collections"] or 0,
                        "total_collected_count": overall_stats["total_collected_count"] or 0,
                        "last_collection": overall_stats["last_collection"],
                        "success_rate": (
                            (overall_stats["successful_collections"] or 0) / max(overall_stats["total_collections"] or 1, 1) * 100
                        ),
                    },
                    "by_source": [
                        {
                            "source_name": row["source_name"],
                            "total_collections": row["total_collections"],
                            "successful_collections": row["successful_collections"],
                            "total_collected_count": row["total_collected_count"] or 0,
                            "last_collection": row["last_collection"],
                            "avg_collected_count": round(row["avg_collected_count"] or 0, 2),
                            "success_rate": (row["successful_collections"] / max(row["total_collections"], 1) * 100),
                        }
                        for row in source_stats
                    ],
                    "recent_collections": [
                        {
                            "source_name": row["source_name"],
                            "success": bool(row["success"]),
                            "collected_count": row["collected_count"] or 0,
                            "collected_at": row["collected_at"],
                            "error_message": row["error_message"],
                        }
                        for row in recent_collections
                    ],
                }

        except Exception as e:
            print(f"Statistics retrieval failed: {e}")
            return {
                "overall": {"total_collections": 0, "successful_collections": 0, "failed_collections": 0, "total_collected_count": 0, "success_rate": 0},
                "by_source": [],
                "recent_collections": [],
            }

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
                        "success_rate": (row["successful_collections"] / max(row["total_collections"], 1) * 100),
                    }
                
                return {
                    "year": year,
                    "month": month,
                    "daily_stats": daily_stats,
                    "month_summary": {
                        "total_days_with_collections": len(daily_stats),
                        "total_collections": sum(stats["total_collections"] for stats in daily_stats.values()),
                        "total_successful": sum(stats["successful_collections"] for stats in daily_stats.values()),
                        "total_collected_count": sum(stats["total_collected_count"] for stats in daily_stats.values()),
                    },
                }

        except Exception as e:
            print(f"Calendar data retrieval failed: {e}")
            return {
                "year": year,
                "month": month,
                "daily_stats": {},
                "month_summary": {"total_days_with_collections": 0, "total_collections": 0, "total_successful": 0, "total_collected_count": 0},
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
                
                history = []
                for row in cursor.fetchall():
                    import json
                    metadata = None
                    if row["metadata_json"]:
                        try:
                            metadata = json.loads(row["metadata_json"])
                        except json.JSONDecodeError:
                            metadata = None
                    
                    history.append({
                        "id": row["id"],
                        "source_name": row["source_name"],
                        "success": bool(row["success"]),
                        "collected_count": row["collected_count"] or 0,
                        "error_message": row["error_message"],
                        "collected_at": row["collected_at"],
                        "metadata": metadata,
                    })
                
                return history

        except Exception as e:
            print(f"History retrieval failed: {e}")
            return []

    def cleanup_old_history(self, days_to_keep: int = 90) -> bool:
        """Clean up old collection history records"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM collection_history WHERE collected_at < ?",
                    (cutoff_date.isoformat(),),
                )
                deleted_count = cursor.rowcount
                conn.commit()
                
                print(f"Cleaned up {deleted_count} old history records")
                return True

        except Exception as e:
            print(f"History cleanup failed: {e}")
            return False

    def get_error_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get summary of recent errors"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get error counts by source
                cursor = conn.execute(
                    """
                    SELECT 
                        source_name,
                        COUNT(*) as error_count,
                        MAX(collected_at) as last_error
                    FROM collection_history
                    WHERE success = 0 AND collected_at >= ?
                    GROUP BY source_name
                    ORDER BY error_count DESC
                """,
                    (cutoff_date.isoformat(),),
                )
                error_by_source = cursor.fetchall()
                
                # Get recent error messages
                cursor = conn.execute(
                    """
                    SELECT source_name, error_message, collected_at
                    FROM collection_history
                    WHERE success = 0 AND collected_at >= ? AND error_message IS NOT NULL
                    ORDER BY collected_at DESC
                    LIMIT 20
                """,
                    (cutoff_date.isoformat(),),
                )
                recent_errors = cursor.fetchall()
                
                return {
                    "error_by_source": [
                        {
                            "source_name": row["source_name"],
                            "error_count": row["error_count"],
                            "last_error": row["last_error"],
                        }
                        for row in error_by_source
                    ],
                    "recent_errors": [
                        {
                            "source_name": row["source_name"],
                            "error_message": row["error_message"],
                            "collected_at": row["collected_at"],
                        }
                        for row in recent_errors
                    ],
                    "period_days": days,
                }

        except Exception as e:
            print(f"Error summary retrieval failed: {e}")
            return {"error_by_source": [], "recent_errors": [], "period_days": days}


if __name__ == "__main__":
    import sys
    import tempfile
    import os
    
    # Test database operations functionality
    all_validation_failures = []
    total_tests = 0
    
    # Create temporary database for testing
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        test_db_path = tmp_db.name
    
    try:
        # Initialize database tables first
        with sqlite3.connect(test_db_path) as conn:
            conn.execute("""
                CREATE TABLE collection_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_name TEXT NOT NULL,
                    success BOOLEAN DEFAULT 0,
                    collected_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata_json TEXT
                )
            """)
            conn.commit()
        
        db_ops = DatabaseOperations(test_db_path)
        
        # Test 1: Collection result save and statistics
        total_tests += 1
        try:
            # Save some test collection results
            success1 = db_ops.save_collection_result("test_source", True, 100)
            success2 = db_ops.save_collection_result("test_source", False, 0, "Test error")
            success3 = db_ops.save_collection_result("other_source", True, 50)
            
            if not all([success1, success2, success3]):
                all_validation_failures.append("Collection results: Save failed")
            
            stats = db_ops.get_collection_statistics()
            if stats["overall"]["total_collections"] != 3:
                all_validation_failures.append(f"Statistics: Expected 3 total collections, got {stats['overall']['total_collections']}")
            if stats["overall"]["successful_collections"] != 2:
                all_validation_failures.append(f"Statistics: Expected 2 successful collections, got {stats['overall']['successful_collections']}")
                
        except Exception as e:
            all_validation_failures.append(f"Collection results: Exception occurred - {e}")
        
        # Test 2: Collection history retrieval
        total_tests += 1
        try:
            history = db_ops.get_collection_history(limit=10)
            if len(history) != 3:
                all_validation_failures.append(f"History: Expected 3 records, got {len(history)}")
            
            # Test filtering by source
            filtered_history = db_ops.get_collection_history("test_source", limit=10)
            if len(filtered_history) != 2:
                all_validation_failures.append(f"Filtered history: Expected 2 records for test_source, got {len(filtered_history)}")
                
        except Exception as e:
            all_validation_failures.append(f"History retrieval: Exception occurred - {e}")
        
        # Test 3: Error summary
        total_tests += 1
        try:
            error_summary = db_ops.get_error_summary(7)
            if len(error_summary["error_by_source"]) == 0:
                all_validation_failures.append("Error summary: No error sources found when one was expected")
            
            if len(error_summary["recent_errors"]) == 0:
                all_validation_failures.append("Error summary: No recent errors found when one was expected")
                
        except Exception as e:
            all_validation_failures.append(f"Error summary: Exception occurred - {e}")
        
    finally:
        # Clean up test database
        try:
            os.unlink(test_db_path)
        except OSError:
            pass
    
    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Database operations module is validated and formal tests can now be written")
        sys.exit(0)
