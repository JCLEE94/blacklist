#!/usr/bin/env python3
"""
Fixed data collection test - properly using CollectionConfig
"""

import os
import sys
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables
os.environ["REGTECH_USERNAME"] = "nextrade"
os.environ["REGTECH_PASSWORD"] = "test_password"
os.environ["SECUDIUM_USERNAME"] = "nextrade"
os.environ["SECUDIUM_PASSWORD"] = "test_password"
os.environ["REGTECH_BASE_URL"] = "https://regtech.fsec.or.kr"
os.environ["SECUDIUM_BASE_URL"] = "https://www.secudium.com"


def test_regtech_direct():
    """Test REGTECH collector directly"""
    print("\n🔍 Testing REGTECH Direct Collection...")

    try:
        from src.core.collectors.regtech_collector import RegtechCollector
        from src.core.collectors.unified_collector import CollectionConfig

        # Create config with proper structure
        config = CollectionConfig(
            enabled=True,
            settings={
                "username": "nextrade",
                "password": "test_password",
                "base_url": "https://regtech.fsec.or.kr",
            },
        )

        # Initialize collector
        collector = RegtechCollector(config)
        print(f"✅ REGTECH collector initialized with user: {collector.username}")

        # Test collection
        result = collector.collect()

        if result.get("success"):
            print(
                f"✅ REGTECH collection successful: {result.get('total_collected', 0)} IPs"
            )
            print(f"   Data: {result.get('data', [])[:5]}")  # Show first 5 entries
        else:
            print(f"⚠️ REGTECH collection failed: {result.get('error')}")

    except Exception as e:
        print(f"❌ REGTECH error: {e}")
        import traceback

        traceback.print_exc()


def test_collector_factory():
    """Test using the collector factory"""
    print("\n🔍 Testing Collector Factory...")

    try:
        from src.core.collectors.collector_factory import CollectorFactory

        # Get factory instance
        factory = CollectorFactory.get_instance()
        print(f"✅ Factory initialized")

        # Get REGTECH collector
        regtech = factory.get_collector("regtech")
        if regtech:
            print(f"✅ REGTECH collector available from factory")

            # Try collection
            result = regtech.collect()
            if result.get("success"):
                print(
                    f"✅ Factory REGTECH collection: {result.get('total_collected', 0)} IPs"
                )
            else:
                print(f"⚠️ Factory REGTECH failed: {result.get('error')}")
        else:
            print(f"⚠️ REGTECH collector not available in factory")

    except Exception as e:
        print(f"❌ Factory error: {e}")
        import traceback

        traceback.print_exc()


def test_api_trigger_with_auth():
    """Test API trigger with proper authentication"""
    print("\n🔍 Testing API Triggers with Auth...")

    import requests

    base_url = "http://localhost:32542/api/collection"

    # First ensure collection is enabled
    try:
        response = requests.post(
            f"{base_url}/enable", json={"clear_data": False}, timeout=10
        )
        print(f"✅ Collection enable status: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Enable error: {e}")

    # Test REGTECH trigger
    print("\nTriggering REGTECH via API...")
    try:
        response = requests.post(
            f"{base_url}/regtech/trigger",
            json={
                "start_date": datetime.now().strftime("%Y-%m-%d"),
                "end_date": datetime.now().strftime("%Y-%m-%d"),
            },
            timeout=60,
        )

        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Success: {data.get('success')}")
            print(f"   Message: {data.get('message')}")
            if data.get("success"):
                print(f"   Collected: {data.get('ips_collected', 0)} IPs")
        else:
            print(f"   Response: {response.text[:200]}")

    except Exception as e:
        print(f"❌ REGTECH API error: {e}")


def check_database_data():
    """Check if data is in database"""
    print("\n🔍 Checking Database for Data...")

    try:
        import sqlite3

        # Connect to database
        db_path = "/home/jclee/app/blacklist/instance/blacklist.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check blacklist_ips table
        cursor.execute("SELECT COUNT(*) FROM blacklist_ips")
        total_ips = cursor.fetchone()[0]
        print(f"✅ Total IPs in database: {total_ips}")

        # Check by source
        cursor.execute("SELECT source, COUNT(*) FROM blacklist_ips GROUP BY source")
        sources = cursor.fetchall()
        for source, count in sources:
            print(f"   - {source}: {count} IPs")

        # Show sample data
        cursor.execute(
            "SELECT ip_address, source, category, added_date FROM blacklist_ips LIMIT 5"
        )
        samples = cursor.fetchall()
        if samples:
            print("\n   Sample data:")
            for ip, source, category, date in samples:
                print(f"   - {ip} | {source} | {category} | {date}")

        conn.close()

    except Exception as e:
        print(f"❌ Database check error: {e}")


def main():
    """Run all tests"""
    print("=" * 60)
    print("📊 Fixed Data Collection Test Suite")
    print("=" * 60)

    # Test direct collection
    test_regtech_direct()

    # Test via factory
    test_collector_factory()

    # Test API triggers
    test_api_trigger_with_auth()

    # Check database
    check_database_data()

    print("\n" + "=" * 60)
    print("✅ Test Suite Completed")
    print("=" * 60)


if __name__ == "__main__":
    main()
