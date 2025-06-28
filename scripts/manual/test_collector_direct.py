#!/usr/bin/env python3
"""
수집기 직접 테스트 - 프레임워크 없이 단독 실행
"""
import requests
import os
import sys
from datetime import datetime

def test_regtech_access():
    """REGTECH 사이트 직접 접근 테스트"""
    print("=== REGTECH 직접 접근 테스트 ===")
    
    base_url = "https://regtech.fsec.or.kr"
    username = "nextrade" 
    password = "Sprtmxm1@3"
    
    session = requests.Session()
    
    try:
        # 1. 메인 페이지 접근
        print("1. 메인 페이지 접근...")
        response = session.get(f"{base_url}/main/main", timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Content length: {len(response.text)} bytes")
        
        # 2. 로그인 시도 (가능한 로그인 엔드포인트들)
        login_endpoints = [
            "/login",
            "/auth/login", 
            "/user/login",
            "/member/login"
        ]
        
        for endpoint in login_endpoints:
            try:
                print(f"2. 로그인 시도: {endpoint}")
                login_url = f"{base_url}{endpoint}"
                
                # GET 요청으로 로그인 페이지 확인
                response = session.get(login_url, timeout=5)
                print(f"   GET {endpoint}: {response.status_code}")
                
                if response.status_code == 200:
                    # POST 로그인 시도
                    login_data = {
                        'username': username,
                        'password': password,
                        'userid': username,
                        'userpw': password,
                        'id': username,
                        'pw': password,
                        'email': username,
                        'passwd': password
                    }
                    
                    post_response = session.post(login_url, data=login_data, timeout=5)
                    print(f"   POST {endpoint}: {post_response.status_code}")
                    
                    if post_response.status_code in [200, 302]:
                        print(f"   ✅ 로그인 성공 가능성: {endpoint}")
                        return True
                        
            except Exception as e:
                print(f"   ❌ {endpoint}: {str(e)[:50]}...")
        
        # 3. 직접 IP 목록 페이지 찾기
        print("3. IP 목록 페이지 탐색...")
        ip_endpoints = [
            "/blacklist",
            "/ip/list",
            "/threat/list", 
            "/data/ip",
            "/report/ip",
            "/malicious/ip"
        ]
        
        for endpoint in ip_endpoints:
            try:
                url = f"{base_url}{endpoint}"
                response = session.get(url, timeout=5)
                print(f"   {endpoint}: {response.status_code}")
                if response.status_code == 200:
                    print(f"   ✅ 접근 가능: {endpoint}")
            except Exception as e:
                print(f"   ❌ {endpoint}: {str(e)[:50]}...")
                
    except Exception as e:
        print(f"❌ REGTECH 테스트 실패: {e}")
        return False
    
    return False

def test_secudium_access():
    """SECUDIUM 사이트 직접 접근 테스트"""
    print("\n=== SECUDIUM 직접 접근 테스트 ===")
    
    base_url = "https://www.secudium.com"
    username = "nextrade"
    password = "Sprtmxm1@3"
    
    session = requests.Session()
    
    try:
        # 1. 메인 페이지 접근
        print("1. 메인 페이지 접근...")
        response = session.get(base_url, timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 403:
            print("   403 Forbidden - 인증이 필요한 사이트")
            
        # 2. 로그인 페이지 찾기
        login_endpoints = [
            "/login",
            "/auth",
            "/signin",
            "/member/login"
        ]
        
        for endpoint in login_endpoints:
            try:
                print(f"2. 로그인 시도: {endpoint}")
                login_url = f"{base_url}{endpoint}"
                response = session.get(login_url, timeout=5)
                print(f"   {endpoint}: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"   ✅ 로그인 페이지 발견: {endpoint}")
                    
            except Exception as e:
                print(f"   ❌ {endpoint}: {str(e)[:50]}...")
                
    except Exception as e:
        print(f"❌ SECUDIUM 테스트 실패: {e}")
        return False
        
    return False

def test_network_connectivity():
    """네트워크 연결 테스트"""
    print("\n=== 네트워크 연결 테스트 ===")
    
    test_sites = [
        "https://google.com",
        "https://naver.com", 
        "https://regtech.fsec.or.kr",
        "https://www.secudium.com"
    ]
    
    for site in test_sites:
        try:
            response = requests.get(site, timeout=5)
            print(f"✅ {site}: {response.status_code}")
        except Exception as e:
            print(f"❌ {site}: {str(e)[:50]}...")

if __name__ == "__main__":
    print("🧪 수집기 단독 테스트 시작")
    print(f"실행 시간: {datetime.now()}")
    
    test_network_connectivity()
    regtech_result = test_regtech_access()
    secudium_result = test_secudium_access()
    
    print(f"\n📊 테스트 결과:")
    print(f"  REGTECH: {'✅ 접근 가능' if regtech_result else '❌ 접근 제한'}")
    print(f"  SECUDIUM: {'✅ 접근 가능' if secudium_result else '❌ 접근 제한'}")
    
    if not regtech_result and not secudium_result:
        print("\n⚠️ 두 사이트 모두 접근이 제한되어 있습니다.")
        print("   - 인증 정보가 변경되었거나")
        print("   - 사이트 정책이 변경되었을 가능성이 있습니다.")