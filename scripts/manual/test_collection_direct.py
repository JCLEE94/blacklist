#!/usr/bin/env python3
"""
직접 REGTECH 수집을 테스트하고 데이터베이스에 저장
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.core.container import get_container
from src.core.regtech_collector import RegtechCollector
from src.core.blacklist_unified import UnifiedBlacklistManager
from src.utils.advanced_cache import EnhancedSmartCache

def test_direct_collection():
    print("REGTECH 직접 수집 테스트 시작")
    
    # Initialize components
    cache = EnhancedSmartCache()
    collector = RegtechCollector('data', cache)
    
    # Get blacklist manager from container
    container = get_container()
    blacklist_manager = container.resolve('blacklist_manager')
    
    print(f"Blacklist manager type: {type(blacklist_manager)}")
    print(f"Blacklist manager methods: {[m for m in dir(blacklist_manager) if not m.startswith('_') and callable(getattr(blacklist_manager, m))]}")
    
    # Collect from REGTECH
    print("\n1. REGTECH 수집 시작...")
    ips = collector.collect_from_web(max_pages=1)  # Test with 1 page only
    print(f"   수집된 IP 수: {len(ips)}")
    
    if ips:
        print(f"\n2. 샘플 IP:")
        for i, ip_entry in enumerate(ips[:5]):
            print(f"   {i+1}. {ip_entry.ip_address} ({ip_entry.country}) - {ip_entry.reason}")
        
        # Save to database using bulk_import_ips
        print(f"\n3. 데이터베이스 저장 시도...")
        
        # Prepare data for bulk import
        ips_data = []
        for ip_entry in ips:
            ips_data.append({
                'ip': ip_entry.ip_address,
                'source': 'REGTECH',
                'threat_type': ip_entry.reason,
                'country': ip_entry.country,
                'confidence': 1.0
            })
        
        # Bulk import
        result = blacklist_manager.bulk_import_ips(ips_data, source='REGTECH')
        
        if result.get('success'):
            print(f"   ✅ 성공: {result['imported_count']}개 IP 저장됨")
            print(f"   - 건너뛴 수: {result.get('skipped_count', 0)}")
            print(f"   - 오류 수: {result.get('error_count', 0)}")
            print(f"   - 소요 시간: {result.get('duration', 0):.2f}초")
        else:
            print(f"   ❌ 실패: {result.get('error')}")
        
        # Verify by searching for one of the IPs
        if ips:
            test_ip = ips[0].ip_address
            print(f"\n4. 저장 확인 - IP 검색: {test_ip}")
            search_result = blacklist_manager.search_ip(test_ip)
            if search_result.get('found'):
                print(f"   ✅ IP가 데이터베이스에 존재합니다")
                print(f"   - Sources: {search_result.get('sources', [])}")
            else:
                print(f"   ❌ IP를 찾을 수 없습니다")

if __name__ == "__main__":
    test_direct_collection()