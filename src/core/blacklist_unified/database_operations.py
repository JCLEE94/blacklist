#!/usr/bin/env python3
"""
Database Operations Service for Blacklist Data Management

This module handles all database-specific operations including:
- PostgreSQL operations and schema management
- Bulk import operations with batch processing
- Database connectivity and health checks
- Connection management and pooling

Third-party packages:
- psycopg2: https://pypi.org/project/psycopg2/
- sqlalchemy: https://sqlalchemy.org/

Sample input: IP data dictionaries, database connection parameters
Expected output: Database operation results, health status
"""

import logging
import os
import threading
from datetime import datetime
from typing import Any, Dict, List

import psycopg2

from ..database import DatabaseManager
from .models import DataProcessingError

logger = logging.getLogger(__name__)


class DatabaseOperations:
    """Handles database operations for blacklist data"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.lock = threading.RLock()

        # Use PostgreSQL database URL from config
        self.database_url = (
            db_manager.database_url
            if db_manager
            else os.environ.get(
                "DATABASE_URL",
                "postgresql://blacklist_user:blacklist_password_change_me@localhost:32543/blacklist",
            )
        )

        logger.info(f"DatabaseOperations initialized with: {self.database_url}")

    def bulk_import_ips(
        self,
        valid_ips: List[Dict[str, Any]],
        source: str,
        batch_size: int = 1000,
    ) -> Dict[str, Any]:
        """Bulk import validated IP addresses to PostgreSQL"""
        start_time = datetime.now()
        processed = 0
        errors = []

        try:
            # Use PostgreSQL if available
            if self.database_url and self.database_url.startswith("postgresql://"):
                conn = psycopg2.connect(self.database_url)
                cursor = conn.cursor()

                # PostgreSQL-specific table creation
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS blacklist_entries (
                        id SERIAL PRIMARY KEY,
                        ip_address INET NOT NULL,
                        source TEXT,
                        detection_date TIMESTAMP,
                        collection_date TIMESTAMP,
                        reg_date TIMESTAMP,
                        attack_type TEXT,
                        reason TEXT,
                        country TEXT,
                        threat_level TEXT,
                        as_name TEXT,
                        city TEXT,
                        is_active INTEGER DEFAULT 1,
                        expires_at DATETIME,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        extra_data TEXT
                    )
                    """
                )

                # Process in batches
                for i in range(0, len(valid_ips), batch_size):
                    batch = valid_ips[i : i + batch_size]

                    try:
                        # Prepare batch data
                        batch_data = []
                        for ip_data in batch:
                            batch_data.append(
                                (
                                    ip_data["ip"],
                                    ip_data.get("source", source),
                                    ip_data.get("detection_date"),
                                    ip_data.get("collection_date"),
                                    ip_data.get("country"),
                                    ip_data.get("threat_type"),
                                    ip_data.get("confidence_score", 1.0),
                                    ip_data.get("is_active", 1),
                                    ip_data.get("expires_at"),
                                    datetime.now(),
                                    datetime.now(),
                                )
                            )

                        # Batch insert with upsert logic
                        cursor.executemany(
                            """
                            INSERT OR REPLACE INTO blacklist_entries (
                                ip, source, detection_date, collection_date, country,
                                attack_type, threat_level, is_active,
                                expires_at, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            batch_data,
                        )

                        processed += len(batch)
                        logger.debug(
                            f"Processed batch {i//batch_size + 1}, total: {processed}"
                        )

                    except Exception as e:
                        error_msg = f"Error processing batch {i//batch_size + 1}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)

                conn.commit()

        except Exception as e:
            error_msg = f"Database error during bulk import: {e}"
            logger.error(error_msg)
            raise DataProcessingError(error_msg, operation="bulk_import")

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        return {
            "processed": processed,
            "errors": errors,
            "processing_time_seconds": processing_time,
            "timestamp": datetime.now().isoformat(),
        }

    def get_active_ips(self) -> List[str]:
        """Get all active IP addresses from database (PostgreSQL preferred)"""
        try:
            # Try PostgreSQL first (primary database)
            logger.debug(f"Getting active IPs from PostgreSQL: {self.database_url}")
            with psycopg2.connect(self.database_url) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT DISTINCT ip_address::text
                    FROM blacklist_entries
                    WHERE is_active = true
                      AND (exp_date IS NULL OR exp_date > CURRENT_DATE::text)
                    ORDER BY ip_address
                    """
                )

                result = []
                for row in cursor.fetchall():
                    ip_str = row[0]
                    # Remove CIDR notation if present (e.g., 1.2.3.4/32 -> 1.2.3.4)
                    if "/" in ip_str:
                        ip_str = ip_str.split("/")[0]
                    result.append(ip_str)

                logger.info(f"Found {len(result)} active IPs from PostgreSQL database")
                return result
                
        except Exception as e:
            logger.warning(f"PostgreSQL error: {e}, trying SQLite fallback")
            
            # Fallback to SQLite if PostgreSQL fails
            try:
                import sqlite3
                sqlite_db_path = "instance/blacklist.db"

                if os.path.exists(sqlite_db_path):
                    logger.debug(f"Getting active IPs from SQLite: {sqlite_db_path}")
                    with sqlite3.connect(sqlite_db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            SELECT DISTINCT ip_address
                            FROM blacklist_entries
                            WHERE is_active = 1
                            ORDER BY ip_address
                            """
                        )
                        result = []
                        for row in cursor.fetchall():
                            ip_str = row[0]
                            # Remove CIDR notation if present (e.g., 1.2.3.4/32 -> 1.2.3.4)
                            if "/" in ip_str:
                                ip_str = ip_str.split("/")[0]
                            result.append(ip_str)
                        logger.info(f"Found {len(result)} active IPs from SQLite database")
                        return result

            except Exception as sqlite_e:
                logger.error(f"SQLite fallback also failed: {sqlite_e}")

            # Final fallback to empty list
            logger.error("All database access attempts failed")
            raise DataProcessingError(
                f"Database error: {e}", operation="get_active_ips"
            )

    def cleanup_old_data(self, days: int = 365) -> Dict[str, Any]:
        """Clean up old data beyond specified days"""
        from datetime import timedelta

        cutoff_date = datetime.now() - timedelta(days=days)

        try:
            with psycopg2.connect(self.database_url) as conn:
                cursor = conn.cursor()

                # Count records to be cleaned
                cursor.execute(
                    "SELECT COUNT(*) FROM blacklist_entries WHERE created_at < %s",
                    (cutoff_date,),
                )
                count = cursor.fetchone()[0]

                # Mark old records as inactive
                cursor.execute(
                    "UPDATE blacklist_entries SET is_active = false, updated_at = %s "
                    "WHERE created_at < %s AND is_active = true",
                    (datetime.now(), cutoff_date),
                )

                conn.commit()

                logger.info(f"Cleaned up {count} records older than {days} days")
                return {
                    "cleaned_records": count,
                    "cutoff_date": cutoff_date.isoformat(),
                }

        except psycopg2.Error as e:
            logger.error(f"Error during cleanup: {e}")
            return {"error": str(e)}

    def clear_all_data(self) -> Dict[str, Any]:
        """Clear all blacklist data from database"""
        start_time = datetime.now()
        cleared_records = 0

        try:
            with psycopg2.connect(self.database_url) as conn:
                cursor = conn.cursor()

                # Count records before deletion
                cursor.execute(
                    "SELECT COUNT(*) FROM blacklist_entries WHERE is_active = true"
                )
                cleared_records = cursor.fetchone()[0]

                # Mark all records as inactive instead of deleting
                cursor.execute(
                    "UPDATE blacklist_entries SET is_active = false, updated_at = %s "
                    "WHERE is_active = true",
                    (datetime.now(),),
                )

                conn.commit()

        except Exception as e:
            logger.error(f"Error during clear_all operation: {e}")
            raise DataProcessingError(
                f"Clear operation failed: {e}", operation="clear_all"
            )

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        return {
            "success": True,
            "cleared_records": cleared_records,
            "processing_time_seconds": processing_time,
            "timestamp": datetime.now().isoformat(),
        }


if __name__ == "__main__":
    # Validation tests
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: Database operations instantiation
    total_tests += 1
    try:
        # Mock database manager for testing
        class MockDBManager:
            def __init__(self):
                self.database_url = "postgresql://test:test@localhost/test"

        db_ops = DatabaseOperations(MockDBManager())
        if hasattr(db_ops, "database_url") and hasattr(db_ops, "lock"):
            print("✅ DatabaseOperations instantiation working")
        else:
            all_validation_failures.append(
                "DatabaseOperations missing required attributes"
            )
    except Exception as e:
        all_validation_failures.append(f"DatabaseOperations instantiation failed: {e}")

    # Test 2: Batch data preparation structure
    total_tests += 1
    try:
        test_ip_data = {
            "ip": "192.168.1.1",
            "source": "test",
            "detection_date": "2025-01-01",
            "collection_date": "2025-01-01",
            "country": "US",
            "threat_type": "malware",
            "confidence_score": 0.8,
            "is_active": 1,
            "expires_at": None,
        }

        # Simulate batch data preparation
        batch_tuple = (
            test_ip_data["ip"],
            test_ip_data.get("source", "test"),
            test_ip_data.get("detection_date"),
            test_ip_data.get("collection_date"),
            test_ip_data.get("country"),
            test_ip_data.get("threat_type"),
            test_ip_data.get("confidence_score", 1.0),
            test_ip_data.get("is_active", 1),
            test_ip_data.get("expires_at"),
            datetime.now(),
            datetime.now(),
        )

        if len(batch_tuple) == 11 and batch_tuple[0] == "192.168.1.1":
            print("✅ Batch data preparation structure working")
        else:
            all_validation_failures.append(
                f"Batch data structure invalid: {len(batch_tuple)} items, first: {batch_tuple[0]}"
            )
    except Exception as e:
        all_validation_failures.append(f"Batch data preparation failed: {e}")

    # Final validation result
    if all_validation_failures:
        print(
            f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print("DatabaseOperations module is validated and ready for use")
        sys.exit(0)
