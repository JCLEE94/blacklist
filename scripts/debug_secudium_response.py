#!/usr/bin/env python3
"""
SECUDIUM 응답 디버깅
"""
import os
import requests
from datetime import datetime, timedelta

# SECUDIUM 설정
base_url = os.getenv('SECUDIUM_BASE_URL', 'https://secudium.skinfosec.co.kr')
username = os.getenv('SECUDIUM_USERNAME', 'nextrade')
password = os.getenv('SECUDIUM_PASSWORD', 'Sprtmxm1@3')

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
})

print("SECUDIUM 응답 디버깅")
print("="*60)

# 1. 로그인
print("1. 로그인 시도...")
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
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': f"{base_url}/login"
    },
    timeout=30
)

print(f"로그인 상태: {login_resp.status_code}")
print(f"Content-Type: {login_resp.headers.get('Content-Type', 'None')}")
print(f"응답 길이: {len(login_resp.text)} bytes")
print(f"응답 처음 500자:\n{login_resp.text[:500]}")

# 2. 블랙리스트 페이지 접근
print("\n2. 블랙리스트 페이지 접근...")

# 날짜 설정
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

# 다양한 방법 시도
methods = [
    {
        "name": "GET with params",
        "method": "GET",
        "url": f"{base_url}/secinfo/black_ip",
        "params": {
            'board_idx': '',
            'view_count': '100',
            'search_keyword': '',
            'page': '1',
            'sort_key': 'REG_DT',
            'sort_type': 'DESC',
            'view_mode': 'card',
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        },
        "data": None
    },
    {
        "name": "POST with form data",
        "method": "POST",
        "url": f"{base_url}/secinfo/black_ip",
        "params": None,
        "data": {
            'board_idx': '',
            'view_count': '100',
            'search_keyword': '',
            'page': '1',
            'sort_key': 'REG_DT',
            'sort_type': 'DESC',
            'view_mode': 'card',
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        }
    },
    {
        "name": "Simple GET",
        "method": "GET",
        "url": f"{base_url}/secinfo/black_ip",
        "params": None,
        "data": None
    }
]

for method_info in methods:
    print(f"\n시도: {method_info['name']}")
    print("-" * 40)
    
    try:
        if method_info['method'] == 'GET':
            resp = session.get(
                method_info['url'],
                params=method_info['params'],
                headers={
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': f"{base_url}/secinfo/black_ip"
                },
                timeout=30
            )
        else:
            resp = session.post(
                method_info['url'],
                data=method_info['data'],
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': f"{base_url}/secinfo/black_ip"
                },
                timeout=30
            )
        
        print(f"상태: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('Content-Type', 'None')}")
        print(f"응답 길이: {len(resp.text)} bytes")
        
        # JSON 파싱 시도
        if 'json' in resp.headers.get('Content-Type', '').lower():
            try:
                data = resp.json()
                print(f"JSON 파싱 성공!")
                print(f"키: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                if isinstance(data, dict) and 'list' in data:
                    print(f"리스트 항목 수: {len(data['list'])}")
                    if data['list']:
                        print(f"첫 번째 항목 키: {list(data['list'][0].keys())}")
                        print(f"첫 번째 항목: {data['list'][0]}")
            except Exception as e:
                print(f"JSON 파싱 실패: {e}")
        else:
            print(f"HTML 응답:")
            print(resp.text[:500])
            
            # HTML에서 데이터 찾기
            if 'mal_ip' in resp.text:
                print("\n✅ 'mal_ip' 키워드 발견됨!")
            if 'blacklist' in resp.text.lower():
                print("✅ 'blacklist' 키워드 발견됨!")
                
    except Exception as e:
        print(f"오류: {e}")

print("\n" + "="*60)
print("디버깅 완료")