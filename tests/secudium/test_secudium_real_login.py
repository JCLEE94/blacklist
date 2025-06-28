#!/usr/bin/env python3
"""
SECUDIUM 실제 로그인 및 데이터 수집 테스트
REGTECH처럼 실제 웹사이트 동작 분석
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

def test_secudium_real_login():
    """SECUDIUM 실제 로그인 테스트"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })
    
    print("1. SECUDIUM 메인 페이지 접속...")
    try:
        resp = session.get(BASE_URL, verify=False)
        print(f"   상태: {resp.status_code}")
        print(f"   쿠키: {dict(session.cookies)}")
        
        if resp.status_code == 200:
            # HTML 파싱하여 로그인 폼 정보 추출
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 로그인 폼 찾기
            form = soup.find('form')
            if form:
                action = form.get('action', '')
                print(f"   폼 액션: {action}")
                
                # 모든 input 필드 찾기
                inputs = form.find_all('input')
                form_data = {}
                for inp in inputs:
                    name = inp.get('name')
                    value = inp.get('value', '')
                    input_type = inp.get('type', 'text')
                    print(f"   Input: {name} = {value} (type: {input_type})")
                    
                    if name:
                        form_data[name] = value
                
                # 로그인 데이터 설정
                form_data['login_name'] = USERNAME
                form_data['password'] = PASSWORD
                form_data['is_otp'] = 'N'  # OTP 사용 안함
                form_data['otp_value'] = ''
                
                print(f"\n   로그인 데이터: {form_data}")
        
    except Exception as e:
        print(f"   오류: {e}")
        return
    
    print("\n2. 로그인 시도...")
    try:
        # JavaScript에서 확인한 로그인 처리 방식 시도
        login_endpoints = [
            "/loginProcess",
            "/login",
            "/auth/login",
            ""  # 현재 페이지에 POST
        ]
        
        for endpoint in login_endpoints:
            login_url = f"{BASE_URL}{endpoint}" if endpoint else BASE_URL
            print(f"\n   URL: {login_url}")
            
            # Ajax 스타일 헤더
            session.headers.update({
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Origin': BASE_URL,
                'Referer': BASE_URL + '/'
            })
            
            # 로그인 요청
            login_resp = session.post(
                login_url,
                data=form_data,
                verify=False,
                allow_redirects=True
            )
            
            print(f"      상태: {login_resp.status_code}")
            print(f"      쿠키: {dict(session.cookies)}")
            print(f"      헤더: {dict(login_resp.headers)}")
            
            if login_resp.text:
                print(f"      응답 길이: {len(login_resp.text)}")
                
                # JSON 응답 체크
                try:
                    json_resp = login_resp.json()
                    print(f"      JSON: {json.dumps(json_resp, indent=2, ensure_ascii=False)}")
                    
                    # 성공/실패 체크
                    if 'success' in json_resp:
                        if json_resp['success']:
                            print("      ✅ 로그인 성공!")
                            return test_data_collection(session)
                        else:
                            print(f"      ❌ 로그인 실패: {json_resp}")
                except:
                    # HTML 응답일 경우
                    if len(login_resp.text) < 1000:
                        print(f"      응답: {login_resp.text}")
                    else:
                        print(f"      응답 시작: {login_resp.text[:300]}...")
                        
                        # 로그인 성공 여부를 HTML에서 판단
                        if 'dashboard' in login_resp.text.lower() or 'main' in login_resp.text.lower():
                            print("      ✅ 로그인 성공 (HTML 리다이렉트)!")
                            return test_data_collection(session)
            
            # 로그인 후 페이지 확인
            if login_resp.status_code in [200, 302]:
                test_urls = ["/dashboard", "/main", "/blacklist", "/home"]
                for test_url in test_urls:
                    try:
                        test_resp = session.get(f"{BASE_URL}{test_url}", verify=False)
                        if test_resp.status_code == 200:
                            print(f"      {test_url}: 접근 성공 - 로그인 성공!")
                            return test_data_collection(session)
                    except:
                        continue
        
    except Exception as e:
        print(f"   로그인 오류: {e}")

def test_data_collection(session):
    """로그인 후 데이터 수집 테스트"""
    print("\n3. 데이터 수집 시도...")
    
    # 가능한 데이터 엔드포인트들
    data_endpoints = [
        "/api/blacklist",
        "/api/blacklist/list",
        "/api/ips",
        "/api/threats",
        "/data/blacklist",
        "/blacklist/export",
        "/threat/list",
        "/security/blacklist"
    ]
    
    for endpoint in data_endpoints:
        print(f"\n   엔드포인트: {endpoint}")
        try:
            resp = session.get(f"{BASE_URL}{endpoint}", verify=False)
            print(f"      상태: {resp.status_code}")
            
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    print(f"      JSON 데이터 타입: {type(data)}")
                    if isinstance(data, list) and len(data) > 0:
                        print(f"      IP 데이터 개수: {len(data)}")
                        print(f"      첫 번째 항목: {data[0]}")
                    elif isinstance(data, dict):
                        print(f"      응답 키: {list(data.keys())}")
                        if 'data' in data:
                            print(f"      데이터 개수: {len(data['data'])}")
                except:
                    if 'ip' in resp.text.lower() and len(resp.text) > 100:
                        print(f"      IP 관련 HTML 데이터 발견 ({len(resp.text)} bytes)")
                        
        except Exception as e:
            print(f"      오류: {e}")

if __name__ == "__main__":
    test_secudium_real_login()