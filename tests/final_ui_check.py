#!/usr/bin/env python3
"""
Final UI check - verify data appears in all endpoints
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables
os.environ["REGTECH_USERNAME"] = "nextrade"
os.environ["REGTECH_PASSWORD"] = "test_password"
os.environ["COLLECTION_ENABLED"] = "true"
os.environ["FORCE_DISABLE_COLLECTION"] = "false"


def test_with_flask_app():
    """Test using Flask test client directly"""
    print("\n🔍 Testing with Flask App Directly...")

    try:
        from src.core.app_compact import create_app

        app = create_app()

        with app.test_client() as client:
            # 1. Active IPs (text)
            print("\n📡 /api/blacklist/active:")
            response = client.get("/api/blacklist/active")
            if response.status_code == 200:
                data = response.get_data(as_text=True)
                if data:
                    ips = data.strip().split("\n")
                    print(f"   ✅ {len(ips)} IPs returned")
                    if ips and ips[0]:
                        print(f"   First 5:")
                        for ip in ips[:5]:
                            print(f"     - {ip}")
                else:
                    print("   ❌ Empty response")
            else:
                print(f"   ❌ HTTP {response.status_code}")

            # 2. FortiGate format
            print("\n📡 /api/fortigate:")
            response = client.get("/api/fortigate")
            if response.status_code == 200:
                import json

                data = json.loads(response.get_data(as_text=True))
                if "blacklist" in data:
                    print(f"   ✅ {len(data['blacklist'])} IPs in blacklist")
                    if data["blacklist"]:
                        print(f"   First 5:")
                        for ip in data["blacklist"][:5]:
                            print(f"     - {ip}")
                else:
                    print(f"   ❌ No blacklist field")
            else:
                print(f"   ❌ HTTP {response.status_code}")

            # 3. Enhanced endpoint
            print("\n📡 /api/v2/blacklist/enhanced:")
            response = client.get("/api/v2/blacklist/enhanced")
            if response.status_code == 200:
                import json

                data = json.loads(response.get_data(as_text=True))
                if data.get("success"):
                    entries = data.get("data", [])
                    print(f"   ✅ {len(entries)} entries")
                    if entries:
                        print(f"   First 3:")
                        for entry in entries[:3]:
                            print(
                                f"     - {entry.get('ip_address')} | {entry.get('source')} | {entry.get('category')}"
                            )
                else:
                    print(f"   ⚠️ Not successful: {data.get('message')}")
            else:
                print(f"   ❌ HTTP {response.status_code}")

            # 4. Collection status
            print("\n📡 /api/collection/status:")
            response = client.get("/api/collection/status")
            if response.status_code == 200:
                import json

                data = json.loads(response.get_data(as_text=True))
                stats = data.get("stats", {})
                print(f"   Collection enabled: {data.get('collection_enabled')}")
                print(f"   Total IPs: {stats.get('total_ips', 0)}")
                print(f"   Active IPs: {stats.get('active_ips', 0)}")
            else:
                print(f"   ❌ HTTP {response.status_code}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


def check_database_direct():
    """Direct database check"""
    print("\n🔍 Direct Database Check:")

    import sqlite3

    conn = sqlite3.connect("instance/blacklist.db")
    cursor = conn.cursor()

    # Check active IPs
    cursor.execute("SELECT COUNT(*) FROM blacklist_ips WHERE is_active = 1")
    active = cursor.fetchone()[0]
    print(f"   Active IPs in DB: {active}")

    # By source
    cursor.execute(
        """
        SELECT source, COUNT(*)
        FROM blacklist_ips
        WHERE is_active = 1
        GROUP BY source
    """
    )
    sources = cursor.fetchall()
    for source, count in sources:
        print(f"   - {source}: {count}")

    conn.close()


def check_service_direct():
    """Check service directly"""
    print("\n🔍 Direct Service Check:")

    try:
        from src.core.unified_service import get_unified_service

        service = get_unified_service()

        # Get active IPs
        active_ips = service.get_active_ips()
        print(f"   Service active IPs: {len(active_ips) if active_ips else 0}")

        if active_ips and len(active_ips) > 0:
            print(f"   First 5: {active_ips[:5]}")

    except Exception as e:
        print(f"   Error: {e}")


def main():
    print("=" * 60)
    print("🎯 FINAL UI CHECK - 실제 데이터 표시 확인")
    print("=" * 60)

    # Check database
    check_database_direct()

    # Check service
    check_service_direct()

    # Test with Flask app
    test_with_flask_app()

    print("\n" + "=" * 60)
    print("✅ Check Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
