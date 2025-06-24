#!/usr/bin/env python3
"""
SECUDIUM API 직접 테스트
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import requests
import json
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

from src.config.settings import settings

def test_secudium_api():
    """SECUDIUM API 직접 호출 테스트"""
    username = settings.secudium_username
    password = settings.secudium_password
    base_url = settings.secudium_base_url
    
    print(f"=== SECUDIUM API 테스트 ===")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': f"{base_url}/"
    })
    
    # 1. 메인 페이지
    print("\n1. 메인 페이지 접속...")
    main_resp = session.get(f"{base_url}/")
    print(f"Status: {main_resp.status_code}")
    
    # 2. 로그인 (강제 로그인 파라미터 추가)
    print("\n2. 로그인...")
    login_data = {
        'login_name': username,
        'password': password,
        'lang': 'ko',
        'force_login': 'true'  # 강제 로그인 시도
    }
    
    login_resp = session.post(
        f"{base_url}/isap-api/loginProcess",
        data=login_data,
        headers={'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
    )
    
    print(f"Login Status: {login_resp.status_code}")
    if login_resp.text:
        login_result = login_resp.json()
        print(f"Login Response: {json.dumps(login_result, indent=2, ensure_ascii=False)}")
        
        # 토큰 추출
        token = None
        if 'response' in login_result:
            if 'token' in login_result['response']:
                token = login_result['response']['token']
                print(f"Token found: {token[:20]}...")
                session.headers['X-Auth-Token'] = token
    
    # 3. 블랙리스트 데이터 요청 (세션 쿠키 사용)
    print("\n3. 블랙리스트 데이터 요청...")
    print(f"세션 쿠키: {dict(session.cookies)}")
    
    # 파라미터로 요청
    params = {
        'sdate': '',
        'edate': '',
        'dateKey': 'i.reg_date',
        'count': '10',
        'filter': ''
    }
    
    # 세션 쿠키만으로 시도
    blacklist_resp = session.get(
        f"{base_url}/isap-api/secinfo/list/black_ip",
        params=params
    )
    
    print(f"Blacklist Status: {blacklist_resp.status_code}")
    print(f"Response Headers: {dict(blacklist_resp.headers)}")
    
    if blacklist_resp.status_code == 200:
        try:
            data = blacklist_resp.json()
            print(f"Data: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}...")
        except:
            print(f"Response: {blacklist_resp.text[:500]}...")
    else:
        print(f"Error Response: {blacklist_resp.text[:500]}...")
    
    # 4. 토큰을 파라미터로 추가해서 재시도
    if blacklist_resp.status_code == 401:
        print("\n4. 토큰을 파라미터로 추가해서 재시도...")
        
        # JSESSIONID를 X-Auth-Token으로 사용
        jsessionid = session.cookies.get('JSESSIONID')
        if jsessionid:
            params['X-Auth-Token'] = jsessionid
            
            retry_resp = session.get(
                f"{base_url}/isap-api/secinfo/list/black_ip",
                params=params
            )
            
            print(f"Retry Status: {retry_resp.status_code}")
            if retry_resp.status_code == 200:
                try:
                    data = retry_resp.json()
                    print(f"Success! Data: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}...")
                except:
                    print(f"Response: {retry_resp.text[:500]}...")

if __name__ == "__main__":
    test_secudium_api()