#!/usr/bin/env python3
"""
IP Search Service for Unified Blacklist Manager
"""

import ipaddress
import logging
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional

from ...utils.advanced_cache import EnhancedSmartCache
from ...utils.unified_decorators import unified_cache, unified_monitoring
from ..database import DatabaseManager

logger = logging.getLogger(__name__)


class SearchService:
    """Handles IP search operations for the blacklist manager"""

    def __init__(
        self, data_dir: str, db_manager: DatabaseManager, cache: EnhancedSmartCache
    ):
        self.data_dir = data_dir
        self.blacklist_dir = os.path.join(data_dir, "blacklist_ips")
        self.detection_dir = os.path.join(data_dir, "by_detection_month")
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

    @unified_monitoring("search_ip")
    def search_ip(self, ip: str, include_geo: bool = False) -> Dict[str, Any]:
        """Search for IP in blacklist with enhanced features"""
        try:
            # Validate IP address
            ipaddress.ip_address(ip)
        except ValueError:
            return {
                "ip": ip,
                "found": False,
                "error": "Invalid IP address format",
                "sources": [],
                "search_timestamp": datetime.now().isoformat(),
            }

        # Check cache first
        cache_key = "ip_search_{ip}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            logger.debug("Cache hit for IP search: {ip}")
            return cached_result

        # Search in files and database
        file_result = self._search_ip_in_files(ip)
        db_result = self._search_ip_in_database(ip)

        # Combine results
        found = file_result["found"] or (db_result is not None)
        sources = file_result["sources"]

        if db_result:
            sources.extend(db_result.get("sources", []))

        result = {
            "ip": ip,
            "found": found,
            "sources": list(set(sources)),  # Remove duplicates
            "search_timestamp": datetime.now().isoformat(),
        }

        # Add database metadata if available
        if db_result:
            result.update(
                {
                    "first_detection": db_result.get("first_detection"),
                    "last_detection": db_result.get("last_detection"),
                    "detection_count": db_result.get("detection_count", 0),
                    "country": db_result.get("country"),
                    "threat_type": db_result.get("threat_type"),
                    "confidence_score": db_result.get("confidence_score"),
                }
            )

        # Cache result
        self.cache.set(cache_key, result, ttl=300)  # 5 minute cache

        # Record search for analytics
        self._record_ip_search(ip, found)

        return result

    def _search_ip_in_files(self, ip: str) -> Dict[str, Any]:
        """Search IP in file-based blacklists"""
        found_sources = []

        try:
            # Search in blacklist directory
            if os.path.exists(self.blacklist_dir):
                for filename in os.listdir(self.blacklist_dir):
                    if filename.endswith(".txt"):
                        file_path = os.path.join(self.blacklist_dir, filename)
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                if ip in f.read():
                                    found_sources.append(filename.replace(".txt", ""))
                        except Exception as e:
                            logger.warning("Error reading {file_path}: {e}")
                            continue

            # Search in detection directory
            if os.path.exists(self.detection_dir):
                for filename in os.listdir(self.detection_dir):
                    if filename.endswith(".txt"):
                        file_path = os.path.join(self.detection_dir, filename)
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                content = f.read()
                                if ip in content:
                                    # Extract date from filename
                                    date_part = filename.replace(".txt", "")
                                    found_sources.append("detection_{date_part}")
                        except Exception as e:
                            logger.warning("Error reading {file_path}: {e}")
                            continue

        except Exception as e:
            logger.error("Error searching IP in files: {e}")

        return {
            "found": len(found_sources) > 0,
            "sources": found_sources,
        }

    def _search_ip_in_database(self, ip: str) -> Optional[Dict[str, Any]]:
        """Search IP in database with metadata"""
        try:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Search in ip_detections table
                cursor.execute(
                    """
                    SELECT
                        ip_address,
                        source,
                        detection_date,
                        country,
                        threat_type,
                        confidence_score,
                        is_active,
                        created_at,
                        updated_at
                    FROM ip_detections
                    WHERE ip_address = ? AND is_active = 1
                    ORDER BY detection_date DESC
                    """,
                    (ip,),
                )

                rows = cursor.fetchall()
                if not rows:
                    return None

                # Aggregate data from multiple detections
                sources = list(set(row["source"] for row in rows if row["source"]))
                detection_dates = [
                    datetime.fromisoformat(row["detection_date"])
                    for row in rows
                    if row["detection_date"]
                ]

                first_detection = min(detection_dates) if detection_dates else None
                last_detection = max(detection_dates) if detection_dates else None

                # Use data from most recent detection
                latest_row = rows[0]

                return {
                    "ip": ip,
                    "sources": sources,
                    "first_detection": (
                        first_detection.isoformat() if first_detection else None
                    ),
                    "last_detection": (
                        last_detection.isoformat() if last_detection else None
                    ),
                    "detection_count": len(rows),
                    "country": latest_row["country"],
                    "threat_type": latest_row["threat_type"],
                    "confidence_score": latest_row["confidence_score"],
                    "is_active": bool(latest_row["is_active"]),
                    "created_at": latest_row["created_at"],
                    "updated_at": latest_row["updated_at"],
                }

        except sqlite3.Error as e:
            logger.error("Database error during IP search: {e}")
            return None
        except Exception as e:
            logger.error("Unexpected error during database search: {e}")
            return None

    def _record_ip_search(self, ip: str, found: bool):
        """Record IP search for analytics"""
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                cursor = conn.cursor()

                # Create search_history table if it doesn't exist
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS search_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ip_address TEXT NOT NULL,
                        found BOOLEAN NOT NULL,
                        search_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        user_agent TEXT,
                        source_ip TEXT
                    )
                    """
                )

                # Insert search record
                cursor.execute(
                    """
                    INSERT INTO search_history (ip_address, found)
                    VALUES (?, ?)
                    """,
                    (ip, found),
                )

                conn.commit()
        except Exception as e:
            logger.warning("Failed to record search history: {e}")

    @unified_cache(ttl=600)
    def search_ips(
        self, ips: List[str], max_workers: int = 20, include_geo: bool = False
    ) -> Dict[str, Any]:
        """Bulk search for multiple IPs with concurrent processing"""
        start_time = datetime.now()
        results = []

        # Process IPs in batches to avoid overwhelming the system
        batch_size = min(max_workers, len(ips))

        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            # Submit all search tasks
            future_to_ip = {
                executor.submit(self.search_ip, ip, include_geo): ip for ip in ips
            }

            # Collect results as they complete
            for future in as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error("Error searching IP {ip}: {e}")
                    results.append(
                        {
                            "ip": ip,
                            "found": False,
                            "error": str(e),
                            "sources": [],
                            "search_timestamp": datetime.now().isoformat(),
                        }
                    )

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        # Calculate statistics
        found_count = sum(1 for r in results if r.get("found", False))

        return {
            "total_searched": len(ips),
            "found_count": found_count,
            "not_found_count": len(ips) - found_count,
            "processing_time_seconds": processing_time,
            "results": results,
            "search_timestamp": datetime.now().isoformat(),
        }
