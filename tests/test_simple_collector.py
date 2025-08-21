#!/usr/bin/env python3
"""
Test the simple collector which is actually being used
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables
os.environ["REGTECH_USERNAME"] = "nextrade"
os.environ["REGTECH_PASSWORD"] = "test_password"


def test_simple_collector():
    """Test the RegtechSimpleCollector that's actually used by the service"""
    print("\n🔍 Testing RegtechSimpleCollector...")

    try:
        from src.core.regtech_simple_collector import RegtechSimpleCollector

        # Initialize collector
        collector = RegtechSimpleCollector("data")
        print(f"✅ Collector initialized")
        print(f"   Username: {collector.username}")
        print(f"   Base URL: {collector.base_url}")

        # Test collection
        result = collector.collect_from_web()

        if result.get("success"):
            print(f"✅ Collection successful!")
            print(f"   Total collected: {result.get('total_collected', 0)} IPs")
            print(f"   Method: {result.get('method')}")
        else:
            print(f"⚠️ Collection failed: {result.get('error')}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


def test_api_trigger():
    """Test the API trigger endpoint"""
    print("\n🔍 Testing API Trigger...")

    from datetime import datetime

    import requests

    base_url = "http://localhost:32542"

    # Check collection status first
    try:
        resp = requests.get(f"{base_url}/api/collection/status")
        if resp.status_code == 200:
            status = resp.json()
            print(f"✅ Collection status: Enabled={status.get('collection_enabled')}")
    except Exception as e:
        print(f"⚠️ Status check error: {e}")

    # Trigger REGTECH collection
    print("\nTriggering REGTECH collection via API...")
    try:
        response = requests.post(
            f"{base_url}/api/collection/regtech/trigger",
            json={
                "start_date": datetime.now().strftime("%Y-%m-%d"),
                "end_date": datetime.now().strftime("%Y-%m-%d"),
            },
            timeout=60,
        )

        print(f"   Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"   Success: {data.get('success')}")
            print(f"   Message: {data.get('message')}")

            if data.get("success"):
                # Check for collected IPs
                result = data.get("data", {})
                print(f"   Collection result: {result}")
        else:
            print(f"   Error Response: {response.text[:500]}")

    except requests.Timeout:
        print("⚠️ Request timed out (collection might still be running)")
    except Exception as e:
        print(f"❌ API trigger error: {e}")


def check_database():
    """Check database for collected data"""
    print("\n🔍 Checking Database...")

    try:
        import sqlite3

        conn = sqlite3.connect("instance/blacklist.db")
        cursor = conn.cursor()

        # Check total IPs
        cursor.execute("SELECT COUNT(*) FROM blacklist_ips")
        total = cursor.fetchone()[0]
        print(f"✅ Total IPs in database: {total}")

        # Check by source
        cursor.execute("SELECT source, COUNT(*) FROM blacklist_ips GROUP BY source")
        sources = cursor.fetchall()
        if sources:
            print("   By source:")
            for source, count in sources:
                print(f"   - {source}: {count} IPs")

        # Show recent IPs
        cursor.execute(
            """
            SELECT ip_address, source, category, added_date
            FROM blacklist_ips
            ORDER BY added_date DESC
            LIMIT 5
        """
        )
        recent = cursor.fetchall()
        if recent:
            print("\n   Recent IPs:")
            for ip, source, cat, date in recent:
                print(f"   - {ip} | {source} | {cat} | {date}")

        conn.close()

    except Exception as e:
        print(f"❌ Database error: {e}")


def main():
    """Run all tests"""
    print("=" * 60)
    print("📊 Simple Collector Test Suite")
    print("=" * 60)

    # Test simple collector directly
    test_simple_collector()

    # Test API trigger
    test_api_trigger()

    # Check database
    check_database()

    print("\n" + "=" * 60)
    print("✅ Test Suite Completed")
    print("=" * 60)


if __name__ == "__main__":
    main()
