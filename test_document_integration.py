#!/usr/bin/env python3
"""
Test document-based data integration
"""
import sys
sys.path.append('.')

from src.core.blacklist_unified import UnifiedBlacklistManager
from src.core.container import get_container

def test_integration():
    """Test the integration of document-based data"""
    print("=== Document Data Integration Test ===\n")
    
    # Get the blacklist manager
    container = get_container()
    manager = container.resolve('blacklist_manager')
    
    if not manager:
        print("Error: Could not get blacklist manager")
        return
    
    # Test various methods
    print("1. Testing get_active_ips():")
    active_ips = manager.get_active_ips()
    print(f"   Active IPs: {len(active_ips)}")
    if active_ips:
        print(f"   Sample IPs: {active_ips[:5]}")
    
    print("\n2. Testing get_stats():")
    stats = manager.get_stats()
    print(f"   Total IPs: {stats.get('total_ips', 0)}")
    print(f"   Active IPs: {stats.get('active_ips', 0)}")
    print(f"   By source: {stats.get('by_source', {})}")
    
    print("\n3. Testing get_fortigate_format():")
    fortigate = manager.get_fortigate_format()
    print(f"   Entries: {len(fortigate.get('entries', []))}")
    print(f"   Total count: {fortigate.get('total_count', 0)}")
    
    print("\n4. Testing search_ip():")
    test_ip = '211.234.100.45'
    result = manager.search_ip(test_ip)
    print(f"   Search for {test_ip}: {'Found' if result else 'Not found'}")
    if result:
        print(f"   Details: {result}")

if __name__ == "__main__":
    test_integration()