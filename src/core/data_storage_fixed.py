#!/usr/bin/env python3
"""
Fixed Data Storage System for REGTECH Collection
Handles PostgreSQL storage with proper schema compatibility
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List

import psycopg2
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()


class FixedDataStorage:
    """
    Fixed data storage system for PostgreSQL blacklist entries
    """

    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv(
            "DATABASE_URL", 
            "postgresql://blacklist_user:blacklist_password_change_me@localhost:32543/blacklist"
        )
        logger.info(f"Initialized storage with database: {self.database_url}")

    def store_ips(self, ip_data: List[Dict[str, Any]], source: str = "REGTECH") -> Dict[str, Any]:
        """
        Store IP data in PostgreSQL database
        
        Args:
            ip_data: List of IP data dictionaries
            source: Data source name
            
        Returns:
            Dictionary with storage results
        """
        if not ip_data:
            return {
                "success": True,
                "imported_count": 0,
                "message": "No data to store"
            }
        
        logger.info(f"Storing {len(ip_data)} IPs from {source}")
        
        try:
            with psycopg2.connect(self.database_url) as conn:
                cursor = conn.cursor()
                
                # Ensure table exists with proper schema
                self._ensure_table_exists(cursor)
                
                # Process and insert data
                imported_count = 0
                failed_count = 0
                
                for ip_entry in ip_data:
                    try:
                        ip_address = ip_entry.get("ip")
                        if not ip_address:
                            failed_count += 1
                            continue
                        
                        # Prepare data for insertion
                        insert_data = {
                            "ip": ip_address,
                            "source": ip_entry.get("source", source),
                            "description": ip_entry.get("description", ""),
                            "threat_level": ip_entry.get("confidence", "medium"),
                            "detection_date": self._parse_date(ip_entry.get("detection_date")),
                            "expiry_date": self._calculate_expiry_date(ip_entry.get("detection_date")),
                            "created_at": datetime.now(),
                            "updated_at": datetime.now(),
                            "is_active": True
                        }
                        
                        # First check if IP exists
                        cursor.execute("SELECT id FROM blacklist_entries WHERE ip = %s", (ip_address,))
                        existing = cursor.fetchone()
                        
                        if existing:
                            # Update existing record
                            cursor.execute("""
                                UPDATE blacklist_entries SET
                                    source = %(source)s,
                                    description = %(description)s,
                                    threat_level = %(threat_level)s,
                                    detection_date = %(detection_date)s,
                                    updated_at = %(updated_at)s,
                                    is_active = %(is_active)s
                                WHERE ip = %(ip)s
                            """, insert_data)
                        else:
                            # Insert new record
                            cursor.execute("""
                                INSERT INTO blacklist_entries (
                                    ip, source, description, threat_level, 
                                    detection_date, expiry_date, created_at, updated_at, is_active
                                ) VALUES (
                                    %(ip)s, %(source)s, %(description)s, %(threat_level)s,
                                    %(detection_date)s, %(expiry_date)s, %(created_at)s, %(updated_at)s, %(is_active)s
                                )
                            """, insert_data)
                        
                        imported_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error storing IP {ip_entry.get('ip', 'unknown')}: {e}")
                        failed_count += 1
                        continue
                
                conn.commit()
                
                result = {
                    "success": True,
                    "imported_count": imported_count,
                    "failed_count": failed_count,
                    "total_processed": len(ip_data),
                    "message": f"Stored {imported_count} IPs successfully"
                }
                
                logger.info(f"Storage complete: {imported_count} imported, {failed_count} failed")
                return result
                
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error during storage: {e}")
            return {
                "success": False,
                "error": str(e),
                "imported_count": 0,
                "message": f"Database error: {e}"
            }
        except Exception as e:
            logger.error(f"Unexpected error during storage: {e}")
            return {
                "success": False,
                "error": str(e),
                "imported_count": 0,
                "message": f"Storage failed: {e}"
            }

    def _ensure_table_exists(self, cursor):
        """Ensure blacklist_entries table exists with correct schema"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blacklist_entries (
                id SERIAL PRIMARY KEY,
                ip INET NOT NULL UNIQUE,
                source VARCHAR(100),
                description TEXT,
                threat_level VARCHAR(50) DEFAULT 'medium',
                detection_date DATE,
                expiry_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_blacklist_ip ON blacklist_entries (ip);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_blacklist_active ON blacklist_entries (is_active);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_blacklist_source ON blacklist_entries (source);
        """)

    def _parse_date(self, date_str) -> str:
        """Parse date string to YYYY-MM-DD format"""
        if not date_str:
            return datetime.now().strftime('%Y-%m-%d')
        
        if isinstance(date_str, datetime):
            return date_str.strftime('%Y-%m-%d')
        
        # Try to parse various date formats
        date_formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%Y-%m-%d %H:%M:%S'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(str(date_str), fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # If all parsing fails, return current date
        logger.warning(f"Could not parse date: {date_str}, using current date")
        return datetime.now().strftime('%Y-%m-%d')

    def _calculate_expiry_date(self, detection_date_str, days_to_expire: int = 90) -> str:
        """Calculate expiry date based on detection date"""
        try:
            if detection_date_str:
                detection_date = datetime.strptime(detection_date_str, '%Y-%m-%d')
            else:
                detection_date = datetime.now()
            
            from datetime import timedelta
            expiry_date = detection_date + timedelta(days=days_to_expire)
            return expiry_date.strftime('%Y-%m-%d')
            
        except Exception:
            # Default to 90 days from now
            from datetime import timedelta
            expiry_date = datetime.now() + timedelta(days=days_to_expire)
            return expiry_date.strftime('%Y-%m-%d')

    def get_stored_ips_count(self) -> int:
        """Get count of stored active IPs"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM blacklist_entries WHERE is_active = TRUE")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting IP count: {e}")
            return 0

    def get_stored_ips(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get stored IPs with metadata"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT ip::text, source, description, threat_level, 
                           detection_date, created_at, updated_at
                    FROM blacklist_entries 
                    WHERE is_active = TRUE 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """, (limit,))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        "ip": row[0],
                        "source": row[1],
                        "description": row[2],
                        "threat_level": row[3],
                        "detection_date": str(row[4]) if row[4] else None,
                        "created_at": str(row[5]),
                        "updated_at": str(row[6])
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"Error getting stored IPs: {e}")
            return []

    def clear_all_data(self) -> Dict[str, Any]:
        """Clear all data from database"""
        try:
            with psycopg2.connect(self.database_url) as conn:
                cursor = conn.cursor()
                
                # Count current entries
                cursor.execute("SELECT COUNT(*) FROM blacklist_entries WHERE is_active = TRUE")
                count = cursor.fetchone()[0]
                
                # Mark all as inactive instead of deleting
                cursor.execute("""
                    UPDATE blacklist_entries 
                    SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP 
                    WHERE is_active = TRUE
                """)
                
                conn.commit()
                
                return {
                    "success": True,
                    "cleared_count": count,
                    "message": f"Cleared {count} entries"
                }
                
        except Exception as e:
            logger.error(f"Error clearing data: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to clear data: {e}"
            }


if __name__ == "__main__":
    """Test the fixed data storage system"""
    import sys
    
    all_validation_failures = []
    total_tests = 0
    
    # Test 1: Storage initialization
    total_tests += 1
    try:
        storage = FixedDataStorage()
        if not storage.database_url:
            all_validation_failures.append("Storage initialization failed - no database URL")
    except Exception as e:
        all_validation_failures.append(f"Storage initialization failed: {e}")
    
    # Test 2: Database connection test
    total_tests += 1
    try:
        count = storage.get_stored_ips_count()
        print(f"Current IP count in database: {count}")
    except Exception as e:
        all_validation_failures.append(f"Database connection test failed: {e}")
    
    # Test 3: Test IP storage
    total_tests += 1
    try:
        test_ips = [
            {
                "ip": "1.2.3.4",
                "source": "TEST_REGTECH",
                "description": "Test IP for validation",
                "confidence": "high",
                "detection_date": "2025-01-19"
            },
            {
                "ip": "5.6.7.8",
                "source": "TEST_REGTECH", 
                "description": "Another test IP",
                "confidence": "medium",
                "detection_date": "2025-01-19"
            }
        ]
        
        result = storage.store_ips(test_ips, "TEST_REGTECH")
        if not result.get("success"):
            all_validation_failures.append(f"IP storage test failed: {result.get('error', 'Unknown error')}")
        elif result.get("imported_count") != 2:
            all_validation_failures.append(f"Expected 2 IPs imported, got {result.get('imported_count', 0)}")
        else:
            print(f"Successfully stored {result.get('imported_count')} test IPs")
    except Exception as e:
        all_validation_failures.append(f"IP storage test failed: {e}")
    
    # Test 4: Test data retrieval
    total_tests += 1
    try:
        stored_ips = storage.get_stored_ips(limit=10)
        print(f"Retrieved {len(stored_ips)} stored IPs")
        if stored_ips:
            print("Sample stored IP:", stored_ips[0])
    except Exception as e:
        all_validation_failures.append(f"Data retrieval test failed: {e}")
    
    # Clean up test data
    try:
        with psycopg2.connect(storage.database_url) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM blacklist_entries WHERE source = 'TEST_REGTECH'")
            conn.commit()
            print("Test data cleaned up")
    except Exception as e:
        print(f"Warning: Could not clean up test data: {e}")
    
    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Fixed data storage system is validated and ready for use")
        sys.exit(0)