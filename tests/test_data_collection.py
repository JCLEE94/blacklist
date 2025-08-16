#!/usr/bin/env python3
"""
Test data collection functionality with real credentials
"""

import os
import sys
import time
import requests
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables for testing
os.environ['REGTECH_USERNAME'] = 'nextrade'
os.environ['REGTECH_PASSWORD'] = 'test_password'
os.environ['SECUDIUM_USERNAME'] = 'nextrade'
os.environ['SECUDIUM_PASSWORD'] = 'test_password'


def test_regtech_collection():
    """Test REGTECH data collection with real credentials"""
    print("\n🔍 Testing REGTECH Collection...")
    
    try:
        from src.core.collectors.regtech_collector import RegtechCollector
        from src.core.collectors.unified_collector import CollectionConfig
        
        # Create configuration
        config = CollectionConfig(
            enabled=True,
            username='nextrade',
            password='test_password',
            base_url='https://regtech.fsec.or.kr'
        )
        
        # Initialize collector
        collector = RegtechCollector(config)
        print(f"✅ REGTECH collector initialized")
        
        # Test authentication
        session = collector._create_session()
        if collector._authenticate(session):
            print(f"✅ REGTECH authentication successful")
            
            # Try to collect data
            start_date = datetime.now().strftime('%Y-%m-%d')
            end_date = start_date
            
            result = collector.collect(start_date=start_date, end_date=end_date)
            
            if result.get('success'):
                print(f"✅ REGTECH collection successful: {result.get('total_collected', 0)} IPs collected")
            else:
                print(f"⚠️ REGTECH collection failed: {result.get('error')}")
        else:
            print(f"❌ REGTECH authentication failed")
            
    except Exception as e:
        print(f"❌ REGTECH test error: {e}")
        import traceback
        traceback.print_exc()


def test_secudium_collection():
    """Test SECUDIUM data collection with real credentials"""
    print("\n🔍 Testing SECUDIUM Collection...")
    
    try:
        from src.core.secudium_collector import SecudiumCollector
        from src.core.collectors.unified_collector import CollectionConfig
        
        # Create configuration
        config = CollectionConfig(
            enabled=True,
            username='nextrade',
            password='test_password',
            base_url='https://www.secudium.com'
        )
        
        # Initialize collector
        collector = SecudiumCollector(config)
        print(f"✅ SECUDIUM collector initialized")
        
        # Test authentication
        session = collector._create_session()
        if collector._authenticate(session):
            print(f"✅ SECUDIUM authentication successful")
            
            # Try to collect data
            result = collector.collect()
            
            if result.get('success'):
                print(f"✅ SECUDIUM collection successful: {result.get('total_collected', 0)} IPs collected")
            else:
                print(f"⚠️ SECUDIUM collection failed: {result.get('error')}")
        else:
            print(f"❌ SECUDIUM authentication failed")
            
    except Exception as e:
        print(f"❌ SECUDIUM test error: {e}")
        import traceback
        traceback.print_exc()


def test_api_endpoints():
    """Test API endpoints for data display"""
    print("\n🔍 Testing API Endpoints...")
    
    base_url = "http://localhost:32542"
    
    endpoints = [
        ("/api/health", "Health Check"),
        ("/api/collection/status", "Collection Status"),
        ("/api/blacklist/active", "Active Blacklist"),
        ("/api/fortigate", "FortiGate Format"),
        ("/api/v2/sources/status", "Sources Status"),
    ]
    
    for endpoint, description in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {description}: OK")
            else:
                print(f"⚠️ {description}: Status {response.status_code}")
        except Exception as e:
            print(f"❌ {description}: {e}")


def test_collection_trigger():
    """Test manual collection triggers via API"""
    print("\n🔍 Testing Collection Triggers...")
    
    base_url = "http://localhost:32542/api/collection"
    
    # Enable collection first
    try:
        response = requests.post(
            f"{base_url}/enable",
            json={"clear_data": False},
            timeout=10
        )
        if response.status_code == 200:
            print("✅ Collection enabled")
    except Exception as e:
        print(f"⚠️ Enable collection error: {e}")
    
    # Test REGTECH trigger
    try:
        print("\nTriggering REGTECH collection...")
        response = requests.post(
            f"{base_url}/regtech/trigger",
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✅ REGTECH triggered: {result.get('message')}")
            else:
                print(f"⚠️ REGTECH failed: {result.get('message')}")
        else:
            print(f"❌ REGTECH trigger failed: Status {response.status_code}")
    except Exception as e:
        print(f"❌ REGTECH trigger error: {e}")
    
    # Test SECUDIUM trigger
    try:
        print("\nTriggering SECUDIUM collection...")
        response = requests.post(
            f"{base_url}/secudium/trigger",
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✅ SECUDIUM triggered: {result.get('message')}")
            else:
                print(f"⚠️ SECUDIUM failed: {result.get('message')}")
        else:
            print(f"❌ SECUDIUM trigger failed: Status {response.status_code}")
    except Exception as e:
        print(f"❌ SECUDIUM trigger error: {e}")


def main():
    """Run all data collection tests"""
    print("="*60)
    print("📊 Data Collection & Display Test Suite")
    print("="*60)
    
    # Test API endpoints first
    test_api_endpoints()
    
    # Test direct collection
    test_regtech_collection()
    test_secudium_collection()
    
    # Test via API triggers
    test_collection_trigger()
    
    print("\n" + "="*60)
    print("✅ Test Suite Completed")
    print("="*60)


if __name__ == "__main__":
    main()