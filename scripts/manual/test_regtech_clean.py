#!/usr/bin/env python3
"""
REGTECH 수집기 정리된 버전 테스트
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from src.core.regtech_collector_clean import RegtechCollector
from src.core.models import BlacklistEntry

def test_regtech_collector():
    """정리된 REGTECH 수집기 테스트"""
    print("🧪 정리된 REGTECH 수집기 테스트")
    
    # 수집기 생성
    collector = RegtechCollector(data_dir="data")
    
    # 데이터 수집 (최근 30일, 1페이지만)
    collected_ips = collector.collect_from_web(
        max_pages=1,
        page_size=100,
        start_date='20250601',  # HAR에서 성공했던 날짜 사용
        end_date='20250630'
    )
    
    print(f"🎯 수집 결과: {len(collected_ips)}개 IP")
    
    if collected_ips:
        print("✅ 수집 성공! 샘플 IP들:")
        for i, ip_entry in enumerate(collected_ips[:5]):
            print(f"  {i+1}. {ip_entry.ip} ({ip_entry.country}) - {ip_entry.attack_type}")
        
        if len(collected_ips) > 5:
            print(f"  ... 그리고 {len(collected_ips) - 5}개 더")
        
        # 통계 출력
        stats = collector.stats
        print(f"\n📊 수집 통계:")
        print(f"  - 총 수집: {stats.total_collected}개")
        print(f"  - 중복 제거: {stats.duplicate_count}개")
        print(f"  - 처리 페이지: {stats.pages_processed}개")
        
        return True
    else:
        print("❌ 수집 실패")
        return False

if __name__ == "__main__":
    success = test_regtech_collector()
    if success:
        print("\n🎉 REGTECH 수집기 테스트 성공!")
    else:
        print("\n💥 REGTECH 수집기 테스트 실패")