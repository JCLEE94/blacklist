#!/usr/bin/env python3
"""
Test enhanced endpoint after table fix
"""

import json
import os
import sys

import requests

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_all_endpoints():
    """Test all endpoints after fix"""
    print("🔍 Testing All Endpoints After Fix\n")

    base_url = "http://localhost:32542"

    # 1. Active IPs
    print("📡 /api/blacklist/active:")
    try:
        resp = requests.get(f"{base_url}/api/blacklist/active")
        if resp.status_code == 200:
            ips = resp.text.strip().split("\n")
            if ips and ips[0]:
                print(f"  ✅ {len(ips)} IPs returned")
                print(f"  First 3: {ips[:3]}")
        else:
            print(f"  ❌ HTTP {resp.status_code}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # 2. Enhanced endpoint
    print("\n📡 /api/v2/blacklist/enhanced:")
    try:
        resp = requests.get(f"{base_url}/api/v2/blacklist/enhanced")
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                entries = data.get("data", [])
                print(f"  ✅ {len(entries)} entries returned")

                if entries:
                    print("\n  First 3 entries:")
                    for entry in entries[:3]:
                        ip = entry.get("ip_address")
                        source = entry.get("source")
                        dtype = entry.get("detection_type", entry.get("category"))
                        date = entry.get("detection_date", entry.get("added_date"))
                        print(f"    {ip} | {source} | {dtype}")
                        print(f"      Detection: {date}")
            else:
                print(f"  ⚠️ Not successful: {data.get('message')}")
        else:
            print(f"  ❌ HTTP {resp.status_code}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # 3. FortiGate
    print("\n📡 /api/fortigate:")
    try:
        resp = requests.get(f"{base_url}/api/fortigate")
        if resp.status_code == 200:
            data = resp.json()
            if "blacklist" in data:
                print(f"  ✅ {len(data['blacklist'])} IPs")
                print(f"  First 3: {data['blacklist'][:3]}")
        else:
            print(f"  ❌ HTTP {resp.status_code}")
    except Exception as e:
        print(f"  ❌ Error: {e}")


def check_database_tables():
    """Check both tables"""
    print("\n📊 Database Tables Status:\n")

    import sqlite3

    conn = sqlite3.connect("instance/blacklist.db")
    cursor = conn.cursor()

    # Check blacklist_ips
    cursor.execute("SELECT COUNT(*) FROM blacklist_ips WHERE is_active = 1")
    bl_count = cursor.fetchone()[0]
    print(f"  blacklist_ips: {bl_count} active IPs")

    # Check ip_detections
    cursor.execute("SELECT COUNT(*) FROM ip_detections WHERE is_active = 1")
    det_count = cursor.fetchone()[0]
    print(f"  ip_detections: {det_count} active IPs")

    # Show date difference example
    print("\n📅 Date Example (수집일 vs 탐지일):")
    cursor.execute(
        """
        SELECT 
            ip_address,
            source,
            detection_date,
            created_at
        FROM ip_detections
        WHERE source = 'REGTECH'
        LIMIT 3
    """
    )

    samples = cursor.fetchall()
    for ip, source, detect_date, collect_date in samples:
        print(f"\n  IP: {ip}")
        print(f"    탐지일: {detect_date}")
        print(f"    수집일: {collect_date}")

    conn.close()


def main():
    print("=" * 60)
    print("🎯 TEST AFTER TABLE FIX")
    print("=" * 60)

    # Check database
    check_database_tables()

    # Test endpoints
    print("\n" + "-" * 60)
    test_all_endpoints()

    print("\n" + "=" * 60)
    print("✅ Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
