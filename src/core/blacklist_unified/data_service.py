#!/usr/bin/env python3
"""
Data Management Service for Unified Blacklist Manager

This module provides a high-level interface for blacklist data operations including:
- IP address validation and processing
- Bulk import operations with comprehensive validation
- Active IP retrieval with fallback mechanisms
- Data cleanup and maintenance operations

Third-party packages:
- sqlite3: Python standard library
- Enhanced cache: Local caching system

Sample input: IP data lists, source identifiers, configuration parameters
Expected output: Processing results, active IP lists, operation status
"""

import logging
import os
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List

from ...utils.advanced_cache import EnhancedSmartCache
from ...utils.unified_decorators import unified_cache
from ..common.ip_utils import IPUtils
from ..database import DatabaseManager
from .database_operations import DatabaseOperations
from .file_operations import FileOperations
from .models import DataProcessingError

logger = logging.getLogger(__name__)


class DataService:
    """Handles data operations for the blacklist manager"""

    def __init__(
        self, data_dir: str, db_manager: DatabaseManager, cache: EnhancedSmartCache
    ):
        self.data_dir = data_dir
        self.db_manager = db_manager
        self.cache = cache
        self.lock = threading.RLock()
        
        # Initialize component services
        self.db_ops = DatabaseOperations(db_manager)
        self.file_ops = FileOperations(data_dir)
        
        # SQLite compatibility path (deprecated but kept for backward compatibility)
        self.db_path = os.path.join(data_dir, "blacklist.db")

        logger.info(f"DataService initialized with data_dir: {data_dir}")

    def _is_valid_ip(self, ip_str: str) -> bool:
        """Validate IP address format using centralized utility"""
        return IPUtils.validate_ip(ip_str)

    def bulk_import_ips(
        self,
        ips_data: List[Dict[str, Any]],
        source: str,
        batch_size: int = 1000,
        clear_existing: bool = False,
    ) -> Dict[str, Any]:
        """Bulk import IP addresses with enhanced validation and performance"""
        start_time = datetime.now()

        if clear_existing:
            self.clear_all()

        valid_ips = []
        invalid_ips = []

        # Validate and prepare data
        for ip_data in ips_data:
            if isinstance(ip_data, str):
                ip_data = {"ip": ip_data, "source": source}

            ip = ip_data.get("ip", "").strip()
            if self._is_valid_ip(ip):
                ip_data["ip"] = ip
                ip_data["source"] = ip_data.get("source", source)
                ip_data["detection_date"] = ip_data.get(
                    "detection_date", datetime.now().strftime("%Y-%m-%d")
                )
                valid_ips.append(ip_data)
            else:
                invalid_ips.append({"ip": ip, "reason": "Invalid IP format"})

        # Process via database operations
        try:
            db_result = self.db_ops.bulk_import_ips(valid_ips, source, batch_size)
            processed = db_result["processed"]
            errors = db_result["errors"]
            
            # Update file-based storage
            self.file_ops.update_file_storage(valid_ips, source)

        except Exception as e:
            error_msg = f"Database error during bulk import: {e}"
            logger.error(error_msg)
            raise DataProcessingError(error_msg, operation="bulk_import")

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        # Clear relevant caches
        self.cache.delete_pattern("active_ips*")
        self.cache.delete_pattern("stats*")

        result = {
            "total_submitted": len(ips_data),
            "valid_ips": len(valid_ips),
            "invalid_ips": len(invalid_ips),
            "processed": processed,
            "errors": errors,
            "invalid_entries": invalid_ips,
            "processing_time_seconds": processing_time,
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"Bulk import completed: {processed}/{len(valid_ips)} IPs processed")
        return result

    def get_active_ips(self) -> List[str]:
        """Get all active IP addresses with database and file fallback"""
        try:
            # Try database operations first
            return self.db_ops.get_active_ips()
        except Exception as e:
            logger.error(f"Database error getting active IPs: {e}")
            # Fallback to file-based method
            return self.file_ops.get_active_ips_from_files()

    @unified_cache(ttl=600)
    def get_all_active_ips(self) -> List[Dict[str, Any]]:
        """Get all active IPs with metadata (SQLite fallback for legacy support)"""
        try:
            with sqlite3.connect(self.db_path, timeout=15) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT
                        ip,
                        source,
                        detection_date,
                        collection_date,
                        country,
                        threat_type,
                        confidence as confidence_score,
                        created_at,
                        updated_at,
                        expires_at
                    FROM blacklist_entries
                    WHERE is_active = 1
                      AND (expires_at IS NULL OR expires_at > datetime('now'))
                    ORDER BY updated_at DESC, ip_address
                    """
                )

                results = []
                for row in cursor.fetchall():
                    results.append(
                        {
                            "ip": row["ip"],
                            "source": row["source"] or "REGTECH",
                            "detection_date": row["detection_date"],
                            "country": row["country"],
                            "threat_type": row["threat_type"] or "blacklist",
                            "confidence_score": row["confidence_score"] or 1.0,
                            "created_at": row["created_at"],
                            "updated_at": row["updated_at"],
                            "expires_at": row["expires_at"],
                        }
                    )

                return results

        except sqlite3.Error as e:
            logger.error(f"Database error getting all active IPs: {e}")
            # Fallback to simple IP list
            simple_ips = self.get_active_ips()
            return [
                {"ip": ip, "source": "unknown", "detection_date": None}
                for ip in simple_ips
            ]

    def clear_all(self) -> Dict[str, Any]:
        """Clear all blacklist data with comprehensive cleanup"""
        start_time = datetime.now()
        cleared_items = {
            "database_records": 0,
            "files_removed": 0,
            "directories_cleaned": 0,
            "cache_keys_cleared": 0,
        }

        try:
            # Clear database via database operations
            db_result = self.db_ops.clear_all_data()
            cleared_items["database_records"] = db_result.get("cleared_records", 0)

            # Clear file-based data via file operations
            file_result = self.file_ops.clear_file_data()
            cleared_items["files_removed"] = file_result.get("files_removed", 0)
            cleared_items["directories_cleaned"] = file_result.get("directories_cleaned", 0)

            # Clear caches
            cache_patterns = ["active_ips*", "stats*", "ip_search*", "fortigate*"]
            for pattern in cache_patterns:
                cleared_count = self.cache.delete_pattern(pattern)
                cleared_items["cache_keys_cleared"] += cleared_count

        except Exception as e:
            logger.error(f"Error during clear_all operation: {e}")
            raise DataProcessingError(f"Clear operation failed: {e}", operation="clear_all")

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        result = {
            "success": True,
            "cleared_items": cleared_items,
            "total_items_cleared": sum(cleared_items.values()),
            "processing_time_seconds": processing_time,
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"Clear all completed: {cleared_items}")
        return result

    def cleanup_old_data(self, days: int = 365) -> Dict[str, Any]:
        """Clean up old data beyond specified days"""
        try:
            return self.db_ops.cleanup_old_data(days)
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return {"error": str(e)}


if __name__ == "__main__":
    # Validation tests
    import sys
    import tempfile

    all_validation_failures = []
    total_tests = 0

    # Test 1: DataService instantiation
    total_tests += 1
    try:
        # Mock components for testing
        class MockDBManager:
            def __init__(self):
                self.database_url = "postgresql://test:test@localhost/test"
        
        class MockCache:
            def delete_pattern(self, pattern):
                return 0
        
        with tempfile.TemporaryDirectory() as temp_dir:
            data_service = DataService(temp_dir, MockDBManager(), MockCache())
            if hasattr(data_service, 'db_ops') and hasattr(data_service, 'file_ops'):
                print("✅ DataService instantiation working")
            else:
                all_validation_failures.append("DataService missing required components")
    except Exception as e:
        all_validation_failures.append(f"DataService instantiation failed: {e}")

    # Test 2: IP validation function
    total_tests += 1
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_service = DataService(temp_dir, MockDBManager(), MockCache())
            
            valid_ip = data_service._is_valid_ip("192.168.1.1")
            invalid_ip = data_service._is_valid_ip("invalid.ip.address")
            
            if valid_ip and not invalid_ip:
                print("✅ IP validation function working")
            else:
                all_validation_failures.append(f"IP validation failed: valid={valid_ip}, invalid={invalid_ip}")
    except Exception as e:
        all_validation_failures.append(f"IP validation failed: {e}")

    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("DataService module is validated and ready for use")
        sys.exit(0)
