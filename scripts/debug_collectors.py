#!/usr/bin/env python3
"""
수집기 디버깅 스크립트
REGTECH와 SECUDIUM 수집기의 인증 및 데이터 수집 문제를 진단합니다.
"""

import os
import sys
import logging
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트 추가
sys.path.append(str(Path(__file__).parent.parent))

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_regtech_collector():
    """REGTECH 수집기 테스트"""
    print("\n" + "="*60)
    print("REGTECH 수집기 테스트")
    print("="*60)
    
    try:
        from src.core.regtech_collector import RegtechCollector
        
        # 환경변수 확인
        username = os.getenv('REGTECH_USERNAME', 'nextrade')
        password = os.getenv('REGTECH_PASSWORD', 'Sprtmxm1@3')
        
        print(f"사용자명: {username}")
        print(f"비밀번호: {'*' * len(password)}")
        
        # 수집기 초기화
        collector = RegtechCollector(data_dir='data')
        
        # 1. 로그인 테스트
        print("\n1. 로그인 테스트 시작...")
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 로그인 수행
        login_success = collector._perform_login(session)
        print(f"로그인 결과: {'성공' if login_success else '실패'}")
        
        if not login_success:
            print("로그인 실패 - 자격증명 확인 필요")
            return
        
        # 2. 데이터 수집 테스트 (1페이지만)
        print("\n2. 데이터 수집 테스트...")
        result = collector.collect_from_web(max_pages=1)
        
        if result.get('success'):
            stats = result.get('stats', {})
            print(f"수집 성공!")
            print(f"- 총 수집: {stats.get('total_collected', 0)}개")
            print(f"- 페이지: {stats.get('pages_processed', 0)}개")
            print(f"- 중복: {stats.get('duplicate_count', 0)}개")
        else:
            print(f"수집 실패: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"REGTECH 테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()

def test_secudium_collector():
    """SECUDIUM 수집기 테스트"""
    print("\n" + "="*60)
    print("SECUDIUM 수집기 테스트")
    print("="*60)
    
    try:
        from src.core.secudium_har_collector import SecudiumHarCollector
        
        # 환경변수 확인
        username = os.getenv('SECUDIUM_USERNAME', 'nextrade')
        password = os.getenv('SECUDIUM_PASSWORD', 'Sprtmxm1@3')
        
        print(f"사용자명: {username}")
        print(f"비밀번호: {'*' * len(password)}")
        
        # 수집기 초기화
        collector = SecudiumHarCollector(data_dir='data')
        
        # 1. 로그인 테스트
        print("\n1. 로그인 테스트 시작...")
        auth_success = collector.authenticate()
        print(f"로그인 결과: {'성공' if auth_success else '실패'}")
        
        if not auth_success:
            print("로그인 실패 - 자격증명 확인 필요")
            return
        
        # 2. 데이터 수집 테스트
        print("\n2. 데이터 수집 테스트...")
        result = collector.auto_collect()
        
        if result.get('success'):
            print(f"수집 성공!")
            print(f"- 총 IP: {result.get('total_ips', 0)}개")
            print(f"- 저장 위치: {result.get('json_file', 'N/A')}")
        else:
            print(f"수집 실패: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"SECUDIUM 테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()

def check_network_connectivity():
    """네트워크 연결 확인"""
    print("\n" + "="*60)
    print("네트워크 연결 확인")
    print("="*60)
    
    urls = [
        ("REGTECH", "https://regtech.fsec.or.kr"),
        ("SECUDIUM", "https://apt.secudium.net")
    ]
    
    for name, url in urls:
        try:
            response = requests.get(url, timeout=10)
            print(f"{name} ({url}): 연결 성공 (HTTP {response.status_code})")
        except Exception as e:
            print(f"{name} ({url}): 연결 실패 - {e}")

def test_direct_api_calls():
    """직접 API 호출 테스트"""
    print("\n" + "="*60)
    print("직접 API 호출 테스트")
    print("="*60)
    
    # REGTECH 직접 테스트
    print("\n1. REGTECH API 직접 호출")
    try:
        session = requests.Session()
        
        # 로그인 시도
        login_data = {
            'memberId': 'nextrade',
            'memberPw': 'Sprtmxm1@3',
            'userType': '1'
        }
        
        response = session.post(
            'https://regtech.fsec.or.kr/login/addLogin',
            data=login_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Mozilla/5.0'
            },
            timeout=30
        )
        
        print(f"응답 상태: {response.status_code}")
        print(f"응답 URL: {response.url}")
        print(f"응답 내용 (처음 200자): {response.text[:200]}")
        
    except Exception as e:
        print(f"REGTECH API 호출 실패: {e}")
    
    # SECUDIUM 직접 테스트
    print("\n2. SECUDIUM API 직접 호출")
    try:
        session = requests.Session()
        
        # 로그인 시도
        login_data = {
            'lang': 'ko',
            'is_otp': 'N',
            'is_expire': 'Y',
            'login_name': 'nextrade',
            'password': 'Sprtmxm1@3',
            'otp_value': ''
        }
        
        response = session.post(
            'https://apt.secudium.net/isap-api/loginProcess',
            data=login_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Mozilla/5.0'
            },
            timeout=30
        )
        
        print(f"응답 상태: {response.status_code}")
        print(f"응답 헤더: {dict(response.headers)}")
        print(f"응답 내용 (처음 200자): {response.text[:200]}")
        
    except Exception as e:
        print(f"SECUDIUM API 호출 실패: {e}")

def main():
    """메인 함수"""
    print("블랙리스트 수집기 디버깅 도구")
    print(f"실행 시간: {datetime.now()}")
    
    # 네트워크 확인
    check_network_connectivity()
    
    # 직접 API 호출 테스트
    test_direct_api_calls()
    
    # 수집기 테스트
    test_regtech_collector()
    test_secudium_collector()
    
    print("\n테스트 완료!")

if __name__ == "__main__":
    main()