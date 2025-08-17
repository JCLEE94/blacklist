#!/usr/bin/env python3
"""
Debug why API doesn't show database data
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


def test_blacklist_manager():
    """Test blacklist manager directly"""
    print("\n🔍 Testing Blacklist Manager...")

    try:
        from src.core.container import get_container

        container = get_container()
        blacklist_mgr = container.get("blacklist_manager")

        if blacklist_mgr:
            print("✅ Blacklist manager initialized")

            # Get active IPs
            active_ips = blacklist_mgr.get_active_ips()
            print(f"   Active IPs: {len(active_ips) if active_ips else 0}")

            if active_ips:
                print(f"   First 5: {active_ips[:5]}")

            # Get all IPs with metadata
            all_data = blacklist_mgr.get_all_blacklist_data()
            print(f"   All data: {len(all_data) if all_data else 0} entries")

            if all_data:
                # Show sample
                for entry in all_data[:3]:
                    print(f"   - {entry}")
        else:
            print("❌ Blacklist manager not available")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


def test_unified_service():
    """Test unified service"""
    print("\n🔍 Testing Unified Service...")

    try:
        from src.core.unified_service import get_unified_service

        service = get_unified_service()
        print("✅ Unified service initialized")

        # Get blacklist stats
        stats = service.get_blacklist_stats()
        print(f"   Stats: {stats}")

        # Get active IPs
        active_ips = service.get_active_ips()
        print(f"   Active IPs from service: {len(active_ips) if active_ips else 0}")

        if active_ips and len(active_ips) > 0:
            print(f"   First 5: {active_ips[:5]}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


def test_api_routes():
    """Test API routes directly"""
    print("\n🔍 Testing API Routes Directly...")

    try:
        # Import Flask app
        from src.core.app_compact import create_app

        app = create_app()

        with app.test_client() as client:
            # Test active IPs endpoint
            response = client.get("/api/blacklist/active")
            print(f"   /api/blacklist/active: {response.status_code}")

            if response.status_code == 200:
                data = response.get_data(as_text=True)
                if data:
                    ips = data.strip().split("\n")
                    print(f"   Response: {len(ips)} IPs")
                    if ips and ips[0]:
                        print(f"   First 3: {ips[:3]}")
                else:
                    print("   Response: Empty")

            # Test enhanced endpoint
            response = client.get("/api/v2/blacklist/enhanced")
            print(f"\n   /api/v2/blacklist/enhanced: {response.status_code}")

            if response.status_code == 200:
                import json

                data = json.loads(response.get_data(as_text=True))
                if data.get("success"):
                    entries = data.get("data", [])
                    print(f"   Response: {len(entries)} entries")
                else:
                    print(f"   Response: Failed - {data.get('message')}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


def check_database_directly():
    """Check database directly"""
    print("\n🔍 Checking Database Directly...")

    import sqlite3

    conn = sqlite3.connect("instance/blacklist.db")
    cursor = conn.cursor()

    # Check if data exists
    cursor.execute("SELECT COUNT(*) FROM blacklist_ips WHERE is_active = 1")
    count = cursor.fetchone()[0]
    print(f"   Active IPs in DB: {count}")

    # Get sample IPs
    cursor.execute(
        """
        SELECT ip_address, source, category 
        FROM blacklist_ips 
        WHERE is_active = 1 
        LIMIT 5
    """
    )
    samples = cursor.fetchall()

    if samples:
        print("   Sample IPs:")
        for ip, source, cat in samples:
            print(f"   - {ip} | {source} | {cat}")

    conn.close()


def main():
    print("=" * 60)
    print("🔍 DEBUG API ISSUES")
    print("=" * 60)

    # Check database first
    check_database_directly()

    # Test blacklist manager
    test_blacklist_manager()

    # Test unified service
    test_unified_service()

    # Test API routes
    test_api_routes()

    print("\n" + "=" * 60)
    print("✅ Debug Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
