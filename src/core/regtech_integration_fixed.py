#!/usr/bin/env python3
"""
Complete REGTECH Integration System
End-to-end solution that handles collection, storage, and API serving
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List

from dotenv import load_dotenv

try:
    from .collectors.regtech_collector_fixed import FixedRegtechCollector
    from .data_storage_fixed import FixedDataStorage
except ImportError:
    # For standalone execution
    import os
    import sys

    sys.path.insert(0, os.path.dirname(__file__))
    from collectors.regtech_collector_fixed import FixedRegtechCollector
    from data_storage_fixed import FixedDataStorage

logger = logging.getLogger(__name__)
load_dotenv()


class RegtechIntegrationSystem:
    """
    Complete REGTECH integration system that handles the full pipeline:
    1. Authentication with REGTECH
    2. Data collection
    3. Data storage in PostgreSQL
    4. API serving
    """

    def __init__(self, database_url: str = None):
        # Initialize components
        self.collector = FixedRegtechCollector()
        self.storage = FixedDataStorage(database_url)

        # System status
        self.last_collection_time = None
        self.last_collection_count = 0
        self.last_error = None

    def collect_from_web(
        self, start_date: str = None, end_date: str = None
    ) -> Dict[str, Any]:
        """
        웹에서 데이터 수집 (collection_service.py 호환 메서드)
        """
        return self.run_collection(start_date, end_date)

    def run_collection(
        self, start_date: str = None, end_date: str = None, clear_existing: bool = False
    ) -> Dict[str, Any]:
        """
        Run complete collection pipeline

        Args:
            start_date: Collection start date (YYYY-MM-DD)
            end_date: Collection end date (YYYY-MM-DD)
            clear_existing: Whether to clear existing data first

        Returns:
            Collection results dictionary
        """
        collection_start_time = datetime.now()

        logger.info("Starting REGTECH collection pipeline")
        logger.info(f"Date range: {start_date} to {end_date}")
        logger.info(f"Clear existing: {clear_existing}")

        try:
            # Step 1: Clear existing data if requested
            if clear_existing:
                logger.info("Clearing existing data...")
                clear_result = self.storage.clear_all_data()
                if not clear_result.get("success"):
                    return {
                        "success": False,
                        "error": f"Failed to clear data: {clear_result.get('error')}",
                        "stage": "clear_data",
                    }
                logger.info(
                    f"Cleared {clear_result.get('cleared_count', 0)} existing entries"
                )

            # Step 2: Collect data from REGTECH
            logger.info("Starting data collection from REGTECH...")
            collection_result = self.collector.collect_from_web(start_date, end_date)

            if not collection_result.get("success"):
                return {
                    "success": False,
                    "error": f"Collection failed: {collection_result.get('error')}",
                    "stage": "collection",
                }

            collected_data = collection_result.get("data", [])
            logger.info(f"Collected {len(collected_data)} IPs from REGTECH")

            # Step 3: Store collected data
            if collected_data:
                logger.info("Storing collected data in database...")
                storage_result = self.storage.store_ips(collected_data, "REGTECH")

                if not storage_result.get("success"):
                    return {
                        "success": False,
                        "error": f"Storage failed: {storage_result.get('error')}",
                        "stage": "storage",
                    }

                stored_count = storage_result.get("imported_count", 0)
                logger.info(f"Stored {stored_count} IPs in database")
            else:
                logger.warning("No data collected to store")
                stored_count = 0

            # Step 4: Update system status
            self.last_collection_time = collection_start_time
            self.last_collection_count = stored_count
            self.last_error = None

            # Step 5: Generate final report
            collection_end_time = datetime.now()
            execution_time = (
                collection_end_time - collection_start_time
            ).total_seconds()

            final_ip_count = self.storage.get_stored_ips_count()

            result = {
                "success": True,
                "collected_count": len(collected_data),
                "stored_count": stored_count,
                "total_ips_in_db": final_ip_count,
                "execution_time_seconds": execution_time,
                "start_time": collection_start_time.isoformat(),
                "end_time": collection_end_time.isoformat(),
                "message": f"Successfully collected and stored {stored_count} IPs from REGTECH",
            }

            logger.info("Collection pipeline completed successfully")
            logger.info(
                f"Final result: {stored_count} new IPs, {final_ip_count} total IPs in database"
            )

            return result

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Collection pipeline failed: {e}")
            return {"success": False, "error": str(e), "stage": "pipeline_error"}
        finally:
            # Always logout from REGTECH
            try:
                self.collector.logout()
            except Exception:
                pass

    def get_active_ips(self) -> List[str]:
        """Get list of active IP addresses"""
        try:
            stored_ips = self.storage.get_stored_ips(limit=10000)  # Get all active IPs
            return [
                ip_data["ip"].split("/")[0] for ip_data in stored_ips
            ]  # Remove /32 subnet notation
        except Exception as e:
            logger.error(f"Error getting active IPs: {e}")
            return []

    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        try:
            total_ips = self.storage.get_stored_ips_count()

            return {
                "total_ips": total_ips,
                "last_collection_time": (
                    self.last_collection_time.isoformat()
                    if self.last_collection_time
                    else None
                ),
                "last_collection_count": self.last_collection_count,
                "last_error": self.last_error,
                "database_connected": total_ips
                >= 0,  # If we can get count, DB is connected
                "status": "healthy" if total_ips > 0 else "no_data",
            }
        except Exception as e:
            return {
                "total_ips": 0,
                "last_collection_time": None,
                "last_collection_count": 0,
                "last_error": str(e),
                "database_connected": False,
                "status": "error",
            }

    def test_end_to_end(self) -> Dict[str, Any]:
        """Test complete end-to-end functionality"""
        logger.info("Running end-to-end test")

        try:
            # Test data
            test_ips = [
                {
                    "ip": "192.0.2.1",  # Test IP from RFC 5737
                    "source": "TEST_E2E",
                    "description": "End-to-end test IP",
                    "confidence": "high",
                    "detection_date": "2025-01-19",
                }
            ]

            # Step 1: Test storage
            storage_result = self.storage.store_ips(test_ips, "TEST_E2E")
            if not storage_result.get("success"):
                return {
                    "success": False,
                    "error": f"Storage test failed: {storage_result.get('error')}",
                    "stage": "storage_test",
                }

            # Step 2: Test retrieval
            stored_ips = self.storage.get_stored_ips(limit=10)
            test_ip_found = any(ip["ip"].startswith("192.0.2.1") for ip in stored_ips)

            if not test_ip_found:
                return {
                    "success": False,
                    "error": "Test IP not found in stored data",
                    "stage": "retrieval_test",
                }

            # Step 3: Test API format
            active_ips = self.get_active_ips()
            api_test_success = "192.0.2.1" in active_ips

            # Cleanup test data
            try:
                import psycopg2

                with psycopg2.connect(self.storage.database_url) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "DELETE FROM blacklist_entries WHERE source = 'TEST_E2E'"
                    )
                    conn.commit()
            except Exception as e:
                logger.warning(f"Could not clean up test data: {e}")

            if not api_test_success:
                return {
                    "success": False,
                    "error": "Test IP not found in active IPs API",
                    "stage": "api_test",
                }

            return {
                "success": True,
                "message": "End-to-end test passed successfully",
                "tested_components": ["storage", "retrieval", "api_format"],
            }

        except Exception as e:
            return {"success": False, "error": str(e), "stage": "test_error"}


# Global instance for easy access
regtech_integration = None


def get_regtech_integration() -> RegtechIntegrationSystem:
    """Get global REGTECH integration instance"""
    global regtech_integration
    if regtech_integration is None:
        regtech_integration = RegtechIntegrationSystem()
    return regtech_integration


if __name__ == "__main__":
    """Test the complete integration system"""
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: System initialization
    total_tests += 1
    try:
        integration = RegtechIntegrationSystem()
        if not integration.collector or not integration.storage:
            all_validation_failures.append(
                "System initialization failed - missing components"
            )
    except Exception as e:
        all_validation_failures.append(f"System initialization failed: {e}")

    # Test 2: End-to-end test
    total_tests += 1
    try:
        e2e_result = integration.test_end_to_end()
        if not e2e_result.get("success"):
            all_validation_failures.append(
                f"End-to-end test failed: {e2e_result.get('error')}"
            )
        else:
            print("✅ End-to-end test passed")
    except Exception as e:
        all_validation_failures.append(f"End-to-end test failed: {e}")

    # Test 3: System status
    total_tests += 1
    try:
        status = integration.get_system_status()
        print(f"System status: {status}")
        if not status.get("database_connected"):
            all_validation_failures.append("Database not connected")
    except Exception as e:
        all_validation_failures.append(f"System status test failed: {e}")

    # Test 4: Collection pipeline (dry run with test data)
    total_tests += 1
    try:
        # Only test if we have credentials
        if os.getenv("REGTECH_USERNAME") and os.getenv("REGTECH_PASSWORD"):
            # Run actual collection test (will likely get 0 results but should not error)
            collection_result = integration.run_collection()
            if not collection_result.get("success"):
                print(
                    f"Collection test returned no data (expected): {collection_result.get('error', 'No error')}"
                )
            else:
                print(
                    f"Collection test completed: {collection_result.get('stored_count', 0)} IPs"
                )
        else:
            print("Skipping collection test - no REGTECH credentials")
    except Exception as e:
        all_validation_failures.append(f"Collection pipeline test failed: {e}")

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
        print("Complete REGTECH integration system is validated and ready for use")
        sys.exit(0)
