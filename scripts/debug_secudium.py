#!/usr/bin/env python3
"""
SECUDIUM 로그인 디버깅
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

def debug_secudium_login():
    """SECUDIUM 로그인 응답 확인"""
    username = settings.secudium_username
    password = settings.secudium_password
    base_url = settings.secudium_base_url
    
    print(f"=== SECUDIUM 로그인 디버깅 ===")
    print(f"URL: {base_url}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password) if password else 'None'}")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': f"{base_url}/"
    })
    
    # 메인 페이지 접속
    print("\n1. 메인 페이지 접속...")
    main_resp = session.get(f"{base_url}/")
    print(f"Status: {main_resp.status_code}")
    
    # 로그인 시도
    print("\n2. 로그인 시도...")
    login_data = {
        'login_name': username,
        'password': password,
        'lang': 'ko'
    }
    
    login_resp = session.post(
        f"{base_url}/isap-api/loginProcess",
        data=login_data
    )
    
    print(f"Status: {login_resp.status_code}")
    print(f"Headers: {dict(login_resp.headers)}")
    
    if login_resp.text:
        try:
            response_data = login_resp.json()
            print(f"\n응답 데이터:")
            print(json.dumps(response_data, indent=2, ensure_ascii=False))
            
            # 토큰 찾기
            if 'response' in response_data:
                inner = response_data['response']
                if inner.get('code') == 'already.login':
                    print("\n⚠️ 이미 로그인된 사용자!")
                    
                    # 로그아웃 시도
                    print("\n3. 로그아웃 시도...")
                    logout_resp = session.post(f"{base_url}/isap-api/logoutProcess")
                    print(f"Logout Status: {logout_resp.status_code}")
                    if logout_resp.text:
                        print(f"Logout Response: {logout_resp.text}")
                    
                    # 재로그인
                    print("\n4. 재로그인 시도...")
                    retry_resp = session.post(
                        f"{base_url}/isap-api/loginProcess",
                        data=login_data
                    )
                    print(f"Retry Status: {retry_resp.status_code}")
                    if retry_resp.text:
                        retry_data = retry_resp.json()
                        print(json.dumps(retry_data, indent=2, ensure_ascii=False))
                        
        except Exception as e:
            print(f"JSON 파싱 오류: {e}")
            print(f"응답 텍스트: {login_resp.text[:500]}")
    
    # 쿠키 확인
    print(f"\n쿠키:")
    for cookie in session.cookies:
        print(f"  {cookie.name}: {cookie.value[:50]}...")

if __name__ == "__main__":
    debug_secudium_login()