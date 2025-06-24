#!/usr/bin/env python3
"""
HAR 파일에서 인증 정보 분석
"""
import json
from pathlib import Path

def analyze_har_file(har_path):
    """HAR 파일 분석"""
    with open(har_path, 'r', encoding='utf-8') as f:
        har_data = json.load(f)
    
    print(f"\n=== Analyzing {har_path.name} ===")
    
    # 모든 요청 분석
    entries = har_data['log']['entries']
    
    # 로그인 관련 요청 찾기
    login_requests = []
    cookie_info = []
    
    for entry in entries:
        request = entry['request']
        url = request['url']
        
        # 로그인 관련 URL
        if any(keyword in url.lower() for keyword in ['login', 'auth', 'session']):
            login_requests.append({
                'url': url,
                'method': request['method'],
                'headers': {h['name']: h['value'] for h in request['headers']},
                'cookies': request.get('cookies', []),
                'postData': request.get('postData', {})
            })
        
        # 쿠키 정보 수집
        for cookie in request.get('cookies', []):
            cookie_info.append(cookie)
        
        # 응답에서 Set-Cookie 헤더 확인
        if 'response' in entry:
            response = entry['response']
            for header in response.get('headers', []):
                if header['name'].lower() == 'set-cookie':
                    print(f"\nSet-Cookie found in response to: {url}")
                    print(f"  Cookie: {header['value']}")
    
    # 로그인 요청 출력
    print("\n--- Login Related Requests ---")
    for req in login_requests:
        print(f"\nURL: {req['url']}")
        print(f"Method: {req['method']}")
        if req.get('postData'):
            print(f"Post Data: {req['postData']}")
        if req['cookies']:
            print(f"Cookies sent: {[c['name'] for c in req['cookies']]}")
    
    # 쿠키 정보 출력
    print("\n--- Cookie Information ---")
    unique_cookies = {}
    for cookie in cookie_info:
        name = cookie.get('name', 'unknown')
        if name not in unique_cookies:
            unique_cookies[name] = cookie
    
    for name, cookie in unique_cookies.items():
        print(f"  {name}: {cookie.get('value', '')[:50]}...")
    
    # 실제 데이터 요청 찾기
    print("\n--- Data Requests ---")
    data_requests = []
    for entry in entries:
        request = entry['request']
        url = request['url']
        
        if any(keyword in url.lower() for keyword in ['list', 'data', 'json', 'api', 'black', 'advisory']):
            if 'login' not in url.lower():
                data_requests.append({
                    'url': url,
                    'method': request['method'],
                    'status': entry['response']['status']
                })
    
    for req in data_requests[:10]:  # 처음 10개만
        print(f"  {req['method']} {req['url']} -> {req['status']}")

# 분석 실행
regtech_har = Path("/home/jclee/dev/blacklist/document/regtech/regtech.fsec.or.kr.har")
secudium_har = Path("/home/jclee/dev/blacklist/document/secudium/secudium.skinfosec.co.kr.har")

if regtech_har.exists():
    analyze_har_file(regtech_har)

if secudium_har.exists():
    analyze_har_file(secudium_har)