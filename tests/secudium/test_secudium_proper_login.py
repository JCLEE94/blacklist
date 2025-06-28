#!/usr/bin/env python3
"""
SECUDIUM 올바른 로그인 방식 테스트
JavaScript 분석 결과를 바탕으로 구현
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

BASE_URL = "https://secudium.skinfosec.co.kr"
USERNAME = "nextrade"
PASSWORD = "Sprtmxm1@3"

def test_secudium_proper_login():
    """SECUDIUM 올바른 로그인 테스트"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive'
    })
    
    print("1. SECUDIUM 메인 페이지 접속...")
    try:
        resp = session.get(BASE_URL, verify=False)
        print(f"   상태: {resp.status_code}")
        print(f"   쿠키: {dict(session.cookies)}")
        
        if resp.status_code != 200:
            print("   메인 페이지 접속 실패")
            return
            
    except Exception as e:
        print(f"   오류: {e}")
        return
    
    print("\n2. JavaScript 분석 결과를 바탕으로 로그인...")
    
    # JavaScript에서 발견한 정확한 로그인 방식
    login_data = {
        'lang': 'ko',
        'is_otp': 'N',
        'is_expire': 'N',
        'login_name': USERNAME,
        'password': PASSWORD,
        'otp_value': ''
    }
    
    # Ajax 헤더 설정 (JavaScript에서 확인한 방식)
    session.headers.update({
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': BASE_URL,
        'Referer': BASE_URL + '/'
    })
    
    # JavaScript에서 발견한 '/login' 엔드포인트 사용
    login_url = f"{BASE_URL}/login"
    
    print(f"   로그인 URL: {login_url}")
    print(f"   로그인 데이터: {login_data}")
    
    try:
        # POST 요청 (405 방지를 위해 GET도 시도)
        for method in ['GET', 'POST']:
            print(f"\n   {method} 방식 시도...")
            
            if method == 'POST':
                login_resp = session.post(
                    login_url,
                    data=login_data,
                    verify=False,
                    allow_redirects=False
                )
            else:
                # GET으로 파라미터 전달
                login_resp = session.get(
                    login_url,
                    params=login_data,
                    verify=False,
                    allow_redirects=False
                )
            
            print(f"      상태: {login_resp.status_code}")
            print(f"      헤더: {dict(login_resp.headers)}")
            print(f"      쿠키: {dict(session.cookies)}")
            
            if login_resp.text:
                print(f"      응답 길이: {len(login_resp.text)}")
                
                # JSON 응답 체크
                try:
                    json_resp = login_resp.json()
                    print(f"      JSON 응답: {json.dumps(json_resp, indent=2, ensure_ascii=False)}")
                    
                    # 응답 분석
                    if 'success' in json_resp:
                        if json_resp['success']:
                            print("      ✅ 로그인 성공!")
                            return test_authenticated_requests(session)
                    elif 'error' in json_resp:
                        error = json_resp['error']
                        if error == 'already.login':
                            print("      ⚠️ 이미 로그인됨 - 세션 확인")
                            return test_authenticated_requests(session)
                        else:
                            print(f"      ❌ 로그인 오류: {error}")
                    elif 'token' in json_resp:
                        print("      ✅ 토큰 발급 성공!")
                        return test_authenticated_requests(session)
                        
                except ValueError:
                    # HTML 응답일 경우
                    if login_resp.status_code == 200:
                        if len(login_resp.text) < 1000:
                            print(f"      응답: {login_resp.text}")
                        else:
                            print(f"      응답 시작: {login_resp.text[:200]}...")
                            
                        # 성공 여부 판단
                        if any(keyword in login_resp.text.lower() for keyword in ['dashboard', 'main', 'welcome', '환영']):
                            print("      ✅ 로그인 성공 (리다이렉트)!")
                            return test_authenticated_requests(session)
                    elif login_resp.status_code == 302:
                        location = login_resp.headers.get('Location', '')
                        print(f"      리다이렉트: {location}")
                        if location and not any(fail in location.lower() for fail in ['login', 'error', 'fail']):
                            print("      ✅ 로그인 성공 (302 리다이렉트)!")
                            return test_authenticated_requests(session)
            
            # 로그인 후 인증이 필요한 페이지 접근 테스트
            if login_resp.status_code in [200, 302]:
                test_pages = ['/dashboard', '/main', '/home', '/api/user/info']
                for page in test_pages:
                    try:
                        test_resp = session.get(f"{BASE_URL}{page}", verify=False)
                        if test_resp.status_code == 200 and 'login' not in test_resp.text.lower():
                            print(f"      ✅ {page} 접근 성공 - 로그인됨!")
                            return test_authenticated_requests(session)
                    except:
                        continue
    
    except Exception as e:
        print(f"   로그인 요청 오류: {e}")

def test_authenticated_requests(session):
    """로그인 후 인증된 요청 테스트"""
    print("\n3. 인증된 상태에서 데이터 수집 시도...")
    
    # 가능한 API 엔드포인트들
    endpoints = [
        '/api/blacklist',
        '/api/blacklist/list', 
        '/api/threats',
        '/api/ips',
        '/api/scan/list',
        '/api/dashboard',
        '/data/blacklist',
        '/threat/list'
    ]
    
    for endpoint in endpoints:
        print(f"\n   엔드포인트: {endpoint}")
        try:
            resp = session.get(f"{BASE_URL}{endpoint}", verify=False)
            print(f"      상태: {resp.status_code}")
            
            if resp.status_code == 200:
                # Content-Type 확인
                content_type = resp.headers.get('Content-Type', '')
                print(f"      Content-Type: {content_type}")
                
                if 'json' in content_type:
                    try:
                        data = resp.json()
                        print(f"      JSON 데이터: {type(data)}")
                        
                        if isinstance(data, list):
                            print(f"      배열 길이: {len(data)}")
                            if len(data) > 0:
                                print(f"      첫 번째 항목: {data[0]}")
                        elif isinstance(data, dict):
                            print(f"      딕셔너리 키: {list(data.keys())}")
                            if 'data' in data:
                                print(f"      데이터 필드: {type(data['data'])}")
                                if isinstance(data['data'], list):
                                    print(f"      데이터 개수: {len(data['data'])}")
                    except:
                        print(f"      JSON 파싱 실패")
                else:
                    # HTML 응답
                    if 'ip' in resp.text.lower() and len(resp.text) > 100:
                        print(f"      HTML에서 IP 관련 내용 발견 ({len(resp.text)} bytes)")
                        
                        # IP 패턴 찾기
                        import re
                        ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
                        ips = ip_pattern.findall(resp.text)
                        if ips:
                            unique_ips = list(set(ips))[:10]  # 처음 10개만
                            print(f"      발견된 IP 샘플: {unique_ips}")
            
            elif resp.status_code == 401:
                print("      ❌ 인증 실패 - 로그인이 필요함")
            elif resp.status_code == 403:
                print("      ❌ 접근 권한 없음")
            elif resp.status_code == 404:
                print("      ❌ 엔드포인트 없음")
                
        except Exception as e:
            print(f"      요청 오류: {e}")

if __name__ == "__main__":
    test_secudium_proper_login()