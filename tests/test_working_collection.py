#!/usr/bin/env python3
"""
Working collection test with async handling
"""

import os
import sys
import asyncio
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables
os.environ['REGTECH_USERNAME'] = 'nextrade'
os.environ['REGTECH_PASSWORD'] = 'test_password'


async def test_regtech_async():
    """Test REGTECH collection with async handling"""
    print("\n🔍 Testing REGTECH Collection (Async)...")
    
    try:
        from src.core.collectors.regtech_collector import RegtechCollector
        from src.core.collectors.unified_collector import CollectionConfig
        
        # Create config
        config = CollectionConfig(
            enabled=True,
            settings={
                'username': 'nextrade',
                'password': 'test_password'
            }
        )
        
        # Initialize collector
        collector = RegtechCollector(config)
        print(f"✅ Collector initialized")
        print(f"   Username: {collector.username}")
        print(f"   Base URL: {collector.base_url}")
        
        # Run async collection
        result = await collector.collect()
        
        # Check result
        if result and result.get('success'):
            print(f"✅ Collection successful!")
            print(f"   Total collected: {result.get('total_collected', 0)} IPs")
            
            # Show sample data
            data = result.get('data', [])
            if data:
                print(f"\n   Sample data (first 3):")
                for ip_info in data[:3]:
                    print(f"   - {ip_info.get('ip_address')} | {ip_info.get('category')} | {ip_info.get('source')}")
        else:
            error = result.get('error') if result else 'Unknown error'
            print(f"⚠️ Collection failed: {error}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def test_sync_wrapper():
    """Test sync wrapper for async collectors"""
    print("\n🔍 Testing Sync Wrapper...")
    
    try:
        from src.core.collectors.regtech_collector import RegtechCollector
        from src.core.collectors.unified_collector import CollectionConfig
        from src.utils.async_to_sync import SyncCollectorWrapper
        
        # Create config
        config = CollectionConfig(enabled=True)
        
        # Create async collector
        async_collector = RegtechCollector(config)
        
        # Wrap in sync wrapper
        collector = SyncCollectorWrapper(async_collector)
        print(f"✅ Sync wrapper created")
        
        # Test sync collection
        result = collector.collect()
        
        if result and result.get('success'):
            print(f"✅ Sync collection successful: {result.get('total_collected', 0)} IPs")
        else:
            print(f"⚠️ Sync collection failed: {result.get('error', 'Unknown')}")
            
    except Exception as e:
        print(f"❌ Sync wrapper error: {e}")
        import traceback
        traceback.print_exc()


def test_api_manual_trigger():
    """Test manual API trigger for collection"""
    print("\n🔍 Testing Manual API Trigger...")
    
    import requests
    
    base_url = "http://localhost:32542"
    
    # Check current status
    try:
        response = requests.get(f"{base_url}/api/collection/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Collection enabled: {status.get('collection_enabled')}")
            print(f"   Active IPs: {status.get('stats', {}).get('total_ips', 0)}")
    except Exception as e:
        print(f"⚠️ Status check error: {e}")
    
    # Try to trigger collection
    print("\n   Triggering REGTECH collection...")
    try:
        response = requests.post(
            f"{base_url}/api/collection/regtech/trigger",
            json={
                "start_date": datetime.now().strftime("%Y-%m-%d"),
                "end_date": datetime.now().strftime("%Y-%m-%d")
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✅ Collection triggered successfully")
                print(f"   Message: {result.get('message')}")
                print(f"   IPs collected: {result.get('ips_collected', 0)}")
            else:
                print(f"⚠️ Collection failed: {result.get('message')}")
        else:
            print(f"❌ HTTP {response.status_code}: {response.text[:200]}")
            
    except requests.Timeout:
        print(f"⚠️ Request timed out (collection might still be running)")
    except Exception as e:
        print(f"❌ Trigger error: {e}")


def test_direct_database_insert():
    """Test direct database insertion for verification"""
    print("\n🔍 Testing Direct Database Insert...")
    
    try:
        import sqlite3
        from datetime import datetime
        
        conn = sqlite3.connect('instance/blacklist.db')
        cursor = conn.cursor()
        
        # Insert test data
        test_ips = [
            ('192.168.1.100', 'REGTECH', 'malware', 8, 'Test malware IP'),
            ('10.0.0.50', 'SECUDIUM', 'botnet', 9, 'Test botnet IP'),
            ('172.16.0.25', 'PUBLIC', 'phishing', 7, 'Test phishing IP')
        ]
        
        for ip, source, category, threat, desc in test_ips:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO blacklist_ips 
                    (ip_address, source, category, threat_level, description, added_date, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                ''', (ip, source, category, threat, desc, datetime.now()))
            except Exception as e:
                print(f"   Insert error for {ip}: {e}")
        
        conn.commit()
        
        # Verify insertion
        cursor.execute("SELECT COUNT(*) FROM blacklist_ips")
        total = cursor.fetchone()[0]
        print(f"✅ Test data inserted. Total IPs in database: {total}")
        
        # Show data
        cursor.execute("SELECT ip_address, source, category FROM blacklist_ips LIMIT 5")
        rows = cursor.fetchall()
        if rows:
            print("\n   Current database entries:")
            for ip, source, cat in rows:
                print(f"   - {ip} | {source} | {cat}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")


def verify_ui_display():
    """Verify data appears in UI endpoints"""
    print("\n🔍 Verifying UI Display...")
    
    import requests
    
    base_url = "http://localhost:32542"
    
    # Check active IPs endpoint
    try:
        response = requests.get(f"{base_url}/api/blacklist/active")
        if response.status_code == 200:
            ips = response.text.strip().split('\n')
            if ips and ips[0]:
                print(f"✅ Active IPs endpoint: {len(ips)} IPs")
                print(f"   First 3 IPs: {ips[:3]}")
            else:
                print(f"⚠️ Active IPs endpoint: No data")
    except Exception as e:
        print(f"❌ Active IPs error: {e}")
    
    # Check FortiGate endpoint
    try:
        response = requests.get(f"{base_url}/api/fortigate")
        if response.status_code == 200:
            data = response.text
            if data and len(data) > 10:
                print(f"✅ FortiGate endpoint: Data available ({len(data)} chars)")
            else:
                print(f"⚠️ FortiGate endpoint: No data")
    except Exception as e:
        print(f"❌ FortiGate error: {e}")
    
    # Check enhanced endpoint
    try:
        response = requests.get(f"{base_url}/api/v2/blacklist/enhanced")
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('data'):
                print(f"✅ Enhanced endpoint: {len(data['data'])} entries")
            else:
                print(f"⚠️ Enhanced endpoint: No data")
    except Exception as e:
        print(f"❌ Enhanced endpoint error: {e}")


async def main_async():
    """Main async function"""
    print("="*60)
    print("🚀 Working Collection Test Suite")
    print("="*60)
    
    # Test async collection
    await test_regtech_async()
    
    # Test sync wrapper
    test_sync_wrapper()
    
    # Test API trigger
    test_api_manual_trigger()
    
    # Insert test data
    test_direct_database_insert()
    
    # Verify UI display
    verify_ui_display()
    
    print("\n" + "="*60)
    print("✅ Test Suite Completed")
    print("="*60)


if __name__ == "__main__":
    # Run async main
    asyncio.run(main_async())