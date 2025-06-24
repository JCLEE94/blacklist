#!/usr/bin/env python3
"""
직접 수집 기능 테스트
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.regtech_collector import RegtechCollector
from src.core.secudium_collector import SecudiumCollector
from src.utils.cache import CacheManager

def test_collectors():
    """수집기 직접 테스트"""
    print("🧪 수집기 직접 테스트 시작\n")
    
    # 환경변수 설정
    os.environ['REGTECH_USERNAME'] = 'nextrade'
    os.environ['REGTECH_PASSWORD'] = 'Sprtmxm1@3'
    os.environ['SECUDIUM_USERNAME'] = 'nextrade'
    os.environ['SECUDIUM_PASSWORD'] = 'Sprtmxm1@3'
    
    # 캐시 초기화
    cache = CacheManager(redis_url=None)  # In-memory cache
    
    print("1️⃣ REGTECH 수집기 테스트")
    print("-" * 50)
    try:
        regtech = RegtechCollector('data', cache)
        result = regtech.auto_collect()
        print(f"✅ 결과: {result}")
    except Exception as e:
        print(f"❌ 오류: {e}")
    
    print("\n2️⃣ SECUDIUM 수집기 테스트")
    print("-" * 50)
    try:
        secudium = SecudiumCollector('data', cache)
        result = secudium.auto_collect()
        print(f"✅ 결과: {result}")
    except Exception as e:
        print(f"❌ 오류: {e}")
    
    print("\n🏁 테스트 완료")

if __name__ == '__main__':
    test_collectors()