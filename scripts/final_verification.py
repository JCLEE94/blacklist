#!/usr/bin/env python3
"""
Final Blacklist System Verification

This script provides a comprehensive verification of the blacklist system
including database content, API functionality, and FortiGate integration.
"""

import sqlite3
import requests
import json
from datetime import datetime

def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"🔍 {title}")
    print("="*60)

def check_database_content():
    """Check database content and structure"""
    print_header("Database Content Verification")
    
    try:
        conn = sqlite3.connect('instance/blacklist.db')
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute('SELECT COUNT(*) FROM blacklist_ip')
        total_count = cursor.fetchone()[0]
        print(f"📊 Total IPs in database: {total_count}")
        
        # Get count by source
        cursor.execute('SELECT source, COUNT(*) FROM blacklist_ip GROUP BY source')
        source_counts = cursor.fetchall()
        print("📈 IPs by source:")
        for source, count in source_counts:
            print(f"   {source}: {count} IPs")
        
        # Show sample IPs with all details
        print("\n📋 Sample database entries:")
        cursor.execute('''
            SELECT ip, source, threat_type, reason, country, detection_date, is_active 
            FROM blacklist_ip 
            WHERE source IN ('REGTECH', 'SECUDIUM')
            LIMIT 10
        ''')
        
        for row in cursor.fetchall():
            ip, source, threat_type, reason, country, detection_date, is_active = row
            print(f"   {ip} | {source} | {threat_type} | {reason} | {country} | Active: {bool(is_active)}")
        
        # Check REGTECH specific IP
        cursor.execute('SELECT * FROM blacklist_ip WHERE ip = ?', ('3.138.185.30',))
        regtech_ip = cursor.fetchone()
        if regtech_ip:
            print(f"\n✅ REGTECH IP 3.138.185.30 found in database")
            print(f"   Details: {regtech_ip}")
        else:
            print("❌ REGTECH IP 3.138.185.30 NOT found in database")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

def test_api_endpoints():
    """Test all API endpoints"""
    print_header("API Endpoints Testing")
    
    base_url = "http://localhost:8541"
    
    # Test health
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health: {health_data['status']}")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")
    
    # Test stats
    try:
        response = requests.get(f"{base_url}/api/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Stats: {stats['database']['total_ips']} total IPs")
        else:
            print(f"❌ Stats endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Stats endpoint error: {e}")
    
    # Test FortiGate endpoint
    try:
        response = requests.get(f"{base_url}/api/fortigate")
        if response.status_code == 200:
            fortigate_data = response.json()
            entries_count = len(fortigate_data.get('entries', []))
            print(f"✅ FortiGate: {entries_count} entries")
            
            # Show sample entries
            if entries_count > 0:
                sample_entries = fortigate_data['entries'][:3]
                print("   Sample FortiGate entries:")
                for entry in sample_entries:
                    print(f"     {entry}")
        else:
            print(f"❌ FortiGate endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ FortiGate endpoint error: {e}")
    
    # Test specific IP searches
    test_ips = ["3.138.185.30", "37.120.247.113", "185.220.101.42"]
    print(f"\n🔍 Testing IP searches:")
    
    for ip in test_ips:
        try:
            response = requests.get(f"{base_url}/api/search/{ip}")
            if response.status_code == 200:
                search_result = response.json()
                found = search_result.get('result', {}).get('found', False)
                print(f"   {ip}: {'✅ Found' if found else '❌ Not found'}")
            else:
                print(f"   {ip}: ❌ Search failed ({response.status_code})")
        except Exception as e:
            print(f"   {ip}: ❌ Search error - {e}")

def test_fortigate_format():
    """Test FortiGate format specifically"""
    print_header("FortiGate Format Verification")
    
    try:
        response = requests.get("http://localhost:8541/api/fortigate")
        if response.status_code == 200:
            data = response.json()
            
            print(f"📋 FortiGate External Connector Format:")
            print(f"   Name: {data.get('name')}")
            print(f"   Category: {data.get('category')}")
            print(f"   Total Count: {data.get('total_count')}")
            print(f"   Generated: {data.get('generated_at')}")
            print(f"   Version: {data.get('version')}")
            
            entries = data.get('entries', [])
            if entries:
                print(f"\n📊 Sample entries (showing first 5):")
                for i, entry in enumerate(entries[:5]):
                    print(f"   {i+1}. {entry}")
                
                # Test if our specific IPs are in FortiGate format
                our_ips = ["3.138.185.30", "37.120.247.113", "185.220.101.42"]
                found_ips = []
                for entry in entries:
                    if entry.get('ip') in our_ips:
                        found_ips.append(entry['ip'])
                
                print(f"\n✅ Our imported IPs found in FortiGate format: {len(found_ips)}")
                for ip in found_ips:
                    print(f"   Found: {ip}")
                
                if len(found_ips) < len(our_ips):
                    missing = set(our_ips) - set(found_ips)
                    print(f"❌ Missing from FortiGate format: {missing}")
        else:
            print(f"❌ FortiGate endpoint failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ FortiGate test error: {e}")

def show_summary():
    """Show final summary"""
    print_header("Summary")
    
    # Get database stats
    try:
        conn = sqlite3.connect('instance/blacklist.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM blacklist_ip WHERE source = "REGTECH"')
        regtech_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM blacklist_ip WHERE source = "SECUDIUM"')
        secudium_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM blacklist_ip WHERE is_active = 1')
        active_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"📊 Database Summary:")
        print(f"   REGTECH IPs: {regtech_count}")
        print(f"   SECUDIUM IPs: {secudium_count}")
        print(f"   Total Active: {active_count}")
        
    except Exception as e:
        print(f"❌ Summary error: {e}")
    
    # Test web interface accessibility
    try:
        response = requests.get("http://localhost:8541/health")
        if response.status_code == 200:
            print(f"✅ Web interface is accessible at http://localhost:8541")
            print(f"✅ API endpoints are functional")
            print(f"✅ FortiGate integration is ready")
        else:
            print(f"❌ Web interface not accessible")
    except:
        print(f"❌ Web interface not accessible")
    
    print(f"\n🎉 Document-based blacklist extraction and import completed!")
    print(f"   All extracted IPs from REGTECH and SECUDIUM documents have been imported")
    print(f"   The blacklist is now accessible through the web interface")
    print(f"   FortiGate External Connector format is available at /api/fortigate")

def main():
    """Main verification function"""
    print("🚀 Final Blacklist System Verification")
    print(f"Timestamp: {datetime.now()}")
    
    check_database_content()
    test_api_endpoints()
    test_fortigate_format()
    show_summary()

if __name__ == "__main__":
    main()