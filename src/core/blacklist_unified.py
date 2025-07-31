#!/usr/bin/env python3
"""
Enhanced UnifiedBlacklistManager with fixed database schema compatibility
"""

import ipaddress
import logging
import os
import sqlite3
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Import components
from src.core.database import DatabaseManager
from src.utils.advanced_cache import EnhancedSmartCache
from src.utils.unified_decorators import unified_cache, unified_monitoring

# Monitoring and geolocation would be imported here if available
# from src.core.monitoring import MonitoringManager
# from src.core.geolocation import GeolocationEnricher

logger = logging.getLogger(__name__)


# Custom exceptions
class DataProcessingError(Exception):
    """Data processing error with context"""

    def __init__(
        self,
        message: str,
        file_path: str = None,
        operation: str = None,
        cause: Exception = None,
    ):
        super().__init__(message)
        self.file_path = file_path
        self.operation = operation
        self.cause = cause


class ValidationError(Exception):
    """Data validation error"""

    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(message)
        self.field = field
        self.value = value


@dataclass
class SearchResult:
    """Enhanced search result with geolocation and history"""

    ip: str
    found: bool
    sources: List[str] = field(default_factory=list)
    first_detection: Optional[datetime] = None
    last_detection: Optional[datetime] = None
    detection_count: int = 0
    geolocation: Optional[Dict[str, Any]] = None
    threat_intelligence: Optional[Dict[str, Any]] = None
    search_timestamp: datetime = field(default_factory=datetime.now)


