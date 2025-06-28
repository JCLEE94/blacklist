#!/usr/bin/env python3
"""
SECUDIUM 실제 로그인 테스트
"""
import requests
from bs4 import BeautifulSoup
import json
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

BASE_URL = "https://secudium.skinfosec.co.kr"
USERNAME = "nextrade"
PASSWORD = "Sprtmxm1@3"

def test_secudium_login():
    """SECUDIUM 로그인 테스트"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    })
    
    print("1. 메인 페이지 접속...")
    try:
        resp = session.get(BASE_URL, verify=False)
        print(f"   상태: {resp.status_code}")
        print(f"   쿠키: {dict(session.cookies)}")
        
        # HTML 파싱하여 추가 정보 얻기
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 로그인 관련 스크립트 찾기
        for script in soup.find_all('script'):
            if script.string and 'login' in script.string:
                # 로그인 URL 찾기
                import re
                login_urls = re.findall(r'url\s*:\s*["\']([^"\']+login[^"\']*)["\']', script.string)
                if login_urls:
                    print(f"   로그인 URL 발견: {login_urls}")
        
    except Exception as e:
        print(f"   오류: {e}")
        return
    
    print("\n2. 로그인 시도...")
    
    # Form 데이터 (HTML에서 발견한 필드)
    login_data = {
        'lang': 'ko',
        'is_otp': 'N',
        'is_expire': '',
        'login_name': USERNAME,
        'password': PASSWORD,
        'otp_value': ''
    }
    
    # 가능한 로그인 엔드포인트들
    login_endpoints = [
        "/loginProcess",
        "/login/process",
        "/auth/login",
        "/member/loginProcess",
        "/api/loginProcess"
    ]
    
    for endpoint in login_endpoints:
        print(f"\n   엔드포인트 시도: {endpoint}")
        
        # Ajax 스타일 헤더 추가
        ajax_headers = session.headers.copy()
        ajax_headers.update({
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Origin': BASE_URL,
            'Referer': BASE_URL + '/'
        })
        
        try:
            resp = session.post(
                f"{BASE_URL}{endpoint}",
                data=login_data,
                headers=ajax_headers,
                verify=False,
                allow_redirects=False
            )
            
            print(f"      상태 코드: {resp.status_code}")
            print(f"      헤더: {dict(resp.headers)}")
            
            if resp.text:
                print(f"      응답 길이: {len(resp.text)}")
                if len(resp.text) < 500:
                    print(f"      응답: {resp.text}")
                else:
                    print(f"      응답 시작: {resp.text[:200]}...")
                    
                # JSON 응답 시도
                try:
                    json_resp = resp.json()
                    print(f"      JSON 응답: {json.dumps(json_resp, indent=2, ensure_ascii=False)}")
                except:
                    pass
            
            # 성공 여부 확인
            if resp.status_code in [200, 302]:
                print("      로그인 성공 가능성!")
                
                # 세션 확인
                print(f"      세션 쿠키: {dict(session.cookies)}")
                
                # 로그인 후 페이지 접근 시도
                test_urls = [
                    "/main",
                    "/dashboard",
                    "/blacklist",
                    "/api/blacklist/list"
                ]
                
                for test_url in test_urls:
                    try:
                        test_resp = session.get(f"{BASE_URL}{test_url}", verify=False)
                        print(f"      {test_url}: {test_resp.status_code}")
                        if test_resp.status_code == 200:
                            print(f"        페이지 접근 성공!")
                    except:
                        pass
                        
        except Exception as e:
            print(f"      오류: {e}")

if __name__ == "__main__":
    test_secudium_login()