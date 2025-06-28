#!/usr/bin/env python3
"""
Test API data loading from database
"""
import requests
import json

# Test endpoints
base_url = "http://localhost:2541"

print("Testing API endpoints...\n")

# 1. Health check
try:
    response = requests.get(f"{base_url}/health")
    print(f"1. Health Check: {response.status_code}")
    print(f"   Response: {response.text[:100]}...\n")
except Exception as e:
    print(f"1. Health Check failed: {e}\n")

# 2. Stats
try:
    response = requests.get(f"{base_url}/api/stats")
    data = response.json()
    print(f"2. Stats: {response.status_code}")
    print(f"   Active IPs: {data['data']['active_ips']}")
    print(f"   REGTECH count: {data['data']['regtech_count']}")
    print(f"   Database connected: {data['data']['database_connected']}\n")
except Exception as e:
    print(f"2. Stats failed: {e}\n")

# 3. Active blacklist
try:
    response = requests.get(f"{base_url}/api/blacklist/active")
    ips = response.text.strip().split('\n') if response.text else []
    print(f"3. Active Blacklist: {response.status_code}")
    print(f"   Total IPs: {len(ips)}")
    if ips and ips[0]:
        print(f"   First 5 IPs: {ips[:5]}\n")
    else:
        print("   No IPs returned\n")
except Exception as e:
    print(f"3. Active Blacklist failed: {e}\n")

# 4. FortiGate format
try:
    response = requests.get(f"{base_url}/api/fortigate")
    data = response.json()
    print(f"4. FortiGate Format: {response.status_code}")
    print(f"   Total count: {data['total_count']}")
    print(f"   Entries: {len(data['threat_feed']['entries'])}\n")
except Exception as e:
    print(f"4. FortiGate Format failed: {e}\n")

# 5. Collection status
try:
    response = requests.get(f"{base_url}/api/collection/status")
    data = response.json()
    print(f"5. Collection Status: {response.status_code}")
    print(f"   Collection enabled: {data['status']['collection_enabled']}")
    print(f"   Total IPs collected: {data['status']['summary']['total_ips_collected']}")
    for source, info in data['status']['sources'].items():
        print(f"   {source}: {info['total_ips']} IPs\n")
except Exception as e:
    print(f"5. Collection Status failed: {e}\n")

# 6. Test database directly
print("6. Direct Database Check:")
import sqlite3
try:
    conn = sqlite3.connect('instance/blacklist.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM blacklist_ip")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM blacklist_ip WHERE source = 'REGTECH'")
    regtech = cursor.fetchone()[0]
    conn.close()
    print(f"   Total IPs in DB: {total}")
    print(f"   REGTECH IPs in DB: {regtech}")
except Exception as e:
    print(f"   Database check failed: {e}")