#!/usr/bin/env python3
"""
Fix async collection issues - proper async/await handling
"""

import asyncio
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables
os.environ["REGTECH_USERNAME"] = "nextrade"
os.environ["REGTECH_PASSWORD"] = "test_password"


def run_async(async_func):
    """Helper to run async function in sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(async_func)
    finally:
        loop.close()


async def test_regtech_async():
    """Test REGTECH collector with proper async handling"""
    print("\n🔍 Testing REGTECH Collection (Async)...")

    try:
        from src.core.collectors.regtech_collector import RegtechCollector
        from src.core.collectors.unified_collector import CollectionConfig

        # Create config
        config = CollectionConfig(
            enabled=True, settings={"username": "nextrade", "password": "test_password"}
        )

        # Initialize collector
        collector = RegtechCollector(config)
        print(f"✅ Collector initialized")
        print(f"   Username: {collector.username}")
        print(f"   Base URL: {collector.base_url}")

        # The collect method in BaseCollector is sync, not async
        # It internally calls _collect_data which is async
        # So we need to call collect() directly, not await it

        # Check if collect is a coroutine function
        import inspect

        if inspect.iscoroutinefunction(collector.collect):
            print("   collect() is async, awaiting...")
            result = await collector.collect()
        else:
            print("   collect() is sync, calling directly...")
            result = collector.collect()

        # Check result
        if result and result.get("success"):
            print(f"✅ Collection successful!")
            print(f"   Total collected: {result.get('total_collected', 0)} IPs")

            # Show sample data
            data = result.get("data", [])
            if data:
                print(f"\n   Sample data (first 3):")
                for ip_info in data[:3]:
                    if isinstance(ip_info, dict):
                        print(
                            f"   - {ip_info.get('ip', 'N/A')} | {ip_info.get('source', 'N/A')}"
                        )
                    else:
                        print(f"   - {ip_info}")
        else:
            error = result.get("error") if result else "Unknown error"
            print(f"⚠️ Collection failed: {error}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


def test_sync_collection():
    """Test synchronous collection"""
    print("\n🔍 Testing Sync Collection Wrapper...")

    try:
        from src.core.collectors.regtech_collector import RegtechCollector
        from src.core.collectors.unified_collector import CollectionConfig

        # Create config
        config = CollectionConfig(
            enabled=True, settings={"username": "nextrade", "password": "test_password"}
        )

        # Initialize collector
        collector = RegtechCollector(config)
        print(f"✅ Collector initialized")

        # The BaseCollector.collect() method should handle async internally
        # It uses asyncio.run() to execute _collect_data
        result = collector.collect()

        if result and result.get("success"):
            print(f"✅ Sync collection successful!")
            print(f"   Total collected: {result.get('total_collected', 0)} IPs")
        else:
            error = result.get("error", "Unknown error")
            print(f"⚠️ Collection failed: {error}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


def insert_test_data():
    """Insert test data directly to database"""
    print("\n🔍 Inserting Test Data...")

    try:
        import sqlite3

        conn = sqlite3.connect("instance/blacklist.db")
        cursor = conn.cursor()

        # Insert test IPs
        test_ips = [
            ("192.168.100.1", "REGTECH", "malware", 8, "Test IP 1"),
            ("10.20.30.40", "REGTECH", "botnet", 9, "Test IP 2"),
            ("172.16.50.60", "SECUDIUM", "phishing", 7, "Test IP 3"),
        ]

        for ip, source, category, threat, desc in test_ips:
            cursor.execute(
                """
                INSERT OR REPLACE INTO blacklist_ips 
                (ip_address, source, category, threat_level, description, added_date, is_active)
                VALUES (?, ?, ?, ?, ?, datetime('now'), 1)
            """,
                (ip, source, category, threat, desc),
            )

        conn.commit()

        # Verify
        cursor.execute(
            "SELECT COUNT(*) FROM blacklist_ips WHERE source IN ('REGTECH', 'SECUDIUM')"
        )
        count = cursor.fetchone()[0]
        print(f"✅ Test data inserted. Total REGTECH/SECUDIUM IPs: {count}")

        conn.close()

    except Exception as e:
        print(f"❌ Database error: {e}")


def check_api_endpoints():
    """Check if data appears in API endpoints"""
    print("\n🔍 Checking API Endpoints...")

    import requests

    base_url = "http://localhost:32542"

    # Check collection status
    try:
        resp = requests.get(f"{base_url}/api/collection/status")
        if resp.status_code == 200:
            status = resp.json()
            print(f"✅ Collection status:")
            print(f"   Enabled: {status.get('collection_enabled')}")
            print(f"   Total IPs: {status.get('stats', {}).get('total_ips', 0)}")
    except Exception as e:
        print(f"⚠️ Status check error: {e}")

    # Check active IPs
    try:
        resp = requests.get(f"{base_url}/api/blacklist/active")
        if resp.status_code == 200:
            ips = resp.text.strip().split("\n")
            if ips and ips[0]:
                print(f"✅ Active IPs endpoint: {len(ips)} IPs found")
                print(f"   Sample: {ips[:3]}")
            else:
                print("⚠️ No active IPs found")
    except Exception as e:
        print(f"⚠️ Active IPs error: {e}")

    # Check enhanced endpoint
    try:
        resp = requests.get(f"{base_url}/api/v2/blacklist/enhanced")
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success") and data.get("data"):
                print(f"✅ Enhanced endpoint: {len(data['data'])} entries")
                for entry in data["data"][:3]:
                    print(f"   - {entry.get('ip_address')} | {entry.get('source')}")
            else:
                print("⚠️ No data in enhanced endpoint")
    except Exception as e:
        print(f"⚠️ Enhanced endpoint error: {e}")


def main():
    """Main test function"""
    print("=" * 60)
    print("🔧 Async Collection Fix Test")
    print("=" * 60)

    # Test async collection
    print("\n[1] Testing async collection...")
    run_async(test_regtech_async())

    # Test sync wrapper
    print("\n[2] Testing sync collection...")
    test_sync_collection()

    # Insert test data to ensure something is visible
    print("\n[3] Inserting test data...")
    insert_test_data()

    # Check API endpoints
    print("\n[4] Checking API endpoints...")
    check_api_endpoints()

    print("\n" + "=" * 60)
    print("✅ Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
