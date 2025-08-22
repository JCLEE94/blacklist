#!/usr/bin/env python3
"""
Analysis Scripts Main Entry Point
Consolidated analysis functionality for blacklist system
"""
import logging
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_performance_analysis():
    """Run performance analysis tasks"""
    logger.info("Running performance analysis")

    import time
    import psutil
    import requests
    from datetime import datetime

    try:
        # System performance metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        logger.info(f"CPU Usage: {cpu_percent}%")
        logger.info(
            f"Memory Usage: {memory.percent}% ({memory.used / (1024**3):.1f}GB / {memory.total / (1024**3):.1f}GB)"
        )
        logger.info(
            f"Disk Usage: {disk.percent}% ({disk.used / (1024**3):.1f}GB / {disk.total / (1024**3):.1f}GB)"
        )

        # API performance testing
        try:
            start_time = time.time()
            response = requests.get("http://localhost:32542/health", timeout=5)
            end_time = time.time()

            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            logger.info(
                f"API Health Check: {response.status_code} - Response Time: {response_time:.2f}ms"
            )

            if response.status_code == 200:
                logger.info("✅ API Performance: Healthy")
            else:
                logger.warning(f"⚠️  API Performance: Status {response.status_code}")

        except Exception as e:
            logger.error(f"❌ API Performance Test Failed: {e}")

        logger.info("Performance analysis completed successfully")
        return True

    except Exception as e:
        logger.error(f"Performance analysis failed: {e}")
        return False


def run_data_analysis():
    """Run data analysis tasks"""
    logger.info("Running data analysis")

    import sqlite3
    import json
    from datetime import datetime, timedelta

    try:
        # Database analysis
        db_path = "/home/jclee/app/blacklist/instance/blacklist.db"

        if not os.path.exists(db_path):
            logger.warning(f"Database not found at {db_path}")
            return False

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Get table information
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            logger.info(f"Database Tables: {[table[0] for table in tables]}")

            # Analyze blacklist entries if table exists
            try:
                cursor.execute("SELECT COUNT(*) FROM blacklist_entries;")
                total_entries = cursor.fetchone()[0]
                logger.info(f"Total Blacklist Entries: {total_entries}")

                # Get recent entries (last 7 days)
                week_ago = datetime.now() - timedelta(days=7)
                cursor.execute(
                    "SELECT COUNT(*) FROM blacklist_entries WHERE created_at > ?;",
                    (week_ago.isoformat(),),
                )
                recent_entries = cursor.fetchone()[0]
                logger.info(f"Entries Added (Last 7 days): {recent_entries}")

                # Source distribution
                cursor.execute(
                    "SELECT source, COUNT(*) FROM blacklist_entries GROUP BY source;"
                )
                source_dist = cursor.fetchall()
                logger.info(f"Source Distribution: {dict(source_dist)}")

            except sqlite3.OperationalError as e:
                logger.warning(f"Blacklist entries analysis skipped: {e}")

            # Collection logs analysis if table exists
            try:
                cursor.execute("SELECT COUNT(*) FROM collection_logs;")
                total_logs = cursor.fetchone()[0]
                logger.info(f"Total Collection Logs: {total_logs}")

                # Recent collection activity
                cursor.execute(
                    "SELECT status, COUNT(*) FROM collection_logs GROUP BY status;"
                )
                status_dist = cursor.fetchall()
                logger.info(f"Collection Status Distribution: {dict(status_dist)}")

            except sqlite3.OperationalError as e:
                logger.warning(f"Collection logs analysis skipped: {e}")

        # API data analysis
        try:
            response = requests.get("http://localhost:32542/api/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                logger.info(f"API Health Status: {health_data}")

                if "details" in health_data:
                    details = health_data["details"]
                    logger.info(f"Active IPs: {details.get('active_ips', 0)}")
                    logger.info(f"Total IPs: {details.get('total_ips', 0)}")
                    logger.info(f"Last Update: {details.get('last_update', 'N/A')}")

        except Exception as e:
            logger.warning(f"API health check failed: {e}")

        logger.info("Data analysis completed successfully")
        return True

    except Exception as e:
        logger.error(f"Data analysis failed: {e}")
        return False


def main():
    """Main analysis entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Blacklist System Analysis")
    parser.add_argument(
        "--performance", action="store_true", help="Run performance analysis"
    )
    parser.add_argument("--data", action="store_true", help="Run data analysis")

    args = parser.parse_args()

    if args.performance:
        run_performance_analysis()
    elif args.data:
        run_data_analysis()
    else:
        logger.info("No analysis type specified. Use --performance or --data")
        parser.print_help()


if __name__ == "__main__":
    main()