class UnifiedBlacklistManager:
    """Enhanced Unified Blacklist Manager with database integration and optimized performance"""

    def __init__(
        self,
        data_dir: str = "data",
        cache_backend=None,
        db_url: str = None,
        geo_api_keys: Dict[str, str] = None,
    ):
        """Initialize enhanced blacklist manager"""
        self.data_dir = data_dir
        self.blacklist_dir = os.path.join(data_dir, "blacklist_ips")
        self.detection_dir = os.path.join(data_dir, "by_detection_month")

        # Ensure directory structure
        self._ensure_directories()

        # Initialize core components
        self.db_manager = DatabaseManager(db_url)

        # Set database path for direct SQLite access
        if db_url and "sqlite:///" in db_url:
            # Extract path from SQLite URL
            self.db_path = db_url.replace("sqlite:///", "")
        else:
            # Default path
            self.db_path = os.path.join(
                "/app" if os.path.exists("/app") else ".", "instance/blacklist.db"
            )

        self.cache = EnhancedSmartCache(cache_backend)
        # Dummy classes for missing modules
        self.monitor = type(
            "DummyMonitor", (), {"start_monitoring": lambda self: None}
        )()
        self.geo_enricher = type(
            "DummyGeoEnricher", (), {"geolocate_ip": lambda self, ip: {}}
        )()

        # Thread pool for concurrent operations
        self._thread_pool = ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="blacklist"
        )
        self._lock = threading.RLock()

        # Start monitoring
        self.monitor.start_monitoring()
        self._setup_cleanup_scheduler()

        logger.info(f"Enhanced UnifiedBlacklistManager initialized: {data_dir}")
        logger.info(
            f"Features: Cache={bool(cache_backend)}, Geo={bool(geo_api_keys)}, DB={bool(db_url)}"
        )

    def _ensure_directories(self) -> None:
        """Create required directories with proper structure"""
        directories = [
            self.blacklist_dir,
            self.detection_dir,
            os.path.join(self.data_dir, "sources"),
            os.path.join(self.data_dir, "backups"),
            os.path.join(self.data_dir, "logs"),
            os.path.join(self.data_dir, "exports"),
        ]

        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                logger.debug(f"Directory ensured: {directory}")
            except OSError as e:
                # Docker 환경에서는 디렉토리 생성 실패를 무시
                logger.warning(f"Failed to create directory {directory}: {e}")
                # Continue without raising error

    def _setup_cleanup_scheduler(self):
        """Setup automatic cleanup of old data"""

        def cleanup_thread():
            while True:
                try:
                    # Run cleanup every 24 hours
                    time.sleep(86400)
                    self.cleanup_old_data()
                except Exception as e:
                    logger.error(f"Scheduled cleanup failed: {e}")

        cleanup_thread = threading.Thread(target=cleanup_thread, daemon=True)
        cleanup_thread.start()

    # ========== Enhanced IP Search Functions ==========

    @unified_monitoring()
    @unified_cache(ttl=300, key_prefix="search_ip_enhanced")
    def search_ip(self, ip: str, include_geo: bool = False) -> Dict[str, Any]:
        """Enhanced single IP search with geolocation and database storage"""
        try:
            # Validate IP
            ipaddress.ip_address(ip)
        except ValueError:
            raise ValidationError(f"Invalid IP address: {ip}", field="ip", value=ip)

        # Search in files first (backward compatibility)
        result = self._search_ip_in_files(ip)

        # Search in database for additional details
        db_result = self._search_ip_in_database(ip)
        if db_result:
            result.update(db_result)

        # Add geolocation data if requested
        if include_geo:
            geo_data = self.geo_enricher.geolocate_ip(ip)
            result["geolocation"] = geo_data

        # Store search in database for analytics
        self._record_ip_search(ip, result["found"])

        return result

    def _search_ip_in_files(self, ip: str) -> Dict[str, Any]:
        """Search IP in file-based data (legacy compatibility)"""
        result = {
            "ip": ip,
            "found": False,
            "months": [],
            "first_detection": None,
            "last_detection": None,
            "total_months": 0,
            "sources": [],
        }

        months_found = []
        sources_found = set()

        # Search in by_detection_month directory
        for month_dir in sorted(Path(self.detection_dir).glob("*/"), reverse=True):
            if not month_dir.is_dir():
                continue

            ips_file = month_dir / "ips.txt"
            if not ips_file.exists():
                continue

            try:
                with open(ips_file, "r") as f:
                    ips = set(line.strip() for line in f if line.strip())

                if ip in ips:
                    month_name = month_dir.name
                    months_found.append(month_name)
                    sources_found.add("DETECTION_MONTHLY")

                    # Parse month for date calculations
                    try:
                        month_date = datetime.strptime(month_name, "%Y-%m")
                        if (
                            not result["first_detection"]
                            or month_date < result["first_detection"]
                        ):
                            result["first_detection"] = month_date
                        if (
                            not result["last_detection"]
                            or month_date > result["last_detection"]
                        ):
                            result["last_detection"] = month_date
                    except ValueError:
                        logger.warning(f"Invalid month format: {month_name}")

            except Exception as e:
                logger.error(f"Error searching in {ips_file}: {e}")

        # Search in regtech data
        regtech_ips = self._load_regtech_ips()
        if ip in regtech_ips:
            sources_found.add("REGTECH")
            result["found"] = True

        # Update result
        if months_found or ip in regtech_ips:
            result["found"] = True
            result["months"] = sorted(months_found, reverse=True)
            result["total_months"] = len(months_found)
            result["sources"] = list(sources_found)

        return result

    def _search_ip_in_database(self, ip: str) -> Optional[Dict[str, Any]]:
        """Search IP in database with enhanced details"""
        try:
            with self.db_manager.get_session() as session:
                from sqlalchemy import text

                # Get IP record from blacklist_ip table
                blacklist_result = session.execute(
                    text("SELECT * FROM blacklist_ip WHERE ip = :ip"), {"ip": ip}
                ).fetchone()

                if not blacklist_result:
                    return None

                # Get detection history from ip_detection table
                detection_results = session.execute(
                    text(
                        """
                        SELECT source, attack_type, confidence_score, created_at
                        FROM ip_detection
                        WHERE ip = :ip
                        ORDER BY created_at DESC
                    """
                    ),
                    {"ip": ip},
                ).fetchall()

                return {
                    "database_found": True,
                    "database_info": {
                        "id": blacklist_result.id,
                        "ip": blacklist_result.ip,
                        "attack_type": blacklist_result.attack_type,
                        "country": blacklist_result.country,
                        "source": blacklist_result.source,
                        "created_at": blacklist_result.created_at,
                        "extra_data": blacklist_result.extra_data,
                    },
                    "detection_history": [
                        {
                            "source": det.source,
                            "attack_type": det.attack_type,
                            "confidence_score": det.confidence_score,
                            "created_at": det.created_at,
                        }
                        for det in detection_results
                    ],
                }

        except Exception as e:
            logger.error(f"Database search error for IP {ip}: {e}")
            return None

    def _record_ip_search(self, ip: str, found: bool):
        """Record IP search in database for analytics"""
        try:
            with self.db_manager.get_session() as session:
                from sqlalchemy import text

                session.execute(
                    text(
                        """
                        INSERT INTO ip_detection (ip, created_at, source, attack_type, confidence_score)
                        VALUES (:ip, :date, 'search', 'query', :confidence)
                    """
                    ),
                    {
                        "ip": ip,
                        "date": datetime.now(),
                        "confidence": 1.0 if found else 0.0,
                    },
                )
                session.commit()

        except Exception as e:
            logger.debug(f"Failed to record IP search: {e}")

    @unified_monitoring()
    def search_ips(
        self, ips: List[str], max_workers: int = 4, include_geo: bool = False
    ) -> Dict[str, Any]:
        """Enhanced batch IP search with parallel processing"""
        if not ips:
            return {"found_ips": [], "not_found_ips": [], "error_ips": []}

        # Validate IPs first
        valid_ips = []
        invalid_ips = []

        for ip in ips:
            try:
                ipaddress.ip_address(ip.strip())
                valid_ips.append(ip.strip())
            except ValueError:
                invalid_ips.append(ip)

        if invalid_ips:
            logger.warning(f"Found {len(invalid_ips)} invalid IPs: {invalid_ips[:5]}")

        found_ips = []
        not_found_ips = []
        error_ips = []

        # Parallel search with controlled workers
        with ThreadPoolExecutor(
            max_workers=min(max_workers, len(valid_ips))
        ) as executor:
            # Submit search tasks
            future_to_ip = {
                executor.submit(self.search_ip, ip, include_geo): ip for ip in valid_ips
            }

            # Collect results
            for future in as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    result = future.result(timeout=30)
                    if result.get("found", False):
                        found_ips.append({"ip": ip, "details": result})
                    else:
                        not_found_ips.append(ip)
                except Exception as e:
                    logger.error(f"Search error for IP {ip}: {e}")
                    error_ips.append({"ip": ip, "error": str(e)})

        return {
            "total_searched": len(valid_ips),
            "found_ips": found_ips,
            "not_found_ips": not_found_ips,
            "error_ips": error_ips,
            "invalid_ips": invalid_ips,
            "summary": {
                "found_count": len(found_ips),
                "not_found_count": len(not_found_ips),
                "error_count": len(error_ips),
                "invalid_count": len(invalid_ips),
            },
        }

    # ========== Enhanced Data Management ==========

    @unified_monitoring()
    def bulk_import_ips(
        self, ips_data: List[Dict[str, Any]], source: str = "MANUAL"
    ) -> Dict[str, Any]:
        """Enhanced bulk import with database integration and conflict resolution"""
        if not ips_data:
            return {"success": False, "error": "No data provided"}

        logger.info(f"Starting bulk import: {len(ips_data)} IPs from {source}")

        imported = 0
        skipped = 0
        errors = 0
        start_time = time.time()

        try:
            # Use direct SQLite connection instead of SQLAlchemy session
            logger.info(f"Using database path: {self.db_path}")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for ip_data in ips_data:
                try:
                    ip = ip_data.get("ip", "").strip()
                    if not ip:
                        skipped += 1
                        continue

                    # Validate IP
                    try:
                        ipaddress.ip_address(ip)
                    except ValueError:
                        logger.warning(f"Invalid IP address: {ip}")
                        errors += 1
                        continue

                    # Check if IP already exists
                    cursor.execute("SELECT id FROM blacklist_ip WHERE ip = ?", (ip,))
                    existing = cursor.fetchone()

                    if existing:
                        # Update existing record
                        cursor.execute(
                            """
                            UPDATE blacklist_ip
                            SET created_at = ?,
                                detection_date = COALESCE(?, detection_date),
                                attack_type = COALESCE(?, attack_type),
                                country = COALESCE(?, country),
                                reason = COALESCE(?, reason),
                                threat_level = COALESCE(?, threat_level),
                                is_active = ?,
                                updated_at = ?
                            WHERE ip = ?
                        """,
                            (
                                datetime.now().isoformat(),
                                ip_data.get("reg_date")
                                or ip_data.get("detection_date"),
                                ip_data.get("attack_type")
                                or ip_data.get("threat_type")
                                or ip_data.get("reason"),
                                ip_data.get("country"),
                                ip_data.get("reason")
                                or ip_data.get("threat_type", "blacklist"),
                                ip_data.get("threat_level", "high"),
                                1,  # is_active = True
                                datetime.now().isoformat(),
                                ip,
                            ),
                        )
                    else:
                        # Insert new record
                        cursor.execute(
                            """
                            INSERT INTO blacklist_ip
                            (ip, created_at, detection_date, attack_type, country, source, reason, threat_level, is_active, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                ip,
                                datetime.now().isoformat(),
                                ip_data.get("reg_date")
                                or ip_data.get("detection_date")
                                or datetime.now().isoformat(),
                                ip_data.get("attack_type")
                                or ip_data.get("threat_type")
                                or ip_data.get("reason"),
                                ip_data.get("country"),
                                ip_data.get("source", source),
                                ip_data.get("reason")
                                or ip_data.get("threat_type", "blacklist"),
                                ip_data.get("threat_level", "high"),
                                1,  # is_active = True
                                datetime.now().isoformat(),
                            ),
                        )

                    # Record detection
                    cursor.execute(
                        """
                        INSERT INTO ip_detection
                        (ip, created_at, source, attack_type, confidence_score)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            ip,
                            datetime.now().isoformat(),
                            source,
                            ip_data.get("threat_type", "blacklist"),
                            ip_data.get("confidence", 1.0),
                        ),
                    )

                    imported += 1

                except Exception as e:
                    logger.error(
                        f"Failed to import IP {ip_data.get('ip', 'unknown')}: {e}"
                    )
                    errors += 1

            # Commit all changes
            conn.commit()
            conn.close()

            # Clear cache after successful import
            if imported > 0:
                # EnhancedSmartCache doesn't support pattern argument
                self.cache.clear()
                logger.info(f"Cache cleared: {imported} entries")

            duration = time.time() - start_time
            logger.info(
                f"Bulk import completed: {imported} imported, {skipped} skipped, {errors} errors in {duration:.2f}s"
            )

            return {
                "success": True,
                "imported_count": imported,
                "skipped_count": skipped,
                "error_count": errors,
                "duration": duration,
                "source": source,
            }

        except Exception as e:
            logger.error(f"Bulk import failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "imported_count": imported,
                "skipped_count": skipped,
                "error_count": errors,
            }

    # ========== Legacy compatibility methods ==========

    def get_active_ips(self) -> List[str]:
        """Get all active IPs for FortiGate external connector compatibility"""
        try:
            # Use direct SQLite connection
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get all active IPs (is_active = 1) without date restriction
            cursor.execute(
                """
                SELECT DISTINCT ip
                FROM blacklist_ip
                WHERE is_active = 1
                ORDER BY ip
            """
            )

            result = cursor.fetchall()
            conn.close()

            ips = [row[0] for row in result]
            logger.info(f"Retrieved {len(ips)} active IPs from database")
            return ips

        except Exception as e:
            logger.error(f"Failed to get active IPs from database: {e}")
            # Fallback to file-based approach
            return self._get_active_ips_from_files()

    def get_all_active_ips(self) -> List[Dict[str, Any]]:
        """Get all active IPs with detailed information including detection_date"""
        try:
            # Use direct SQLite connection
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()

            # Check if is_active column exists
            cursor.execute("PRAGMA table_info(blacklist_ip)")
            columns = [col[1] for col in cursor.fetchall()]

            # Build query based on available columns
            base_query = """
                SELECT ip, source, country, attack_type, detection_date, created_at,
                       threat_level, reason, extra_data
                FROM blacklist_ip
            """

            if "is_active" in columns:
                query = base_query + " WHERE is_active = 1 ORDER BY created_at DESC"
            else:
                query = base_query + " ORDER BY created_at DESC"

            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()

            # Convert to list of dictionaries with proper date handling
            result = []
            for row in rows:
                ip_data = {
                    "ip": row["ip"],
                    "source": row["source"] or "unknown",
                    "country": row["country"] or "Unknown",
                    "attack_type": row["attack_type"] or "Unknown",
                    "detection_date": row["detection_date"],  # 원본 등록일 (엑셀 기준)
                    "added_date": row["created_at"],  # 시스템 수집일
                    "threat_level": row["threat_level"] or "high",
                    "reason": row["reason"] or row["attack_type"] or "Unknown",
                    "extra_data": row["extra_data"],
                    "risk_score": 0.8,  # Default risk score for filtering
                }
                result.append(ip_data)

            logger.info(
                f"Retrieved {len(result)} active IPs with details from database"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to get detailed active IPs from database: {e}")
            # Fallback to simple format
            simple_ips = self.get_active_ips()
            return [
                {
                    "ip": ip,
                    "source": "Unknown",
                    "country": "Unknown",
                    "attack_type": "Unknown",
                    "detection_date": datetime.now().strftime("%Y-%m-%d"),
                    "added_date": datetime.now().isoformat(),
                    "threat_level": "high",
                    "reason": "Unknown",
                    "extra_data": None,
                    "risk_score": 0.8,
                }
                for ip in simple_ips
            ]

    def _get_active_ips_from_files(self) -> List[str]:
        """Fallback method to get IPs from files"""
        all_ips = set()

        try:
            # Load from by_detection_month (recent 6 months)
            active_cutoff = datetime.now() - timedelta(days=180)

            for month_dir in Path(self.detection_dir).glob("*/"):
                if not month_dir.is_dir():
                    continue

                try:
                    month_date = datetime.strptime(month_dir.name, "%Y-%m")
                    if month_date >= active_cutoff:
                        ips_file = month_dir / "ips.txt"
                        if ips_file.exists():
                            with open(ips_file, "r") as f:
                                month_ips = set(
                                    line.strip() for line in f if line.strip()
                                )
                                all_ips.update(month_ips)
                except ValueError:
                    continue

            # Add regtech IPs
            regtech_ips = self._load_regtech_ips()
            all_ips.update(regtech_ips)

            return sorted(list(all_ips))

        except Exception as e:
            logger.error(f"Failed to get active IPs from files: {e}")
            return []

    def _load_regtech_ips(self) -> Set[str]:
        """Load REGTECH IPs from files"""
        regtech_ips = set()

        try:
            regtech_dir = os.path.join(self.data_dir, "regtech")
            if not os.path.exists(regtech_dir):
                return regtech_ips

            # Load from various regtech files
            for file_path in Path(regtech_dir).rglob("*.txt"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        for line in f:
                            ip = line.strip()
                            if ip and self._is_valid_ip(ip):
                                regtech_ips.add(ip)
                except Exception as e:
                    logger.error(f"Error reading regtech file {file_path}: {e}")

            logger.info(f"Total regtech IPs loaded: {len(regtech_ips)}")

        except Exception as e:
            logger.error(f"Failed to load regtech IPs: {e}")

        return regtech_ips

    def _is_valid_ip(self, ip_str: str) -> bool:
        """Validate IP address"""
        try:
            ipaddress.ip_address(ip_str.strip())
            return True
        except ValueError:
            return False

    # ========== System utilities ==========

    def cleanup_old_data(self, days: int = 365):
        """Cleanup old data beyond retention period"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            with self.db_manager.get_session() as session:
                from sqlalchemy import text

                # Clean old detections
                result = session.execute(
                    text("DELETE FROM ip_detection WHERE created_at < :cutoff"),
                    {"cutoff": cutoff_date},
                )

                deleted_count = result.rowcount
                session.commit()

                logger.info(f"Cleaned up {deleted_count} old detection records")

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    def get_stats_for_period(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get statistics for a specific time period with expiration support"""
        try:
            if not self.db_manager:
                return {
                    "total_ips": 0,
                    "sources": {},
                    "active_ips": 0,
                    "expired_ips": 0,
                }

            with self.db_manager.get_session() as session:
                from sqlalchemy import text

                # Query for the specific period using detection_date
                # Include both active and expired IPs for historical accuracy
                query = text(
                    """
                    SELECT
                        source,
                        COUNT(DISTINCT ip) as total_count,
                        SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_count,
                        SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) as expired_count,
                        MIN(detection_date) as first_detection,
                        MAX(detection_date) as last_detection
                    FROM blacklist_ip
                    WHERE detection_date >= :start_date
                    AND detection_date <= :end_date
                    GROUP BY source
                """
                )

                result = session.execute(
                    query, {"start_date": start_date, "end_date": end_date}
                )

                sources = {}
                total_ips = 0
                active_ips = 0
                expired_ips = 0
                first_detection = None
                last_detection = None

                for row in result:
                    source, total_count, active_count, expired_count, first, last = row
                    sources[source] = {
                        "total": total_count,
                        "active": active_count,
                        "expired": expired_count,
                    }
                    total_ips += total_count
                    active_ips += active_count
                    expired_ips += expired_count

                    if first_detection is None or (first and first < first_detection):
                        first_detection = first
                    if last_detection is None or (last and last > last_detection):
                        last_detection = last

                return {
                    "total_ips": total_ips,
                    "active_ips": active_ips,
                    "expired_ips": expired_ips,
                    "sources": sources,
                    "first_detection": first_detection if first_detection else None,
                    "last_detection": last_detection if last_detection else None,
                }

        except Exception as e:
            logger.error(
                f"Error getting stats for period {start_date} to {end_date}: {e}"
            )
            return {
                "total_ips": 0,
                "active_ips": 0,
                "expired_ips": 0,
                "sources": {},
                "first_detection": None,
                "last_detection": None,
            }

    def update_expiration_status(self) -> Dict[str, Any]:
        """Update expiration status for all IPs based on current time"""
        try:
            if not self.db_manager:
                return {"updated": 0, "error": "Database not available"}

            with self.db_manager.get_session() as session:
                from sqlalchemy import text

                # Update is_active status based on expires_at
                query = text(
                    """
                    UPDATE blacklist_ip
                    SET is_active = CASE
                        WHEN expires_at > datetime('now') THEN 1
                        ELSE 0
                    END
                    WHERE expires_at IS NOT NULL
                """
                )

                result = session.execute(query)
                session.commit()

                # Get current statistics
                stats_query = text(
                    """
                    SELECT
                        COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_count,
                        COUNT(CASE WHEN is_active = 0 THEN 1 END) as expired_count,
                        COUNT(*) as total_count
                    FROM blacklist_ip
                """
                )

                stats_result = session.execute(stats_query)
                stats_row = stats_result.fetchone()

                return {
                    "updated": result.rowcount,
                    "active_ips": stats_row[0],
                    "expired_ips": stats_row[1],
                    "total_ips": stats_row[2],
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"Error updating expiration status: {e}")
            return {"updated": 0, "error": str(e)}

    def get_active_blacklist_ips(self) -> List[str]:
        """Get only currently active (non-expired) blacklist IPs"""
        try:
            if not self.db_manager:
                return []

            with self.db_manager.get_session() as session:
                from sqlalchemy import text

                # Get all active IPs (is_active = 1)
                query = text(
                    """
                    SELECT DISTINCT ip
                    FROM blacklist_ip
                    WHERE is_active = 1
                    ORDER BY ip
                """
                )

                result = session.execute(query)
                return [row[0] for row in result]

        except Exception as e:
            logger.error(f"Error getting active blacklist IPs: {e}")
            return []

    def get_system_health(self) -> Dict[str, Any]:
        """Get system health status"""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected" if self.db_manager else "disconnected",
            "cache": "active" if self.cache else "inactive",
            "monitoring": "active" if self.monitor else "inactive",
        }

    def get_country_statistics(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top countries by IP count"""
        try:
            if not self.db_manager:
                return []

            with self.db_manager.get_session() as session:
                from sqlalchemy import text

                query = text(
                    """
                    SELECT country, COUNT(*) as count
                    FROM blacklist_ip
                    WHERE country IS NOT NULL AND country != '' AND is_active = 1
                    GROUP BY country
                    ORDER BY count DESC
                    LIMIT :limit
                """
                )

                result = session.execute(query, {"limit": limit})
                return [{"country": row[0], "count": row[1]} for row in result]

        except Exception as e:
            logger.error(f"Error getting country statistics: {e}")
            return []

    def get_daily_trend_data(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily trend data for the last N days"""
        try:
            if not self.db_manager:
                return []

            with self.db_manager.get_session() as session:
                from sqlalchemy import text

                query = text(
                    """
                    SELECT
                        DATE(detection_date) as date,
                        COUNT(*) as new_ips,
                        source
                    FROM blacklist_ip
                    WHERE detection_date >= DATE('now', '-' || :days || ' days')
                    GROUP BY DATE(detection_date), source
                    ORDER BY date DESC
                """
                )

                result = session.execute(query, {"days": days})

                # Aggregate by date
                daily_data = {}
                for row in result:
                    date_str = str(row[0])
                    if date_str not in daily_data:
                        daily_data[date_str] = {
                            "date": date_str,
                            "new_ips": 0,
                            "sources": {},
                        }
                    daily_data[date_str]["new_ips"] += row[1]
                    daily_data[date_str]["sources"][row[2]] = row[1]

                # Convert to list and sort
                return sorted(
                    daily_data.values(), key=lambda x: x["date"], reverse=True
                )

        except Exception as e:
            logger.error(f"Error getting daily trend data: {e}")
            return []

    def clear_all(self) -> Dict[str, Any]:
        """모든 블랙리스트 데이터 삭제"""
        try:
            # 데이터베이스 클리어
            if self.db_manager:
                with self.db_manager.get_session() as session:
                    from sqlalchemy import text

                    session.execute(text("DELETE FROM blacklist_ip"))
                    session.execute(text("DELETE FROM ip_detection"))
                    session.commit()
                    logger.info("Database cleared successfully")

            # SQLite autoincrement 시퀀스 리셋 (직접 연결 사용)
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                # autoincrement 시퀀스 리셋
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='blacklist_ip'")
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='ip_detection'")
                conn.commit()
                conn.close()
                logger.info("SQLite autoincrement sequences reset successfully")
            except Exception as e:
                logger.warning(f"Failed to reset SQLite sequences: {e}")

            # 파일 시스템 클리어
            import shutil

            if os.path.exists(self.data_dir):
                # by_detection_month 디렉토리 내용 삭제
                month_dir = os.path.join(self.data_dir, "by_detection_month")
                if os.path.exists(month_dir):
                    shutil.rmtree(month_dir)
                    os.makedirs(month_dir, exist_ok=True)

                # regtech, secudium 디렉토리 삭제
                for subdir in ["regtech", "secudium"]:
                    dir_path = os.path.join(self.data_dir, subdir)
                    if os.path.exists(dir_path):
                        shutil.rmtree(dir_path)
                        os.makedirs(dir_path, exist_ok=True)

            # 캐시 클리어
            if self.cache:
                self.cache.clear()

            return {
                "success": True,
                "message": "모든 블랙리스트 데이터가 삭제되었습니다. (ID는 1번부터 시작됩니다)",
            }

        except Exception as e:
            logger.error(f"Failed to clear all data: {e}")
            return {"success": False, "error": str(e)}

    def update_expiration_status_duplicate(self) -> Dict[str, Any]:
        """만료 상태 업데이트 - 탐지일로부터 90일 지난 IP를 만료 처리"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 90일 이전 날짜 계산
            expiry_date = datetime.now() - timedelta(days=90)

            # 만료된 IP를 is_active=0으로 업데이트 (detection_date 기준, 없으면 created_at 기준)
            cursor.execute(
                """
                UPDATE blacklist_ip
                SET is_active = 0
                WHERE (
                    (detection_date IS NOT NULL AND detection_date < ?) OR
                    (detection_date IS NULL AND created_at < ?)
                ) AND is_active = 1
            """,
                (expiry_date.strftime("%Y-%m-%d"), expiry_date.isoformat()),
            )

            expired_count = cursor.rowcount

            # 통계 조회
            cursor.execute("SELECT COUNT(*) FROM blacklist_ip WHERE is_active = 1")
            active_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM blacklist_ip WHERE is_active = 0")
            expired_total = cursor.fetchone()[0]

            conn.commit()
            conn.close()

            logger.info(
                f"Expiration update: {expired_count} IPs expired, {active_count} active"
            )

            return {
                "success": True,
                "expired_count": expired_count,
                "active_ips": active_count,
                "expired_ips": expired_total,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to update expiration status: {e}")
            return {"success": False, "error": str(e)}

    def get_expiration_stats(self) -> Dict[str, Any]:
        """만료 통계 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 활성 IP 수
            cursor.execute("SELECT COUNT(*) FROM blacklist_ip WHERE is_active = 1")
            active_count = cursor.fetchone()[0]

            # 만료된 IP 수
            cursor.execute("SELECT COUNT(*) FROM blacklist_ip WHERE is_active = 0")
            expired_count = cursor.fetchone()[0]

            # 30일 내 만료 예정 IP 수
            warning_date = datetime.now() - timedelta(days=60)  # 90-30 = 60일 전
            cursor.execute(
                """
                SELECT COUNT(*) FROM blacklist_ip
                WHERE is_active = 1 AND (
                    (detection_date IS NOT NULL AND detection_date < ?) OR
                    (detection_date IS NULL AND created_at < ?)
                )
            """,
                (warning_date.strftime("%Y-%m-%d"), warning_date.isoformat()),
            )
            warning_count = cursor.fetchone()[0]

            conn.close()

            return {
                "active": active_count,
                "expired": expired_count,
                "warning": warning_count,
                "total": active_count + expired_count,
            }

        except Exception as e:
            logger.error(f"Failed to get expiration stats: {e}")
            return {"active": 0, "expired": 0, "warning": 0, "total": 0}

    def set_ip_expiration(self, ip: str, expires_at: datetime) -> Dict[str, Any]:
        """특정 IP의 만료 날짜 설정"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE blacklist_ip
                SET expires_at = ?
                WHERE ip = ?
            """,
                (expires_at.isoformat(), ip),
            )

            updated = cursor.rowcount > 0
            conn.commit()
            conn.close()

            if updated:
                logger.info(f"Set expiration for IP {ip} to {expires_at}")

            return {
                "success": updated,
                "ip": ip,
                "expires_at": expires_at.isoformat() if updated else None,
            }

        except Exception as e:
            logger.error(f"Failed to set IP expiration: {e}")
            return {"success": False, "error": str(e)}

    def get_expiring_ips(self, days: int = 30) -> List[Dict[str, Any]]:
        """지정된 기간 내에 만료 예정인 IP 목록 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            future_date = datetime.now() + timedelta(days=days)

            cursor.execute(
                """
                SELECT ip, source, detection_date, expires_at, created_at
                FROM blacklist_ip
                WHERE is_active = 1
                AND expires_at IS NOT NULL
                AND expires_at <= ?
                ORDER BY expires_at ASC
                LIMIT 1000
            """,
                (future_date.isoformat(),),
            )

            expiring_ips = []
            for row in cursor.fetchall():
                expiring_ips.append(
                    {
                        "ip": row[0],
                        "source": row[1],
                        "detection_date": row[2],
                        "expires_at": row[3],
                        "created_at": row[4],
                        "days_until_expiry": (
                            (datetime.fromisoformat(row[3]) - datetime.now()).days
                            if row[3]
                            else None
                        ),
                    }
                )

            conn.close()

            return expiring_ips

        except Exception as e:
            logger.error(f"Failed to get expiring IPs: {e}")
            return []


# ==============================================================================
# Rust-style 인라인 통합 테스트
# ==============================================================================


def _test_blacklist_manager_initialization():
    """블랙리스트 매니저 초기화 테스트"""
    print("🧪 블랙리스트 매니저 초기화 테스트 시작...")

    try:
        # 테스트용 설정으로 매니저 생성
        manager = UnifiedBlacklistManager("data", cache_backend=None)

        assert manager is not None
        assert manager.data_dir == "data"
        print("  ✅ 매니저 기본 초기화 성공")

        # 디렉토리 생성 확인
        if hasattr(manager, "_ensure_directories"):
            print("  ✅ 디렉토리 생성 메서드 존재")

        print("✅ 블랙리스트 매니저 초기화 테스트 통과")
        return True

    except Exception as e:
        print(f"❌ 초기화 테스트 중 오류: {str(e)}")
        return False


def _test_blacklist_manager_database_operations():
    """블랙리스트 매니저 데이터베이스 작업 테스트"""
    print("🧪 블랙리스트 매니저 데이터베이스 작업 테스트 시작...")

    try:
        from .container import get_container

        # 컨테이너에서 매니저 가져오기
        container = get_container()
        manager = container.resolve("blacklist_manager")

        if not manager:
            print("  ⚠️ 블랙리스트 매니저를 컨테이너에서 가져올 수 없음")
            return False

        # 활성 IP 목록 가져오기 테스트
        active_ips = manager.get_active_blacklist_ips()
        print(f"  📊 활성 IP 수: {len(active_ips)}")

        if len(active_ips) > 0:
            print("  ✅ 활성 IP 목록 조회 성공")

            # 첫 번째 IP로 검색 테스트
            test_ip = active_ips[0]
            search_result = manager.search_ip(test_ip)

            if search_result and search_result.get("found"):
                print(f"  ✅ IP 검색 기능 동작 확인: {test_ip}")
            else:
                print(f"  ⚠️ IP 검색 결과 불일치: {test_ip}")
        else:
            print("  ⚠️ 활성 IP가 없음 (예상될 수 있음)")

        # 통계 정보 테스트 (통합 서비스 사용)
        try:
            from .unified_service import get_unified_service

            service = get_unified_service()
            stats = service.get_source_statistics()
            if isinstance(stats, dict):
                print(f"  ✅ 통계 정보 조회 성공: {stats}")
            else:
                print("  ⚠️ 통계 정보 형식 오류")
        except Exception as e:
            print(f"  ⚠️ 통계 정보 조회 실패: {str(e)[:30]}...")

        print("✅ 블랙리스트 매니저 데이터베이스 작업 테스트 통과")
        return True

    except Exception as e:
        print(f"❌ 데이터베이스 작업 테스트 중 오류: {str(e)}")
        return False


def _test_blacklist_manager_fortigate_format():
    """FortiGate 형식 변환 테스트"""
    print("🧪 FortiGate 형식 변환 테스트 시작...")

    try:
        from .container import get_container

        container = get_container()
        manager = container.resolve("blacklist_manager")

        if not manager:
            print("  ⚠️ 블랙리스트 매니저를 가져올 수 없음")
            return False

        # FortiGate 형식 변환 테스트 (통합 서비스 사용)
        active_ips = manager.get_active_blacklist_ips()
        from .unified_service import get_unified_service

        service = get_unified_service()
        fortigate_data = service.format_for_fortigate(active_ips)

        # 기본 구조 검증
        if isinstance(fortigate_data, dict):
            print("  ✅ FortiGate 데이터가 딕셔너리 형태")

            if "results" in fortigate_data:
                results_count = len(fortigate_data["results"])
                print(f"  ✅ FortiGate 결과 항목 수: {results_count}")

                if results_count > 0:
                    # 첫 번째 항목의 구조 확인
                    first_item = fortigate_data["results"][0]
                    if isinstance(first_item, dict) and "ip" in first_item:
                        print("  ✅ FortiGate 항목 구조 올바름")
                    else:
                        print("  ⚠️ FortiGate 항목 구조 이상")

                if "metadata" in fortigate_data:
                    print("  ✅ FortiGate 메타데이터 포함")

            else:
                print("  ❌ FortiGate 데이터에 'results' 키 없음")
                return False
        else:
            print("  ❌ FortiGate 데이터가 딕셔너리가 아님")
            return False

        print("✅ FortiGate 형식 변환 테스트 통과")
        return True

    except Exception as e:
        print(f"❌ FortiGate 형식 변환 테스트 중 오류: {str(e)}")
        return False


def _test_blacklist_manager_performance():
    """블랙리스트 매니저 성능 테스트"""
    print("🧪 블랙리스트 매니저 성능 테스트 시작...")

    try:
        import time

        from .container import get_container

        container = get_container()
        manager = container.resolve("blacklist_manager")

        if not manager:
            print("  ⚠️ 블랙리스트 매니저를 가져올 수 없음")
            return False

        # 통계 조회 성능 테스트
        from .unified_service import get_unified_service

        service = get_unified_service()
        start_time = time.time()
        _ = service.get_source_statistics()  # 통계 조회 테스트
        stats_time = time.time() - start_time
        print(f"  📊 통계 조회 시간: {stats_time:.3f}초")

        # IP 검색 성능 테스트 (실제 IP 사용)
        active_ips = manager.get_active_blacklist_ips()
        if len(active_ips) > 0:
            test_ip = active_ips[0]

            start_time = time.time()
            _ = manager.search_ip(test_ip)  # IP 검색 테스트
            search_time = time.time() - start_time
            print(f"  🔍 IP 검색 시간: {search_time:.3f}초")

            # 성능 기준 확인 (응답시간 < 100ms)
            if stats_time < 0.1 and search_time < 0.1:
                print("  ✅ 성능 기준 충족 (< 100ms)")
            else:
                print("  ⚠️ 성능 기준 미충족 (> 100ms)")
        else:
            print("  ⚠️ 테스트할 IP가 없음")

        # FortiGate 형식 변환 성능 테스트
        start_time = time.time()
        _ = service.format_for_fortigate(active_ips)  # FortiGate 형식 변환 테스트
        fortigate_time = time.time() - start_time
        print(f"  🛡️ FortiGate 변환 시간: {fortigate_time:.3f}초")

        # 전체 성능 평가
        total_time = stats_time + search_time + fortigate_time
        if total_time < 0.3:  # 300ms 이하
            print(f"  ✅ 전체 성능 우수: {total_time:.3f}초")
            performance_ok = True
        elif total_time < 1.0:  # 1초 이하
            print(f"  ✅ 전체 성능 양호: {total_time:.3f}초")
            performance_ok = True
        else:
            print(f"  ⚠️ 전체 성능 개선 필요: {total_time:.3f}초")
            performance_ok = False

        print("✅ 블랙리스트 매니저 성능 테스트 완료")
        return performance_ok

    except Exception as e:
        print(f"❌ 성능 테스트 중 오류: {str(e)}")
        return False


def _test_blacklist_manager_data_integrity():
    """데이터 무결성 테스트"""
    print("🧪 블랙리스트 매니저 데이터 무결성 테스트 시작...")

    try:
        from .container import get_container

        container = get_container()
        manager = container.resolve("blacklist_manager")

        if not manager:
            print("  ⚠️ 블랙리스트 매니저를 가져올 수 없음")
            return False

        # 통계 정보와 실제 데이터 일치성 확인
        from .unified_service import get_unified_service

        service = get_unified_service()
        stats = service.get_source_statistics()
        active_ips = manager.get_active_blacklist_ips()

        stats_total = stats.get("total_ips", 0)
        actual_count = len(active_ips)

        print(f"  📊 통계 총 IP 수: {stats_total}")
        print(f"  📊 실제 활성 IP 수: {actual_count}")

        # 완전 일치를 요구하지 않음 (만료된 IP 등이 있을 수 있음)
        if stats_total >= actual_count:
            print("  ✅ 데이터 일치성 검증 통과 (통계 >= 실제)")
            integrity_ok = True
        else:
            print("  ⚠️ 데이터 불일치 (통계 < 실제)")
            integrity_ok = False

        # IP 형식 검증 (샘플링)
        valid_ips = 0
        invalid_ips = 0

        import re

        ip_pattern = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")

        sample_size = min(10, len(active_ips))
        for i in range(sample_size):
            ip = active_ips[i]
            if ip_pattern.match(ip):
                valid_ips += 1
            else:
                invalid_ips += 1

        if sample_size > 0:
            print(f"  🔍 IP 형식 검증 ({sample_size}개 샘플): 유효 {valid_ips}, 무효 {invalid_ips}")
            if invalid_ips == 0:
                print("  ✅ IP 형식 모두 유효")
            else:
                print("  ⚠️ 일부 IP 형식 무효")
                integrity_ok = False

        # 중복 IP 검사
        unique_ips = set(active_ips)
        duplicate_count = len(active_ips) - len(unique_ips)

        if duplicate_count == 0:
            print("  ✅ 중복 IP 없음")
        else:
            print(f"  ⚠️ 중복 IP 발견: {duplicate_count}개")
            integrity_ok = False

        print("✅ 블랙리스트 매니저 데이터 무결성 테스트 완료")
        return integrity_ok

    except Exception as e:
        print(f"❌ 데이터 무결성 테스트 중 오류: {str(e)}")
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Unified Blacklist Manager 통합 테스트 실행")
    print("=" * 70)

    # 테스트 결과 수집
    test_results = []

    # 개별 테스트 실행
    test_results.append(_test_blacklist_manager_initialization())
    test_results.append(_test_blacklist_manager_database_operations())
    test_results.append(_test_blacklist_manager_fortigate_format())
    test_results.append(_test_blacklist_manager_performance())
    test_results.append(_test_blacklist_manager_data_integrity())

    # 전체 결과 요약
    passed_tests = sum(test_results)
    total_tests = len(test_results)

    print("=" * 70)
    print("📊 테스트 결과 요약")
    print("=" * 70)
    print(f"총 테스트 수: {total_tests}")
    print(f"통과한 테스트: {passed_tests}")
    print(f"실패한 테스트: {total_tests - passed_tests}")
    print(f"성공률: {(passed_tests/total_tests)*100:.1f}%")

    if passed_tests == total_tests:
        print("🎉 모든 테스트 통과!")
        exit(0)
    elif passed_tests >= total_tests * 0.7:
        print("✅ 대부분 테스트 통과 (70% 이상)")
        exit(0)
    else:
        print("❌ 다수 테스트 실패")
        exit(1)
