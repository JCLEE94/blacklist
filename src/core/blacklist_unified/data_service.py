#!/usr/bin/env python3
"""
Data Management Service for Unified Blacklist Manager
"""

import ipaddress
import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .models import DataProcessingError
from ..database import DatabaseManager
from ...utils.advanced_cache import EnhancedSmartCache
from ...utils.unified_decorators import unified_cache, unified_monitoring

logger = logging.getLogger(__name__)


class DataService:
    """Handles data operations for the blacklist manager"""
    
    def __init__(self, data_dir: str, db_manager: DatabaseManager, cache: EnhancedSmartCache):
        self.data_dir = data_dir
        self.blacklist_dir = os.path.join(data_dir, "blacklist_ips")
        self.detection_dir = os.path.join(data_dir, "by_detection_month")
        self.db_manager = db_manager
        self.cache = cache
        self.lock = threading.RLock()
        
        # Set database path for direct SQLite access
        if hasattr(db_manager, 'db_url') and db_manager.db_url and "sqlite:///" in db_manager.db_url:
            self.db_path = db_manager.db_url.replace("sqlite:///", "")
        else:
            self.db_path = os.path.join(self.data_dir, "database.db")
    
    def _is_valid_ip(self, ip_str: str) -> bool:
        """Validate IP address format"""
        try:
            ipaddress.ip_address(ip_str.strip())
            return True
        except ValueError:
            return False
    
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
        
        # Process in batches
        processed = 0
        errors = []
        
        try:
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                cursor = conn.cursor()
                
                # Ensure table exists
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ip_detections (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ip_address TEXT NOT NULL,
                        source TEXT,
                        detection_date TEXT,
                        country TEXT,
                        threat_type TEXT,
                        confidence_score REAL DEFAULT 1.0,
                        is_active INTEGER DEFAULT 1,
                        expires_at DATETIME,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                
                # Process in batches
                for i in range(0, len(valid_ips), batch_size):
                    batch = valid_ips[i:i + batch_size]
                    
                    try:
                        # Prepare batch data
                        batch_data = []
                        for ip_data in batch:
                            batch_data.append((
                                ip_data["ip"],
                                ip_data.get("source", source),
                                ip_data.get("detection_date"),
                                ip_data.get("country"),
                                ip_data.get("threat_type"),
                                ip_data.get("confidence_score", 1.0),
                                ip_data.get("is_active", 1),
                                ip_data.get("expires_at"),
                                datetime.now(),
                                datetime.now(),
                            ))
                        
                        # Batch insert with upsert logic
                        cursor.executemany(
                            """
                            INSERT OR REPLACE INTO ip_detections (
                                ip_address, source, detection_date, country,
                                threat_type, confidence_score, is_active,
                                expires_at, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            batch_data,
                        )
                        
                        processed += len(batch)
                        logger.debug(f"Processed batch {i//batch_size + 1}, total: {processed}")
                        
                    except Exception as e:
                        error_msg = f"Error processing batch {i//batch_size + 1}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                
                conn.commit()
                
                # Update file-based storage
                self._update_file_storage(valid_ips, source)
                
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
    
    def _update_file_storage(self, ips_data: List[Dict[str, Any]], source: str):
        """Update file-based storage for backward compatibility"""
        try:
            # Ensure directories exist
            os.makedirs(self.blacklist_dir, exist_ok=True)
            os.makedirs(self.detection_dir, exist_ok=True)
            
            # Update source file
            source_file = os.path.join(self.blacklist_dir, f"{source}.txt")
            with open(source_file, "w", encoding="utf-8") as f:
                ips_by_source = [ip_data["ip"] for ip_data in ips_data if ip_data.get("source") == source]
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
    
    @unified_cache(ttl=300)
    def get_active_ips(self) -> List[str]:
        """Get all active IP addresses from database"""
        try:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    SELECT DISTINCT ip_address 
                    FROM ip_detections 
                    WHERE is_active = 1 
                      AND (expires_at IS NULL OR expires_at > datetime('now'))
                    ORDER BY ip_address
                    """
                )
                
                return [row[0] for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Database error getting active IPs: {e}")
            # Fallback to file-based method
            return self._get_active_ips_from_files()
    
    def _get_active_ips_from_files(self) -> List[str]:
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
                                if ip and self._is_valid_ip(ip):
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
            import glob
            for excel_file in glob.glob(os.path.join(self.data_dir, "**", pattern), recursive=True):
                try:
                    df = pd.read_excel(excel_file)
                    
                    # Look for IP columns
                    ip_columns = [col for col in df.columns if "ip" in col.lower() or "주소" in col.lower()]
                    
                    for col in ip_columns:
                        for ip in df[col].dropna():
                            ip_str = str(ip).strip()
                            if self._is_valid_ip(ip_str):
                                regtech_ips.add(ip_str)
                    
                except Exception as e:
                    logger.warning(f"Error processing REGTECH Excel file {excel_file}: {e}")
        
        return regtech_ips
    
    @unified_cache(ttl=600)
    def get_all_active_ips(self) -> List[Dict[str, Any]]:
        """Get all active IPs with metadata"""
        try:
            with sqlite3.connect(self.db_path, timeout=15) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    SELECT 
                        ip_address,
                        source,
                        detection_date,
                        country,
                        threat_type,
                        confidence_score,
                        created_at,
                        updated_at,
                        expires_at
                    FROM ip_detections 
                    WHERE is_active = 1 
                      AND (expires_at IS NULL OR expires_at > datetime('now'))
                    ORDER BY updated_at DESC, ip_address
                    """
                )
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        "ip": row["ip_address"],
                        "source": row["source"],
                        "detection_date": row["detection_date"],
                        "country": row["country"],
                        "threat_type": row["threat_type"],
                        "confidence_score": row["confidence_score"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                        "expires_at": row["expires_at"],
                    })
                
                return results
                
        except sqlite3.Error as e:
            logger.error(f"Database error getting all active IPs: {e}")
            # Fallback to simple IP list
            simple_ips = self.get_active_ips()
            return [{"ip": ip, "source": "unknown", "detection_date": None} for ip in simple_ips]
    
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
            # Clear database
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                cursor = conn.cursor()
                
                # Count records before deletion
                cursor.execute("SELECT COUNT(*) FROM ip_detections WHERE is_active = 1")
                cleared_items["database_records"] = cursor.fetchone()[0]
                
                # Mark all records as inactive instead of deleting
                cursor.execute(
                    "UPDATE ip_detections SET is_active = 0, updated_at = ? WHERE is_active = 1",
                    (datetime.now(),)
                )
                
                conn.commit()
            
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
    
    def cleanup_old_data(self, days: int = 365):
        """Clean up old data beyond specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                cursor = conn.cursor()
                
                # Count records to be cleaned
                cursor.execute(
                    "SELECT COUNT(*) FROM ip_detections WHERE created_at < ?",
                    (cutoff_date,)
                )
                count = cursor.fetchone()[0]
                
                # Mark old records as inactive
                cursor.execute(
                    "UPDATE ip_detections SET is_active = 0, updated_at = ? WHERE created_at < ? AND is_active = 1",
                    (datetime.now(), cutoff_date)
                )
                
                conn.commit()
                
                logger.info(f"Cleaned up {count} records older than {days} days")
                return {"cleaned_records": count, "cutoff_date": cutoff_date.isoformat()}
                
        except sqlite3.Error as e:
            logger.error(f"Error during cleanup: {e}")
            return {"error": str(e)}
