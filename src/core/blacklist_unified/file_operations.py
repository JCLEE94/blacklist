#!/usr/bin/env python3
"""
File Operations Service for Blacklist Data Management

This module handles file-based operations including:
- File-based storage for backward compatibility
- Excel file processing for REGTECH data
- Directory management and organization
- Fallback data loading mechanisms

Third-party packages:
- pandas: https://pandas.pydata.org/
- glob: Python standard library

Sample input: File paths, IP data structures
Expected output: File operation results, loaded IP data
"""

import glob
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Set

from ...utils.unified_decorators import unified_cache
from ..common.ip_utils import IPUtils

logger = logging.getLogger(__name__)


class FileOperations:
    """Handles file-based operations for blacklist data"""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.blacklist_dir = os.path.join(data_dir, "blacklist_entries")
        self.detection_dir = os.path.join(data_dir, "by_detection_month")
        
        logger.info(f"FileOperations initialized with data_dir: {data_dir}")

    def update_file_storage(self, ips_data: List[Dict[str, Any]], source: str):
        """Update file-based storage for backward compatibility"""
        try:
            # Ensure directories exist
            os.makedirs(self.blacklist_dir, exist_ok=True)
            os.makedirs(self.detection_dir, exist_ok=True)

            # Update source file
            source_file = os.path.join(self.blacklist_dir, f"{source}.txt")
            with open(source_file, "w", encoding="utf-8") as f:
                ips_by_source = [
                    ip_data["ip"]
                    for ip_data in ips_data
                    if ip_data.get("source") == source
                ]
                f.write("\n".join(sorted(set(ips_by_source))))

            # Update monthly detection files
            ips_by_month = {}
            for ip_data in ips_data:
                detection_date = ip_data.get("detection_date")
                if detection_date:
                    try:
                        month_key = datetime.fromisoformat(detection_date).strftime("%Y-%m")
                        if month_key not in ips_by_month:
                            ips_by_month[month_key] = set()
                        ips_by_month[month_key].add(ip_data["ip"])
                    except ValueError:
                        logger.warning(f"Invalid detection date format: {detection_date}")

            for month_key, ips in ips_by_month.items():
                month_file = os.path.join(self.detection_dir, f"{month_key}.txt")
                with open(month_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(sorted(ips)))

        except Exception as e:
            logger.error(f"Error updating file storage: {e}")

    def get_active_ips_from_files(self) -> List[str]:
        """Fallback method to get IPs from files"""
        all_ips = set()

        # Load from blacklist directory
        if os.path.exists(self.blacklist_dir):
            for filename in os.listdir(self.blacklist_dir):
                if filename.endswith(".txt"):
                    file_path = os.path.join(self.blacklist_dir, filename)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            for line in f:
                                ip = line.strip()
                                if ip and IPUtils.validate_ip(ip):
                                    all_ips.add(ip)
                    except Exception as e:
                        logger.warning(f"Error reading {file_path}: {e}")

        # Load REGTECH IPs specifically
        regtech_ips = self._load_regtech_ips()
        all_ips.update(regtech_ips)

        return sorted(all_ips)

    def _load_regtech_ips(self) -> Set[str]:
        """Load REGTECH IPs from Excel files with robust parsing"""
        regtech_ips = set()

        try:
            import pandas as pd
        except ImportError:
            logger.warning("pandas not available, skipping REGTECH Excel parsing")
            return regtech_ips

        excel_patterns = ["regtech*.xlsx", "REGTECH*.xlsx", "*regtech*.xlsx"]

        for pattern in excel_patterns:
            for excel_file in glob.glob(
                os.path.join(self.data_dir, "**", pattern), recursive=True
            ):
                try:
                    df = pd.read_excel(excel_file)

                    # Look for IP columns
                    ip_columns = [
                        col
                        for col in df.columns
                        if "ip" in col.lower() or "주소" in col.lower()
                    ]

                    for col in ip_columns:
                        for ip in df[col].dropna():
                            ip_str = str(ip).strip()
                            if IPUtils.validate_ip(ip_str):
                                regtech_ips.add(ip_str)

                except Exception as e:
                    logger.warning(f"Error processing REGTECH Excel file {excel_file}: {e}")

        return regtech_ips

    def clear_file_data(self) -> Dict[str, Any]:
        """Clear file-based data"""
        cleared_items = {
            "files_removed": 0,
            "directories_cleaned": 0,
        }

        # Clear file-based data
        if os.path.exists(self.blacklist_dir):
            for filename in os.listdir(self.blacklist_dir):
                file_path = os.path.join(self.blacklist_dir, filename)
                try:
                    os.remove(file_path)
                    cleared_items["files_removed"] += 1
                except Exception as e:
                    logger.warning(f"Could not remove {file_path}: {e}")

        if os.path.exists(self.detection_dir):
            for filename in os.listdir(self.detection_dir):
                file_path = os.path.join(self.detection_dir, filename)
                try:
                    os.remove(file_path)
                    cleared_items["files_removed"] += 1
                except Exception as e:
                    logger.warning(f"Could not remove {file_path}: {e}")

            cleared_items["directories_cleaned"] = 2

        return cleared_items

    def get_file_stats(self) -> Dict[str, Any]:
        """Get statistics about file-based storage"""
        stats = {
            "blacklist_files": 0,
            "detection_files": 0,
            "total_size_bytes": 0,
        }

        if os.path.exists(self.blacklist_dir):
            for filename in os.listdir(self.blacklist_dir):
                if filename.endswith(".txt"):
                    stats["blacklist_files"] += 1
                    file_path = os.path.join(self.blacklist_dir, filename)
                    try:
                        stats["total_size_bytes"] += os.path.getsize(file_path)
                    except OSError:
                        pass

        if os.path.exists(self.detection_dir):
            for filename in os.listdir(self.detection_dir):
                if filename.endswith(".txt"):
                    stats["detection_files"] += 1
                    file_path = os.path.join(self.detection_dir, filename)
                    try:
                        stats["total_size_bytes"] += os.path.getsize(file_path)
                    except OSError:
                        pass

        return stats


