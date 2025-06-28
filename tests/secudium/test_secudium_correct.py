#!/usr/bin/env python3
"""
SECUDIUM 정확한 URL로 테스트
"""
import requests
import json
from datetime import datetime

BASE_URL = "https://secudium.skinfosec.co.kr"
USERNAME = "nextrade"
PASSWORD = "Sprtmxm1@3"

def test_secudium_correct():
    """SECUDIUM 정확한 URL 테스트"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    print("1. SECUDIUM 사이트 접속 테스트...")
    try:
        resp = session.get(BASE_URL, timeout=10, verify=False)
        print(f"   상태 코드: {resp.status_code}")
        print(f"   응답 크기: {len(resp.text)} bytes")
        
        # HTML에서 로그인 폼 찾기
        if 'login' in resp.text.lower():
            print("   로그인 폼 발견")
        
        # API 엔드포인트 찾기
        if 'api' in resp.text:
            print("   API 관련 내용 발견")
            
    except Exception as e:
        print(f"   오류: {e}")
        return
    
    print("\n2. 로그인 시도...")
    login_endpoints = [
        "/login",
        "/api/login",
        "/auth/login",
        "/member/login"
    ]
    
    for endpoint in login_endpoints:
        print(f"\n   엔드포인트: {endpoint}")
        try:
            # JSON 로그인 시도
            login_data = {
                "username": USERNAME,
                "password": PASSWORD
            }
            
            resp = session.post(
                f"{BASE_URL}{endpoint}",
                json=login_data,
                headers={'Content-Type': 'application/json'},
                timeout=10,
                verify=False
            )
            print(f"      JSON 응답: {resp.status_code}")
            
            # Form 로그인 시도
            resp = session.post(
                f"{BASE_URL}{endpoint}",
                data=login_data,
                timeout=10,
                verify=False
            )
            print(f"      Form 응답: {resp.status_code}")
            
        except Exception as e:
            print(f"      오류: {e}")
    
    print("\n3. 블랙리스트 관련 엔드포인트 탐색...")
    endpoints = [
        "/api/blacklist",
        "/api/threats",
        "/api/ips",
        "/blacklist",
        "/threat/list",
        "/data/blacklist"
    ]
    
    for endpoint in endpoints:
        print(f"\n   엔드포인트: {endpoint}")
        try:
            resp = session.get(f"{BASE_URL}{endpoint}", timeout=5, verify=False)
            print(f"      상태: {resp.status_code}")
            if resp.status_code == 200:
                print(f"      타입: {resp.headers.get('Content-Type', 'Unknown')}")
        except Exception as e:
            print(f"      오류: {e}")

if __name__ == "__main__":
    test_secudium_correct()