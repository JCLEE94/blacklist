#!/usr/bin/env python3
"""
SECUDIUM API 엔드포인트 찾기
"""
import os
import requests
from datetime import datetime, timedelta

# SECUDIUM 설정
base_url = os.getenv('SECUDIUM_BASE_URL', 'https://secudium.skinfosec.co.kr')
username = os.getenv('SECUDIUM_USERNAME', 'nextrade')
password = os.getenv('SECUDIUM_PASSWORD', 'Sprtmxm1@3')

session = requests.Session()

# 1. 로그인
print("1. 로그인...")
login_data = {
    'lang': 'ko',
    'is_otp': 'N',
    'is_expire': 'Y',
    'login_name': username,
    'password': password,
    'otp_value': ''
}

login_resp = session.post(
    f"{base_url}/isap-api/loginProcess",
    data=login_data,
    headers={
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest'
    },
    timeout=30
)

token = None
if login_resp.status_code == 200:
    data = login_resp.json()
    resp_data = data.get('response', {})
    token = resp_data.get('token')
    print(f"✅ 로그인 성공, 토큰: {token[:30]}...")

if not token:
    print("❌ 로그인 실패")
    exit(1)

# 토큰 설정
session.headers.update({
    'Authorization': f'Bearer {token}',
    'X-Auth-Token': token
})

# 2. 가능한 API 엔드포인트들 시도
print("\n2. API 엔드포인트 탐색...")

endpoints = [
    # API 엔드포인트들
    "/isap-api/secinfo/blackIpList",
    "/isap-api/secinfo/black_ip",
    "/isap-api/secinfo/blacklist",
    "/isap-api/blackip/list",
    "/isap-api/black_ip/list",
    "/api/secinfo/black_ip",
    "/api/blackip/list",
    # 일반 페이지 (HTML)
    "/secinfo/black_ip",
    "/secinfo/blacklist",
    "/secinfo/blackip"
]

end_date = datetime.now()
start_date = end_date - timedelta(days=30)

for endpoint in endpoints:
    print(f"\n시도: {endpoint}")
    print("-" * 40)
    
    try:
        # GET 요청
        params = {
            'page': 1,
            'size': 100,
            'startDate': start_date.strftime('%Y-%m-%d'),
            'endDate': end_date.strftime('%Y-%m-%d')
        }
        
        resp = session.get(
            f"{base_url}{endpoint}",
            params=params,
            headers={
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json, text/javascript, */*; q=0.01'
            },
            timeout=10
        )
        
        print(f"상태: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('Content-Type', 'None')}")
        print(f"응답 길이: {len(resp.text)} bytes")
        
        # 성공적인 응답 확인
        if resp.status_code == 200:
            if 'json' in resp.headers.get('Content-Type', '').lower():
                try:
                    data = resp.json()
                    print(f"✅ JSON 응답!")
                    print(f"키: {list(data.keys()) if isinstance(data, dict) else 'List'}")
                    
                    # 데이터 구조 확인
                    if isinstance(data, dict):
                        for key in ['list', 'content', 'data', 'items', 'response']:
                            if key in data:
                                print(f"'{key}' 키 발견: {len(data[key]) if isinstance(data[key], list) else type(data[key])}")
                                if isinstance(data[key], list) and data[key]:
                                    print(f"첫 번째 항목: {data[key][0]}")
                    elif isinstance(data, list) and data:
                        print(f"리스트 크기: {len(data)}")
                        print(f"첫 번째 항목: {data[0]}")
                        
                except Exception as e:
                    print(f"JSON 파싱 실패: {e}")
            else:
                # HTML 응답에서 데이터 확인
                if 'mal_ip' in resp.text or 'blacklist' in resp.text.lower():
                    print("✅ 관련 키워드 발견!")
                if '<table' in resp.text:
                    print("✅ 테이블 구조 발견!")
                    
    except Exception as e:
        print(f"오류: {e}")

# 3. 브라우저처럼 접근
print("\n\n3. 브라우저 방식으로 black_ip 페이지 접근...")
print("="*60)

# 대시보드 먼저 접근
dash_resp = session.get(
    f"{base_url}/",
    headers={
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Referer': f'{base_url}/login'
    }
)
print(f"대시보드 접근: {dash_resp.status_code}")

# black_ip 페이지 접근
page_resp = session.get(
    f"{base_url}/secinfo/black_ip",
    headers={
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Referer': f'{base_url}/'
    }
)

print(f"black_ip 페이지 상태: {page_resp.status_code}")

if page_resp.status_code == 200:
    # 페이지에서 실제 API 호출 찾기
    import re
    
    # JavaScript에서 API URL 찾기
    api_patterns = [
        r'url\s*:\s*["\']([^"\']+black[^"\']+)["\']',
        r'ajax\s*\(\s*["\']([^"\']+)["\']',
        r'fetch\s*\(\s*["\']([^"\']+)["\']',
        r'\.get\s*\(\s*["\']([^"\']+)["\']',
        r'\.post\s*\(\s*["\']([^"\']+)["\']'
    ]
    
    for pattern in api_patterns:
        matches = re.findall(pattern, page_resp.text)
        if matches:
            print(f"\n발견된 API URL들:")
            for match in set(matches):
                if 'black' in match.lower() or 'ip' in match.lower():
                    print(f"  - {match}")