if __name__ == "__main__":
    # Validation tests
    import sys
    import tempfile

    all_validation_failures = []
    total_tests = 0

    # Test 1: File operations instantiation
    total_tests += 1
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_ops = FileOperations(temp_dir)
            if hasattr(file_ops, 'data_dir') and hasattr(file_ops, 'blacklist_dir'):
                print("✅ FileOperations instantiation working")
            else:
                all_validation_failures.append("FileOperations missing required attributes")
    except Exception as e:
        all_validation_failures.append(f"FileOperations instantiation failed: {e}")

    # Test 2: File storage update functionality
    total_tests += 1
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_ops = FileOperations(temp_dir)
            test_ips = [
                {"ip": "192.168.1.1", "source": "test", "detection_date": "2025-01-01"},
                {"ip": "192.168.1.2", "source": "test", "detection_date": "2025-01-01"}
            ]
            
            # This should not raise an exception
            file_ops.update_file_storage(test_ips, "test")
            
            # Check if file was created
            source_file = os.path.join(file_ops.blacklist_dir, "test.txt")
            if os.path.exists(source_file):
                print("✅ File storage update working")
            else:
                all_validation_failures.append("File storage update did not create expected file")
    except Exception as e:
        all_validation_failures.append(f"File storage update failed: {e}")

    # Test 3: File statistics functionality
    total_tests += 1
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_ops = FileOperations(temp_dir)
            stats = file_ops.get_file_stats()
            expected_keys = ["blacklist_files", "detection_files", "total_size_bytes"]
            
            if all(key in stats for key in expected_keys):
                print("✅ File statistics functionality working")
            else:
                missing_keys = [key for key in expected_keys if key not in stats]
                all_validation_failures.append(f"File statistics missing keys: {missing_keys}")
    except Exception as e:
        all_validation_failures.append(f"File statistics failed: {e}")

    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("FileOperations module is validated and ready for use")
        sys.exit(0)