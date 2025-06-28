#!/usr/bin/env python3
"""
REGTECH 인증 테스트 (직접 자격증명 사용)
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Set credentials as environment variables
os.environ['REGTECH_USERNAME'] = 'nextrade'
os.environ['REGTECH_PASSWORD'] = 'Sprtmxm1@3'

from src.core.container import get_container
from src.core.regtech_collector import RegtechCollector
from src.utils.advanced_cache import EnhancedSmartCache

def test_regtech_auth():
    print("REGTECH 인증 테스트 시작")
    
    # Initialize collector
    cache = EnhancedSmartCache()
    collector = RegtechCollector('data', cache)
    
    # Collect from REGTECH
    print("\n1. REGTECH 수집 시작...")
    ips = collector.collect_from_web(max_pages=1)
    print(f"   수집된 IP 수: {len(ips)}")
    
    if ips:
        print(f"\n2. 첫 5개 IP:")
        for i, ip_entry in enumerate(ips[:5]):
            print(f"   {i+1}. {ip_entry.ip_address} ({ip_entry.country}) - {ip_entry.reason}")
        
        # Get blacklist manager and save
        container = get_container()
        blacklist_manager = container.resolve('blacklist_manager')
        
        print(f"\n3. 데이터베이스 저장...")
        ips_data = [{
            'ip': ip_entry.ip_address,
            'source': 'REGTECH',
            'threat_type': ip_entry.reason,
            'country': ip_entry.country,
            'confidence': 1.0
        } for ip_entry in ips]
        
        result = blacklist_manager.bulk_import_ips(ips_data, source='REGTECH')
        
        if result.get('success'):
            print(f"   ✅ {result['imported_count']}개 IP 저장 성공!")
        else:
            print(f"   ❌ 저장 실패: {result.get('error')}")
    else:
        print("   ❌ IP 수집 실패")

if __name__ == "__main__":
    test_regtech_auth()