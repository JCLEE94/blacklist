#!/usr/bin/env python3
"""
SECUDIUM 수집 테스트 스크립트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.secudium_collector import SecudiumCollector
from src.core.blacklist_unified import UnifiedBlacklistManager
from src.config.settings import Settings
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_secudium_collection():
    """SECUDIUM 수집 테스트"""
    print("=" * 60)
    print("SECUDIUM Collection Test")
    print("=" * 60)
    
    # SECUDIUM 수집기 생성
    collector = SecudiumCollector(
        data_dir='data',
        cache_backend=None
    )
    
    print(f"Username: {collector.username}")
    print(f"Password: {'***' if collector.password else 'None'}")
    
    # 웹에서 수집 시도
    print("\n웹에서 수집 시작...")
    try:
        entries = collector.collect_from_web()
        print(f"\n✅ 수집 성공: {len(entries)}개의 IP")
        
        # 샘플 출력
        if entries:
            print("\n첫 5개 항목:")
            for i, entry in enumerate(entries[:5]):
                print(f"{i+1}. IP: {entry.ip}")
                print(f"   - Date: {entry.first_seen}")
                print(f"   - Source: {entry.source}")
                print(f"   - Country: {entry.metadata.get('country', 'N/A')}")
                print(f"   - Attack Type: {entry.metadata.get('attack_type', 'N/A')}")
                print(f"   - Description: {entry.description}")
                print()
    except Exception as e:
        print(f"\n❌ 수집 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_secudium_collection()