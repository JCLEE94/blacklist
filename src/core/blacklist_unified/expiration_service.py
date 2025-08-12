#!/usr/bin/env python3
"""
Expiration Service for Unified Blacklist Manager
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List

from ...utils.advanced_cache import EnhancedSmartCache
from ...utils.unified_decorators import unified_monitoring
from ..database import DatabaseManager

logger = logging.getLogger(__name__)


class ExpirationService:
    """Handles IP expiration operations for the blacklist manager"""

    def __init__(
        self, data_dir: str, db_manager: DatabaseManager, cache: EnhancedSmartCache
    ):
        self.data_dir = data_dir
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
            import os

            self.db_path = os.path.join(self.data_dir, "database.db")

    @unified_monitoring("update_expiration_status")
    def update_expiration_status(self) -> Dict[str, Any]:
        """Update expiration status and deactivate expired IPs"""
        try:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                cursor = conn.cursor()

                # Count currently active IPs
                cursor.execute("SELECT COUNT(*) FROM ip_detections WHERE is_active = 1")
                active_before = cursor.fetchone()[0]

                # Count expired IPs that are still active
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM ip_detections
                    WHERE is_active = 1
                      AND expires_at IS NOT NULL
                      AND expires_at < datetime('now')
                    """
                )
                expired_count = cursor.fetchone()[0]

                # Deactivate expired IPs
                cursor.execute(
                    """
                    UPDATE ip_detections
                    SET is_active = 0,
                        updated_at = datetime('now')
                    WHERE is_active = 1
                      AND expires_at IS NOT NULL
                      AND expires_at < datetime('now')
                    """
                )

                # Get updated count
                cursor.execute("SELECT COUNT(*) FROM ip_detections WHERE is_active = 1")
                active_after = cursor.fetchone()[0]

                conn.commit()

                # Clear relevant caches
                self.cache.delete_pattern("active_ips*")
                self.cache.delete_pattern("stats*")

                result = {
                    "success": True,
                    "active_ips_before": active_before,
                    "expired_ips_deactivated": expired_count,
                    "active_ips_after": active_after,
                    "timestamp": datetime.now().isoformat(),
                }

                if expired_count > 0:
                    logger.info(f"Deactivated {expired_count} expired IPs")

                return result

        except sqlite3.Error as e:
            logger.error(f"Database error updating expiration status: {e}")
            return {
                "success": False,
                "error": f"Database error: {e}",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Unexpected error updating expiration status: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {e}",
                "timestamp": datetime.now().isoformat(),
            }

    def set_ip_expiration(self, ip: str, expires_at: datetime) -> Dict[str, Any]:
        """Set expiration date for a specific IP"""
        try:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                cursor = conn.cursor()

                # Check if IP exists and is active
                cursor.execute(
                    "SELECT COUNT(*) FROM ip_detections WHERE ip_address = ? AND is_active = 1",
                    (ip,),
                )

                if cursor.fetchone()[0] == 0:
                    return {
                        "success": False,
                        "error": f"IP {ip} not found or not active",
                        "timestamp": datetime.now().isoformat(),
                    }

                # Update expiration date
                cursor.execute(
                    """
                    UPDATE ip_detections
                    SET expires_at = ?,
                        updated_at = datetime('now')
                    WHERE ip_address = ?
                      AND is_active = 1
                    """,
                    (expires_at.isoformat(), ip),
                )

                rows_updated = cursor.rowcount
                conn.commit()

                # Clear relevant caches
                self.cache.delete_pattern(f"ip_search_{ip}*")
                self.cache.delete_pattern("stats*")

                return {
                    "success": True,
                    "ip": ip,
                    "expires_at": expires_at.isoformat(),
                    "records_updated": rows_updated,
                    "timestamp": datetime.now().isoformat(),
                }

        except sqlite3.Error as e:
            logger.error(f"Database error setting IP expiration: {e}")
            return {
                "success": False,
                "error": f"Database error: {e}",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Unexpected error setting IP expiration: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {e}",
                "timestamp": datetime.now().isoformat(),
            }

    def bulk_set_expiration(
        self, ip_expirations: List[Dict[str, Any]], default_days: int = 90
    ) -> Dict[str, Any]:
        """Set expiration dates for multiple IPs"""
        try:
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                cursor = conn.cursor()

                updated_count = 0
                errors = []

                for item in ip_expirations:
                    ip = item.get("ip")
                    expires_at = item.get("expires_at")

                    if not ip:
                        errors.append(f"Missing IP address in item: {item}")
                        continue

                    # Use provided expiration or calculate default
                    if expires_at:
                        if isinstance(expires_at, str):
                            try:
                                expires_at = datetime.fromisoformat(expires_at)
                            except ValueError:
                                errors.append(
                                    f"Invalid expiration date for IP {ip}: {expires_at}"
                                )
                                continue
                    else:
                        expires_at = datetime.now() + timedelta(days=default_days)

                    try:
                        cursor.execute(
                            """
                            UPDATE ip_detections
                            SET expires_at = ?,
                                updated_at = datetime('now')
                            WHERE ip_address = ?
                              AND is_active = 1
                            """,
                            (expires_at.isoformat(), ip),
                        )

                        if cursor.rowcount > 0:
                            updated_count += cursor.rowcount
                        else:
                            errors.append(f"IP {ip} not found or not active")

                    except sqlite3.Error as e:
                        errors.append(f"Error updating IP {ip}: {e}")

                conn.commit()

                # Clear relevant caches
                self.cache.delete_pattern("stats*")

                return {
                    "success": True,
                    "total_items": len(ip_expirations),
                    "records_updated": updated_count,
                    "errors": errors,
                    "error_count": len(errors),
                    "timestamp": datetime.now().isoformat(),
                }

        except sqlite3.Error as e:
            logger.error(f"Database error in bulk expiration update: {e}")
            return {
                "success": False,
                "error": f"Database error: {e}",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Unexpected error in bulk expiration update: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {e}",
                "timestamp": datetime.now().isoformat(),
            }

    def extend_ip_expiration(self, ip: str, extend_days: int) -> Dict[str, Any]:
        """Extend expiration date for an IP by specified days"""
        try:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                cursor = conn.cursor()

                # Get current expiration date
                cursor.execute(
                    "SELECT expires_at FROM ip_detections WHERE ip_address = ? AND is_active = 1 LIMIT 1",
                    (ip,),
                )

                row = cursor.fetchone()
                if not row:
                    return {
                        "success": False,
                        "error": f"IP {ip} not found or not active",
                        "timestamp": datetime.now().isoformat(),
                    }

                current_expiration = row[0]

                # Calculate new expiration date
                if current_expiration:
                    current_exp_dt = datetime.fromisoformat(current_expiration)
                    new_expiration = current_exp_dt + timedelta(days=extend_days)
                else:
                    # If no current expiration, set from now
                    new_expiration = datetime.now() + timedelta(days=extend_days)

                # Update expiration date
                cursor.execute(
                    """
                    UPDATE ip_detections
                    SET expires_at = ?,
                        updated_at = datetime('now')
                    WHERE ip_address = ?
                      AND is_active = 1
                    """,
                    (new_expiration.isoformat(), ip),
                )

                rows_updated = cursor.rowcount
                conn.commit()

                # Clear relevant caches
                self.cache.delete_pattern(f"ip_search_{ip}*")
                self.cache.delete_pattern("stats*")

                return {
                    "success": True,
                    "ip": ip,
                    "previous_expiration": current_expiration,
                    "new_expiration": new_expiration.isoformat(),
                    "days_extended": extend_days,
                    "records_updated": rows_updated,
                    "timestamp": datetime.now().isoformat(),
                }

        except sqlite3.Error as e:
            logger.error(f"Database error extending IP expiration: {e}")
            return {
                "success": False,
                "error": f"Database error: {e}",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Unexpected error extending IP expiration: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {e}",
                "timestamp": datetime.now().isoformat(),
            }
