#!/usr/bin/env python3
"""
SECUDIUM 토큰 기반 인증 테스트
로그인 후 토큰을 얻어서 API 접근 시도
"""
import requests
from bs4 import BeautifulSoup
import json
import re
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

BASE_URL = "https://secudium.skinfosec.co.kr"
API_HOST = "https://secudium.skinfosec.co.kr/isap-api"
USERNAME = "nextrade"
PASSWORD = "Sprtmxm1@3"

def test_token_authentication():
    """토큰 기반 인증 테스트"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest'
    })
    
    print("1. 로그인 후 토큰 찾기...")
    
    # 메인 페이지 접속
    main_resp = session.get(BASE_URL, verify=False)
    print(f"   메인 페이지: {main_resp.status_code}")
    
    # 로그인
    login_data = {
        'lang': 'ko',
        'is_otp': 'N',
        'is_expire': 'N',
        'login_name': USERNAME,
        'password': PASSWORD,
        'otp_value': ''
    }
    
    login_resp = session.get(f"{BASE_URL}/login", params=login_data, verify=False)
    print(f"   로그인: {login_resp.status_code}")
    
    # 로그인 후 페이지에서 토큰 찾기
    post_login_resp = session.get(BASE_URL, verify=False)
    soup = BeautifulSoup(post_login_resp.text, 'html.parser')
    
    # JavaScript에서 토큰 찾기
    scripts = soup.find_all('script')
    token = None
    
    for script in scripts:
        if script.string:
            # 토큰 패턴 찾기
            token_patterns = [
                r'token["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'window\.token\s*=\s*["\']([^"\']+)["\']',
                r'localStorage\.setItem\(["\']token["\'],\s*["\']([^"\']+)["\']',
                r'sessionStorage\.setItem\(["\']token["\'],\s*["\']([^"\']+)["\']'
            ]
            
            for pattern in token_patterns:
                matches = re.findall(pattern, script.string, re.IGNORECASE)
                if matches:
                    token = matches[0]
                    print(f"   토큰 발견: {token}")
                    break
            
            if token:
                break
    
    if not token:
        print("   JavaScript에서 토큰을 찾지 못함")
        
        # 쿠키에서 토큰 찾기
        for cookie_name, cookie_value in session.cookies.items():
            if 'token' in cookie_name.lower():
                token = cookie_value
                print(f"   쿠키에서 토큰 발견: {cookie_name} = {token}")
                break
    
    print(f"\n2. 토큰으로 API 접근 시도...")
    
    # 토큰이 있으면 헤더에 추가
    if token:
        session.headers.update({
            'Authorization': f'Bearer {token}',
            'Token': token,
            'X-Token': token
        })
        print(f"   토큰 헤더 설정: {token}")
    
    # 토큰 기반 API 테스트
    protected_endpoints = [
        '/secinfo/list',
        '/secinfo/blacklist',
        '/secinfo/data',
        '/report/list',
        '/report/data'
    ]
    
    for endpoint in protected_endpoints:
        url = f"{API_HOST}{endpoint}"
        try:
            resp = session.get(url, verify=False, timeout=10)
            print(f"\n   {endpoint}: {resp.status_code}")
            
            if resp.status_code == 200:
                content_type = resp.headers.get('Content-Type', '')
                print(f"      Content-Type: {content_type}")
                
                if 'json' in content_type:
                    try:
                        data = resp.json()
                        print(f"      JSON: {type(data)}")
                        
                        if isinstance(data, list) and len(data) > 0:
                            print(f"      데이터 개수: {len(data)}")
                            print(f"      첫 번째 항목: {json.dumps(data[0], indent=2, ensure_ascii=False)}")
                            
                            # IP 찾기
                            all_data_str = json.dumps(data)
                            ips = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', all_data_str)
                            real_ips = [ip for ip in ips if not ip.startswith(('127.', '192.168.', '10.', '172.'))]
                            if real_ips:
                                print(f"      ✅ 실제 IP 발견: {len(real_ips)}개!")
                                print(f"      샘플: {real_ips[:10]}")
                                return real_ips
                                
                        elif isinstance(data, dict):
                            print(f"      딕셔너리: {list(data.keys())}")
                            
                            # 데이터 필드에서 리스트 찾기
                            for key, value in data.items():
                                if isinstance(value, list) and len(value) > 0:
                                    print(f"      {key}: {len(value)}개 항목")
                                    print(f"         첫 번째: {value[0]}")
                                    
                                    # IP 찾기
                                    list_str = json.dumps(value)
                                    ips = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', list_str)
                                    real_ips = [ip for ip in ips if not ip.startswith(('127.', '192.168.', '10.', '172.'))]
                                    if real_ips:
                                        print(f"         ✅ 실제 IP 발견: {len(real_ips)}개!")
                                        print(f"         샘플: {real_ips[:10]}")
                                        return real_ips
                        
                    except ValueError:
                        print(f"      JSON 파싱 실패")
                        print(f"      응답: {resp.text[:500]}...")
                else:
                    print(f"      HTML 응답: {len(resp.text)} bytes")
                    if len(resp.text) < 1000:
                        print(f"      내용: {resp.text}")
                        
            elif resp.status_code == 401:
                print(f"      여전히 인증 필요")
            else:
                print(f"      상태: {resp.status_code}")
                
        except Exception as e:
            print(f"   {endpoint} 오류: {e}")
    
    print(f"\n3. 다른 인증 방법 시도...")
    
    # POST로 로그인 시도 (토큰 받기)
    login_endpoints = [
        '/login',
        '/auth/login',
        '/api/login',
        '/isap-api/login',
        '/isap-api/auth'
    ]
    
    for login_endpoint in login_endpoints:
        try:
            # POST 방식으로 로그인
            login_url = f"{BASE_URL}{login_endpoint}"
            
            # JSON 형태로 로그인 시도
            json_login_data = {
                'username': USERNAME,
                'password': PASSWORD,
                'login_name': USERNAME,
                'lang': 'ko',
                'is_otp': 'N'
            }
            
            post_resp = session.post(login_url, json=json_login_data, verify=False)
            print(f"\n   POST {login_endpoint}: {post_resp.status_code}")
            
            if post_resp.status_code == 200:
                try:
                    auth_data = post_resp.json()
                    print(f"      인증 응답: {json.dumps(auth_data, indent=2, ensure_ascii=False)}")
                    
                    # 토큰 찾기
                    if 'token' in auth_data:
                        new_token = auth_data['token']
                        print(f"      ✅ 새 토큰 발견: {new_token}")
                        
                        # 새 토큰으로 API 재시도
                        session.headers.update({
                            'Authorization': f'Bearer {new_token}',
                            'Token': new_token,
                            'X-Token': new_token
                        })
                        
                        # 보호된 엔드포인트 재시도
                        test_resp = session.get(f"{API_HOST}/secinfo/list", verify=False)
                        print(f"      새 토큰으로 테스트: {test_resp.status_code}")
                        
                        if test_resp.status_code == 200:
                            print(f"      ✅ 새 토큰으로 접근 성공!")
                            try:
                                test_data = test_resp.json()
                                print(f"      데이터: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
                            except:
                                print(f"      응답: {test_resp.text}")
                                
                except ValueError:
                    print(f"      JSON 아님: {post_resp.text}")
                    
        except Exception as e:
            print(f"   {login_endpoint} 오류: {e}")
    
    return []

if __name__ == "__main__":
    real_ips = test_token_authentication()
    
    if real_ips:
        print(f"\n🎉 성공! 총 {len(real_ips)}개의 실제 IP 발견!")
        print(f"샘플: {real_ips[:15]}")
    else:
        print(f"\n❌ 실제 SECUDIUM IP 데이터를 찾지 못했습니다.")
        print(f"추가 인증 방법이나 다른 접근 경로가 필요할 수 있습니다.")