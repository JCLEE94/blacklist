#!/usr/bin/env python3
"""
Unified Blacklist Manager - Main coordination class
"""

import logging
import os
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...utils.advanced_cache import EnhancedSmartCache
from ...utils.unified_decorators import unified_monitoring
from ..database import DatabaseManager
from .data_service import DataService
from .expiration_service import ExpirationService
from .search_service import SearchService
from .statistics_service import StatisticsService

logger = logging.getLogger(__name__)


class UnifiedBlacklistManager:
    """Enhanced Unified Blacklist Manager with modular architecture"""

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
            self.db_path = db_url.replace("sqlite:///", "")
        else:
            self.db_path = os.path.join(self.data_dir, "database.db")

        # Initialize cache
        if cache_backend:
            self.cache = cache_backend
        else:
            from ...utils.advanced_cache import EnhancedSmartCache as CacheManager

            cache_manager = CacheManager()
            self.cache = cache_manager.get_cache()

        # Initialize services
        self.search_service = SearchService(self.data_dir, self.db_manager, self.cache)
        self.data_service = DataService(self.data_dir, self.db_manager, self.cache)
        self.statistics_service = StatisticsService(
            self.data_dir, self.db_manager, self.cache
        )
        self.expiration_service = ExpirationService(
            self.data_dir, self.db_manager, self.cache
        )

        # Initialize geolocation if API keys provided
        self.geo_api_keys = geo_api_keys or {}
        self.geolocation_enabled = bool(self.geo_api_keys)

        # Start cleanup scheduler
        self._setup_cleanup_scheduler()

    def _ensure_directories(self) -> None:
        """Ensure required directories exist"""
        directories = [
            self.data_dir,
            self.blacklist_dir,
            self.detection_dir,
            os.path.join(self.data_dir, "exports"),
            os.path.join(self.data_dir, "logs"),
        ]

        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                logger.debug(f"Directory ensured: {directory}")
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {e}")
                raise

    def _setup_cleanup_scheduler(self):
        """Setup periodic cleanup of old data"""

        def cleanup_thread():
            while True:
                try:
                    import time

                    time.sleep(24 * 3600)  # Run daily

                    # Run expiration update
                    self.expiration_service.update_expiration_status()

                    # Clean old data (older than 1 year)
                    self.data_service.cleanup_old_data(days=365)

                    logger.info("Scheduled cleanup completed")
                except Exception as e:
                    logger.error(f"Error in cleanup scheduler: {e}")

        cleanup_worker = threading.Thread(target=cleanup_thread, daemon=True)
        cleanup_worker.start()

    # Delegate methods to appropriate services
    def search_ip(self, ip: str, include_geo: bool = False) -> Dict[str, Any]:
        """Search for IP in blacklist"""
        return self.search_service.search_ip(ip, include_geo)

    def search_ips(
        self, ips: List[str], max_workers: int = 20, include_geo: bool = False
    ) -> Dict[str, Any]:
        """Bulk search for multiple IPs"""
        return self.search_service.search_ips(ips, max_workers, include_geo)

    def bulk_import_ips(
        self,
        ips_data: List[Dict[str, Any]],
        source: str,
        batch_size: int = 1000,
        clear_existing: bool = False,
    ) -> Dict[str, Any]:
        """Bulk import IP addresses"""
        return self.data_service.bulk_import_ips(
            ips_data, source, batch_size, clear_existing
        )

    def get_active_ips(self) -> List[str]:
        """Get all active IP addresses"""
        return self.data_service.get_active_ips()

    def get_all_active_ips(self) -> List[Dict[str, Any]]:
        """Get all active IPs with metadata"""
        return self.data_service.get_all_active_ips()

    def clear_all(self) -> Dict[str, Any]:
        """Clear all blacklist data"""
        return self.data_service.clear_all()

    def cleanup_old_data(self, days: int = 365):
        """Clean up old data"""
        return self.data_service.cleanup_old_data(days)

    def get_stats_for_period(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get statistics for a date range"""
        return self.statistics_service.get_stats_for_period(start_date, end_date)

    def get_country_statistics(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get country statistics"""
        return self.statistics_service.get_country_statistics(limit)

    def get_daily_trend_data(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily trend data"""
        return self.statistics_service.get_daily_trend_data(days)

    def get_system_health(self) -> Dict[str, Any]:
        """Get system health statistics"""
        return self.statistics_service.get_system_health()

    def update_expiration_status(self) -> Dict[str, Any]:
        """Update expiration status for IPs"""
        return self.expiration_service.update_expiration_status()

    def get_expiration_stats(self) -> Dict[str, Any]:
        """Get expiration statistics"""
        return self.statistics_service.get_expiration_stats()

    def set_ip_expiration(self, ip: str, expires_at: datetime) -> Dict[str, Any]:
        """Set expiration date for an IP"""
        return self.expiration_service.set_ip_expiration(ip, expires_at)

    def get_expiring_ips(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get IPs expiring within specified days"""
        return self.statistics_service.get_expiring_ips(days)

    # Legacy methods for backward compatibility
    def get_active_blacklist_ips(self) -> List[str]:
        """Legacy method - redirects to get_active_ips"""
        return self.get_active_ips()

    @unified_monitoring("get_fortigate_format")
    def get_active_ips_fortigate_format(self) -> str:
        """Get active IPs in FortiGate format"""
        try:
            active_ips = self.get_active_ips()

            if not active_ips:
                return "[]"

            # FortiGate JSON format
            fortigate_data = []
            for ip in active_ips:
                fortigate_data.append(
                    {"ip": ip, "type": "malicious", "confidence": "high"}
                )

            import json

            return json.dumps(fortigate_data, indent=2)

        except Exception as e:
            logger.error(f"Error generating FortiGate format: {e}")
            return "[]"
