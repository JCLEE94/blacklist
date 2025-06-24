#!/usr/bin/env python3
"""
Web Interface Verification Script

This script tests the web interface to ensure the imported blacklist IPs
are accessible through all endpoints.
"""

import requests
import json
import time

def test_endpoint(url, expected_content=None):
    """Test a single endpoint"""
    try:
        response = requests.get(url, timeout=10)
        print(f"✅ {url}: Status {response.status_code}")
        
        if response.status_code == 200:
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
                print(f"   Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                if expected_content and expected_content in str(data):
                    print(f"   ✅ Found expected content: {expected_content}")
                return data
            else:
                content = response.text[:200]
                print(f"   Text content: {content}...")
                if expected_content and expected_content in response.text:
                    print(f"   ✅ Found expected content: {expected_content}")
                return response.text
        else:
            print(f"   ❌ Error: {response.text[:100]}")
            
    except Exception as e:
        print(f"❌ {url}: Error - {e}")
        
    return None

def test_search_endpoints():
    """Test search functionality for imported IPs"""
    test_ips = [
        "3.138.185.30",      # REGTECH IP
        "37.120.247.113",    # SECUDIUM IP
        "185.220.101.42",    # SECUDIUM IP
        "199.195.250.77"     # SECUDIUM IP
    ]
    
    print("\n🔍 Testing Search Endpoints:")
    for ip in test_ips:
        print(f"\nTesting IP: {ip}")
        result = test_endpoint(f"http://localhost:8541/api/search/{ip}", ip)
        if result and isinstance(result, dict):
            found = result.get('result', {}).get('found', False)
            print(f"   Found in blacklist: {found}")

def test_fortigate_endpoint():
    """Test FortiGate external connector endpoint"""
    print("\n🛡️ Testing FortiGate Endpoint:")
    result = test_endpoint("http://localhost:8541/api/fortigate")
    if result and isinstance(result, dict):
        entries = result.get('entries', [])
        print(f"   FortiGate entries count: {len(entries)}")
        if entries:
            sample_entry = entries[0]
            print(f"   Sample entry: {sample_entry}")

def test_stats_breakdown():
    """Test detailed stats breakdown"""
    print("\n📊 Testing Stats Breakdown:")
    result = test_endpoint("http://localhost:8541/api/stats")
    if result and isinstance(result, dict):
        database = result.get('database', {})
        total_ips = database.get('total_ips', 0)
        categories = database.get('categories', {})
        print(f"   Total IPs in database: {total_ips}")
        print(f"   Categories: {categories}")
        
        # Check monthly data
        monthly = database.get('monthly', [])
        if monthly:
            latest_month = monthly[-1]
            print(f"   Latest month data: {latest_month}")

def main():
    """Main verification function"""
    print("🚀 Starting Web Interface Verification")
    print("=" * 60)
    
    # Basic health check
    print("🏥 Testing Health Endpoint:")
    test_endpoint("http://localhost:8541/health", "healthy")
    
    # Test stats
    test_stats_breakdown()
    
    # Test active blacklist
    print("\n📋 Testing Active Blacklist:")
    test_endpoint("http://localhost:8541/api/blacklist/active")
    
    # Test FortiGate
    test_fortigate_endpoint()
    
    # Test search
    test_search_endpoints()
    
    # Test batch search
    print("\n🔍 Testing Batch Search:")
    batch_data = {
        "ips": ["3.138.185.30", "37.120.247.113", "1.1.1.1"]
    }
    try:
        response = requests.post(
            "http://localhost:8541/api/search", 
            json=batch_data,
            timeout=10
        )
        print(f"✅ Batch search: Status {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Results count: {len(data.get('results', []))}")
    except Exception as e:
        print(f"❌ Batch search: Error - {e}")
    
    # Test enhanced endpoints
    print("\n⚡ Testing Enhanced Endpoints:")
    test_endpoint("http://localhost:8541/api/v2/blacklist/enhanced")
    test_endpoint("http://localhost:8541/api/v2/analytics/trends")
    
    print("\n" + "=" * 60)
    print("✅ Web Interface Verification Complete")

if __name__ == "__main__":
    main()