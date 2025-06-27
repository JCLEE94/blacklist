#!/usr/bin/env python3
"""
수집기 테스트 스크립트
"""
import sys
import os
sys.path.append('.')

# 환경변수 설정
os.environ['REGTECH_USERNAME'] = 'nextrade'
os.environ['REGTECH_PASSWORD'] = 'Sprtmxm1@3'
os.environ['SECUDIUM_USERNAME'] = 'nextrade' 
os.environ['SECUDIUM_PASSWORD'] = 'Sprtmxm1@3'

from src.core.har_based_regtech_collector import HarBasedRegtechCollector
from src.core.har_based_secudium_collector import HarBasedSecudiumCollector

def test_regtech():
    """REGTECH 수집기 테스트"""
    print("=== REGTECH 수집기 테스트 ===")
    
    try:
        collector = HarBasedRegtechCollector(data_dir="test_data")
        print("✅ REGTECH 수집기 초기화 성공")
        
        # 인증 테스트
        print("🔐 인증 테스트 중...")
        auth_result = collector.authenticate()
        print(f"인증 결과: {auth_result}")
        
        if auth_result:
            print("✅ 인증 성공!")
            return True
        else:
            print("❌ 인증 실패")
            return False
            
    except Exception as e:
        print(f"❌ REGTECH 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_secudium():
    """SECUDIUM 수집기 테스트"""
    print("\n=== SECUDIUM 수집기 테스트 ===")
    
    try:
        collector = HarBasedSecudiumCollector(data_dir="test_data")
        print("✅ SECUDIUM 수집기 초기화 성공")
        
        # 인증 테스트
        print("🔐 인증 테스트 중...")
        auth_result = collector.authenticate()
        print(f"인증 결과: {auth_result}")
        
        if auth_result:
            print("✅ 인증 성공!")
            return True
        else:
            print("❌ 인증 실패")
            return False
            
    except Exception as e:
        print(f"❌ SECUDIUM 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 수집기 테스트 시작")
    
    # 테스트 디렉토리 생성
    os.makedirs("test_data", exist_ok=True)
    
    regtech_ok = test_regtech()
    secudium_ok = test_secudium()
    
    print(f"\n📊 테스트 결과:")
    print(f"  REGTECH: {'✅ 성공' if regtech_ok else '❌ 실패'}")
    print(f"  SECUDIUM: {'✅ 성공' if secudium_ok else '❌ 실패'}")
    
    if regtech_ok and secudium_ok:
        print("\n🎉 모든 수집기가 정상적으로 작동합니다!")
    else:
        print("\n⚠️ 일부 수집기에 문제가 있습니다.")
        
    # 테스트 파일 정리
    import shutil
    if os.path.exists("test_data"):
        shutil.rmtree("test_data")