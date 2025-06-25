#!/usr/bin/env python3
"""
HAR 파일 분석 스크립트
실제 브라우저에서 캡처한 HAR 파일을 분석하여 로그인 및 데이터 수집 과정을 파악합니다.
"""

import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

def analyze_regtech_har():
    """REGTECH HAR 파일 분석"""
    print("\n" + "="*60)
    print("REGTECH HAR 파일 분석")
    print("="*60)
    
    har_path = Path("document/regtech.fesc.or.kr.har")
    if not har_path.exists():
        har_path = Path("document/regtech.fsec.or.kr.har")  # 오타 수정
    
    if not har_path.exists():
        print(f"HAR 파일을 찾을 수 없습니다: {har_path}")
        return
    
    with open(har_path, 'r', encoding='utf-8') as f:
        har_data = json.load(f)
    
    entries = har_data['log']['entries']
    
    # 1. 로그인 관련 요청 찾기
    print("\n1. 로그인 관련 요청:")
    login_requests = []
    for entry in entries:
        request = entry['request']
        url = request['url']
        
        if 'login' in url.lower() or 'addlogin' in url.lower():
            login_requests.append(entry)
            print(f"\n- URL: {url}")
            print(f"  Method: {request['method']}")
            
            if request['method'] == 'POST' and 'postData' in request:
                print(f"  PostData: {request['postData'].get('text', '')[:200]}")
            
            # 응답 상태 확인
            response = entry['response']
            print(f"  Response Status: {response['status']}")
            
            # 리다이렉트 확인
            for header in response['headers']:
                if header['name'].lower() == 'location':
                    print(f"  Redirect to: {header['value']}")
    
    # 2. 블랙리스트 데이터 요청 찾기
    print("\n\n2. 블랙리스트 데이터 요청:")
    data_requests = []
    for entry in entries:
        request = entry['request']
        url = request['url']
        
        if any(keyword in url.lower() for keyword in ['blacklist', 'advisory', 'fcti']):
            data_requests.append(entry)
            print(f"\n- URL: {url}")
            print(f"  Method: {request['method']}")
            
            # POST 데이터 확인
            if request['method'] == 'POST' and 'postData' in request:
                post_text = request['postData'].get('text', '')
                print(f"  PostData: {post_text[:200]}")
                
                # 파라미터 파싱
                if 'application/x-www-form-urlencoded' in request['postData'].get('mimeType', ''):
                    params = parse_qs(post_text)
                    print("  Parsed Parameters:")
                    for key, value in params.items():
                        print(f"    {key}: {value}")
            
            # 쿠키 확인
            cookies = []
            for header in request['headers']:
                if header['name'].lower() == 'cookie':
                    cookies.append(header['value'])
            if cookies:
                print(f"  Cookies: {cookies[0][:100]}...")
    
    # 3. 다운로드 관련 요청 찾기
    print("\n\n3. 다운로드 관련 요청:")
    for entry in entries:
        request = entry['request']
        url = request['url']
        
        if any(keyword in url.lower() for keyword in ['download', 'xlsx', 'export']):
            print(f"\n- URL: {url}")
            print(f"  Method: {request['method']}")

def analyze_secudium_har():
    """SECUDIUM HAR 파일 분석"""
    print("\n\n" + "="*60)
    print("SECUDIUM HAR 파일 분석")
    print("="*60)
    
    har_path = Path("document/secudium.skinfosec.co.kr.har")
    
    if not har_path.exists():
        print(f"HAR 파일을 찾을 수 없습니다: {har_path}")
        return
    
    with open(har_path, 'r', encoding='utf-8') as f:
        har_data = json.load(f)
    
    entries = har_data['log']['entries']
    
    # 1. 로그인 관련 요청 찾기
    print("\n1. 로그인 관련 요청:")
    for entry in entries:
        request = entry['request']
        url = request['url']
        
        if 'login' in url.lower() or 'auth' in url.lower():
            print(f"\n- URL: {url}")
            print(f"  Method: {request['method']}")
            
            if request['method'] == 'POST' and 'postData' in request:
                post_text = request['postData'].get('text', '')
                print(f"  PostData: {post_text[:200]}")
                
                # JSON 데이터인 경우
                if 'application/json' in request['postData'].get('mimeType', ''):
                    try:
                        post_json = json.loads(post_text)
                        print(f"  JSON Data: {json.dumps(post_json, indent=2)}")
                    except:
                        pass
            
            # 응답 확인
            response = entry['response']
            print(f"  Response Status: {response['status']}")
            
            # 응답 내용 확인 (토큰 등)
            if 'content' in response and 'text' in response['content']:
                resp_text = response['content']['text'][:500]
                if 'token' in resp_text.lower():
                    print(f"  Response (token found): {resp_text}")
    
    # 2. API 요청 찾기
    print("\n\n2. API 요청:")
    for entry in entries:
        request = entry['request']
        url = request['url']
        
        if any(keyword in url for keyword in ['api', 'black_ip', 'secinfo']):
            print(f"\n- URL: {url}")
            print(f"  Method: {request['method']}")
            
            # 헤더 확인 (인증 토큰)
            auth_headers = []
            for header in request['headers']:
                if any(auth in header['name'].lower() for auth in ['authorization', 'token', 'auth']):
                    auth_headers.append(f"{header['name']}: {header['value'][:50]}...")
            
            if auth_headers:
                print("  Auth Headers:")
                for h in auth_headers:
                    print(f"    {h}")
            
            # 파라미터 확인
            parsed_url = urlparse(url)
            if parsed_url.query:
                params = parse_qs(parsed_url.query)
                print("  Query Parameters:")
                for key, value in params.items():
                    print(f"    {key}: {value}")

def extract_login_flow():
    """로그인 플로우 추출"""
    print("\n\n" + "="*60)
    print("로그인 플로우 요약")
    print("="*60)
    
    print("""
REGTECH 로그인 플로우:
1. GET /login/loginForm - 로그인 폼 접근
2. POST /login/addLogin - 로그인 시도
   - Parameters: memberId, memberPw, userType=1
3. 성공 시 리다이렉트 또는 JSON 응답
4. GET /fcti/securityAdvisory/advisoryList - 데이터 페이지 접근
5. POST /fcti/securityAdvisory/advisoryList - 데이터 요청
   - Parameters: page, tabSort=blacklist, startDate, endDate, size

SECUDIUM 로그인 플로우:
1. GET /login - 로그인 페이지
2. POST /isap-api/loginProcess - 로그인 API
   - Parameters: lang=ko, is_otp=N, is_expire=Y, login_name, password
3. 응답에서 token 획득
4. GET /secinfo/black_ip - 데이터 페이지 (토큰 필요)
5. API 호출 시 Authorization 헤더에 토큰 포함
""")

def main():
    """메인 함수"""
    print("HAR 파일 분석 도구")
    print("실제 브라우저 트래픽을 분석하여 정확한 API 사용법을 파악합니다.")
    
    analyze_regtech_har()
    analyze_secudium_har()
    extract_login_flow()
    
    print("\n분석 완료!")

if __name__ == "__main__":
    main()