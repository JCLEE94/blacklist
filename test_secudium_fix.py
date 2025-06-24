#!/usr/bin/env python3
"""
수정된 SECUDIUM 컬렉터 테스트
HAR 파일 분석 결과를 반영한 로그인 로직 검증
"""

import sys
import os
import logging

# 환경 변수 설정 (CLAUDE.md의 자격증명 사용)
os.environ['SECUDIUM_USERNAME'] = 'nextrade'
os.environ['SECUDIUM_PASSWORD'] = 'Sprtmxm1@3'

# 프로젝트 경로 추가
sys.path.insert(0, '/home/jclee/dev/blacklist')

from src.core.secudium_collector import SecudiumCollector

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_secudium_login():
    """SECUDIUM 로그인 테스트"""
    print("=" * 60)
    print("SECUDIUM 컬렉터 로그인 테스트 (HAR 분석 반영)")
    print("=" * 60)
    
    # 데이터 디렉토리 설정
    data_dir = "/home/jclee/dev/blacklist/data"
    os.makedirs(data_dir, exist_ok=True)
    
    # 컬렉터 초기화
    collector = SecudiumCollector(data_dir=data_dir)
    
    # 로그인 테스트
    print("\n1. 로그인 시도...")
    login_success = collector.login()
    
    if login_success:
        print(f"✅ 로그인 성공! 토큰: {collector.auth_token[:20] if collector.auth_token else 'None'}...")
        
        # 세션 정보 확인
        if hasattr(collector, 'last_session'):
            cookies = dict(collector.last_session.cookies)
            print(f"세션 쿠키: {list(cookies.keys())}")
        
        # 데이터 수집 테스트
        print("\n2. 블랙리스트 데이터 수집 시도...")
        data = collector.collect_blacklist_data(count=10)
        
        if data:
            print(f"✅ 데이터 수집 성공: {len(data)}개 레코드")
            for i, item in enumerate(data[:3]):
                print(f"  [{i+1}] {item.get('ip')} - {item.get('country')} - {item.get('attack_type')}")
        else:
            print("❌ 데이터 수집 실패")
            
    else:
        print("❌ 로그인 실패")
    
    return login_success

def test_auto_collect():
    """자동 수집 전체 프로세스 테스트"""
    print("\n" + "=" * 60)
    print("SECUDIUM 자동 수집 전체 테스트")
    print("=" * 60)
    
    # 데이터 디렉토리 설정
    data_dir = "/home/jclee/dev/blacklist/data"
    
    # 컬렉터 초기화
    collector = SecudiumCollector(data_dir=data_dir)
    
    # 자동 수집 실행
    result = collector.auto_collect()
    
    print(f"수집 결과: {result}")
    
    return result.get('success', False)

if __name__ == "__main__":
    print("SECUDIUM 컬렉터 수정 사항 테스트")
    print("HAR 파일 분석을 바탕으로 한 로그인 로직 개선")
    
    # 테스트 실행
    login_test = test_secudium_login()
    
    if login_test:
        auto_test = test_auto_collect()
        
        if auto_test:
            print("\n🎉 모든 테스트 통과!")
        else:
            print("\n⚠️  로그인은 성공했지만 자동 수집에서 문제 발생")
    else:
        print("\n❌ 로그인 테스트 실패")
    
    print("\n분석 요약:")
    print("- HAR 파일에서 정확한 로그인 파라미터 확인")
    print("- JavaScript 코드에서 응답 처리 로직 분석")
    print("- data.response.error 필드로 성공/실패 판단")
    print("- already.login 오류 처리 개선")