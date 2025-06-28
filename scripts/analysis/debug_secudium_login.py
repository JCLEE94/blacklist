#!/usr/bin/env python3
"""
SECUDIUM 로그인 실패 원인 디버깅
"""
import requests
from bs4 import BeautifulSoup
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

BASE_URL = "https://secudium.skinfosec.co.kr"
USERNAME = "nextrade"
PASSWORD = "Sprtmxm1@3"

def debug_login_failure():
    """로그인 실패 원인 분석"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    print("=== SECUDIUM 로그인 실패 원인 분석 ===\n")
    
    # 1. 로그인 페이지 분석
    print("1. 로그인 페이지 폼 분석...")
    login_page = session.get(BASE_URL, verify=False)
    soup = BeautifulSoup(login_page.text, 'html.parser')
    
    # 폼 찾기
    form = soup.find('form')
    if form:
        print(f"   폼 액션: {form.get('action', 'None')}")
        print(f"   폼 메서드: {form.get('method', 'GET')}")
        
        # 모든 입력 필드 분석
        inputs = form.find_all(['input', 'select', 'textarea'])
        print(f"\n   입력 필드:")
        for inp in inputs:
            name = inp.get('name', '')
            input_type = inp.get('type', inp.name)
            value = inp.get('value', '')
            required = inp.get('required', False)
            print(f"      {name}: {input_type} (값: {value}, 필수: {required})")
    
    # 2. GET 로그인 시도
    print(f"\n2. GET 로그인 시도...")
    login_data = {
        'lang': 'ko',
        'is_otp': 'N',
        'is_expire': 'N',
        'login_name': USERNAME,
        'password': PASSWORD,
        'otp_value': ''
    }
    
    get_resp = session.get(f"{BASE_URL}/login", params=login_data, verify=False, allow_redirects=False)
    print(f"   응답 코드: {get_resp.status_code}")
    print(f"   리다이렉트: {get_resp.is_redirect}")
    if get_resp.is_redirect:
        print(f"   리다이렉트 위치: {get_resp.headers.get('Location', 'None')}")
    
    # 응답 헤더 확인
    print(f"\n   응답 헤더:")
    for key, value in get_resp.headers.items():
        if key.lower() in ['set-cookie', 'location', 'content-type']:
            print(f"      {key}: {value}")
    
    # 3. 최종 페이지 내용 확인
    print(f"\n3. 최종 페이지 분석...")
    final_resp = session.get(f"{BASE_URL}/login", params=login_data, verify=False)
    final_soup = BeautifulSoup(final_resp.text, 'html.parser')
    
    # 에러 메시지 찾기
    error_messages = []
    
    # 일반적인 에러 클래스들
    error_classes = ['error', 'alert', 'warning', 'fail', 'message', 'msg']
    for cls in error_classes:
        elements = final_soup.find_all(class_=lambda x: x and cls in x.lower())
        for elem in elements:
            text = elem.get_text(strip=True)
            if text and len(text) > 5:
                error_messages.append(f"{elem.name}.{elem.get('class', [])}: {text}")
    
    # ID로도 찾기
    error_ids = ['error', 'message', 'alert', 'msg']
    for error_id in error_ids:
        elem = final_soup.find(id=lambda x: x and error_id in x.lower())
        if elem:
            text = elem.get_text(strip=True)
            if text and len(text) > 5:
                error_messages.append(f"#{elem.get('id')}: {text}")
    
    # 스크립트에서 alert 찾기
    scripts = final_soup.find_all('script')
    for script in scripts:
        if script.string and 'alert' in script.string:
            import re
            alerts = re.findall(r'alert\s*\(["\']([^"\']+)["\']', script.string)
            error_messages.extend([f"JavaScript Alert: {alert}" for alert in alerts])
    
    if error_messages:
        print("\n   에러 메시지:")
        for msg in error_messages:
            print(f"      {msg}")
    else:
        print("   명시적인 에러 메시지 없음")
    
    # 4. POST 로그인 시도
    print(f"\n4. POST 로그인 시도...")
    
    # 폼 데이터로 POST
    post_data = {
        'lang': 'ko',
        'is_otp': 'N',
        'is_expire': 'N',
        'login_name': USERNAME,
        'password': PASSWORD,
        'otp_value': ''
    }
    
    post_resp = session.post(f"{BASE_URL}/login", data=post_data, verify=False, allow_redirects=False)
    print(f"   POST 응답: {post_resp.status_code}")
    
    # 5. 실제 로그인 프로세스 URL 찾기
    print(f"\n5. JavaScript에서 실제 로그인 프로세스 찾기...")
    
    for script in scripts:
        if script.string:
            # 로그인 관련 URL 패턴
            login_patterns = [
                r'url\s*:\s*["\']([^"\']*login[^"\']*)["\']',
                r'action\s*=\s*["\']([^"\']*login[^"\']*)["\']',
                r'\.post\s*\(["\']([^"\']*login[^"\']*)["\']',
                r'loginProcess["\']?\s*:\s*["\']([^"\']+)["\']'
            ]
            
            for pattern in login_patterns:
                matches = re.findall(pattern, script.string, re.IGNORECASE)
                if matches:
                    print(f"   발견된 로그인 URL:")
                    for match in matches:
                        print(f"      {match}")
    
    # 6. 쿠키 확인
    print(f"\n6. 쿠키 상태:")
    for cookie_name, cookie_value in session.cookies.items():
        print(f"   {cookie_name}: {cookie_value}")
    
    # 7. 실제 인증 확인
    print(f"\n7. 인증 상태 확인...")
    
    # 로그인 후 메인 페이지
    main_resp = session.get(BASE_URL, verify=False)
    main_soup = BeautifulSoup(main_resp.text, 'html.parser')
    
    # 로그인 상태 확인
    if main_soup.title and 'login' in main_soup.title.string.lower():
        print("   ❌ 여전히 로그인 페이지")
    else:
        print(f"   페이지 제목: {main_soup.title.string if main_soup.title else 'None'}")
        
        # 사용자 정보 찾기
        user_elements = main_soup.find_all(text=lambda x: x and USERNAME in x)
        if user_elements:
            print(f"   ✅ 사용자 이름 발견: {len(user_elements)}개 위치")
    
    # 8. API 엔드포인트 직접 테스트
    print(f"\n8. API 엔드포인트 직접 테스트...")
    
    api_endpoints = [
        '/isap-api/loginProcess',
        '/isap-api/login',
        '/isap-api/auth',
        '/api/login',
        '/api/auth'
    ]
    
    for endpoint in api_endpoints:
        try:
            # GET 시도
            get_api = session.get(f"{BASE_URL}{endpoint}", params=login_data, verify=False)
            print(f"\n   GET {endpoint}: {get_api.status_code}")
            
            # POST 시도
            post_api = session.post(f"{BASE_URL}{endpoint}", data=post_data, verify=False)
            print(f"   POST {endpoint}: {post_api.status_code}")
            
            if post_api.status_code == 200:
                print(f"      응답: {post_api.text[:200]}...")
        except:
            pass

if __name__ == "__main__":
    debug_login_failure()