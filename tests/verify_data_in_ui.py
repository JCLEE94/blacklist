#!/usr/bin/env python3
"""
Verify that real collected data appears in UI
"""

import json
import sqlite3

import requests


def check_database():
    """Check what's actually in the database"""
    print("\n📊 Database Status:")
    print("-" * 40)

    conn = sqlite3.connect("instance/blacklist.db")
    cursor = conn.cursor()

    # Total count by source
    cursor.execute(
        """
        SELECT source, COUNT(*), MIN(added_date), MAX(added_date)
        FROM blacklist_ips
        GROUP BY source
    """
    )
    results = cursor.fetchall()

    print("By Source:")
    for source, count, min_date, max_date in results:
        print(f"  {source}: {count} IPs")
        print(f"    Date range: {min_date} to {max_date}")

    # Check active IPs
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM blacklist_ips
        WHERE is_active = 1
    """
    )
    active_count = cursor.fetchone()[0]
    print(f"\nActive IPs: {active_count}")

    # Sample of REGTECH data
    cursor.execute(
        """
        SELECT ip_address, category, threat_level, added_date
        FROM blacklist_ips
        WHERE source = 'REGTECH' AND is_active = 1
        LIMIT 5
    """
    )
    samples = cursor.fetchall()

    if samples:
        print("\nSample REGTECH IPs (real data):")
        for ip, cat, threat, date in samples:
            print(f"  {ip} | {cat} | Threat: {threat} | {date}")

    conn.close()
    return active_count > 0


def check_api_endpoints():
    """Check all API endpoints"""
    print("\n📡 API Endpoints Status:")
    print("-" * 40)

    base_url = "http://localhost:32542"

    # 1. Health check
    try:
        resp = requests.get(f"{base_url}/health")
        print(f"Health: {resp.status_code}")
    except Exception as e:
        print(f"Health: Error - {e}")

    # 2. Collection status
    try:
        resp = requests.get(f"{base_url}/api/collection/status")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Collection Status: Enabled={data.get('collection_enabled')}")
            stats = data.get("stats", {})
            print(f"  Total IPs: {stats.get('total_ips', 0)}")
            print(f"  Active IPs: {stats.get('active_ips', 0)}")
    except Exception as e:
        print(f"Collection Status: Error - {e}")

    # 3. Active IPs (text format)
    try:
        resp = requests.get(f"{base_url}/api/blacklist/active")
        if resp.status_code == 200:
            text = resp.text.strip()
            if text:
                ips = text.split("\n")
                print(f"Active IPs (text): {len(ips)} IPs")
                if len(ips) > 0:
                    print(f"  First 3: {ips[:3]}")
            else:
                print("Active IPs (text): Empty response")
    except Exception as e:
        print(f"Active IPs: Error - {e}")

    # 4. Enhanced endpoint (JSON format)
    try:
        resp = requests.get(f"{base_url}/api/v2/blacklist/enhanced")
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                entries = data.get("data", [])
                print(f"Enhanced Endpoint: {len(entries)} entries")

                # Count by source
                sources = {}
                for entry in entries:
                    src = entry.get("source", "unknown")
                    sources[src] = sources.get(src, 0) + 1

                if sources:
                    print("  By source:")
                    for src, cnt in sources.items():
                        print(f"    {src}: {cnt}")

                # Show first few
                if entries:
                    print("  First 3 entries:")
                    for entry in entries[:3]:
                        print(
                            f"    {entry.get('ip_address')} | {entry.get('source')} | {entry.get('category')}"
                        )
            else:
                print(f"Enhanced Endpoint: Failed - {data.get('message')}")
        else:
            print(f"Enhanced Endpoint: HTTP {resp.status_code}")
    except Exception as e:
        print(f"Enhanced Endpoint: Error - {e}")

    # 5. FortiGate format
    try:
        resp = requests.get(f"{base_url}/api/fortigate")
        if resp.status_code == 200:
            text = resp.text
            try:
                data = json.loads(text)
                if "blacklist" in data:
                    print(f"FortiGate Format: {len(data['blacklist'])} IPs")
                    if data["blacklist"]:
                        print(f"  First 3: {data['blacklist'][:3]}")
                elif "data" in data:
                    print(f"FortiGate Format: {len(data['data'])} entries")
            except:
                lines = text.strip().split("\n")
                print(f"FortiGate Format: {len(lines)} lines")
        else:
            print(f"FortiGate Format: HTTP {resp.status_code}")
    except Exception as e:
        print(f"FortiGate Format: Error - {e}")


def test_authentication():
    """Test if authentication info is saved and working"""
    print("\n🔐 Authentication Test:")
    print("-" * 40)

    import os

    # Check environment variables
    username = os.getenv("REGTECH_USERNAME")
    password = os.getenv("REGTECH_PASSWORD")

    print(f"REGTECH_USERNAME: {'✅ Set' if username else '❌ Not set'}")
    print(f"REGTECH_PASSWORD: {'✅ Set' if password else '❌ Not set'}")

    if username and password:
        print(f"  Username: {username}")
        print(f"  Password: {'*' * len(password)}")

    # Check if credentials work for collection
    if username and password:
        from src.core.regtech_simple_collector import RegtechSimpleCollector

        try:
            collector = RegtechSimpleCollector("data")
            print("\n✅ Collector initialized with credentials")

            # Do a quick test (don't actually collect)
            session = requests.Session()
            login_success = collector._simple_login(session)

            if login_success:
                print("✅ Login successful with saved credentials")
            else:
                print("❌ Login failed with saved credentials")

        except Exception as e:
            print(f"❌ Error testing credentials: {e}")


def main():
    print("=" * 60)
    print("🔍 VERIFY DATA IN UI - REAL DATA ONLY")
    print("=" * 60)

    # Check database
    has_data = check_database()

    if not has_data:
        print("\n⚠️ No active data in database. Loading real collected data...")
        # Load the data we collected
        import subprocess

        result = subprocess.run(
            ["python3", "tests/load_collected_to_db.py"], capture_output=True, text=True
        )
        print("Data loading complete")

    # Check API endpoints
    check_api_endpoints()

    # Test authentication
    test_authentication()

    print("\n" + "=" * 60)
    print("✅ Verification Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
