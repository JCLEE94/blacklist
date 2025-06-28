#!/usr/bin/env python3
"""
REGTECH 전체 세션 쿠키 확인
"""
import requests
import time
from datetime import datetime

def test_full_session():
    print("🔍 REGTECH 전체 세션 쿠키 추적\n")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    })
    
    print("1️⃣ 메인 페이지 접속")
    main_resp = session.get('https://regtech.fsec.or.kr/main/main')
    print(f"상태: {main_resp.status_code}")
    print("받은 쿠키:")
    for cookie in session.cookies:
        print(f"  - {cookie.name}: {cookie.value[:50]}... (domain: {cookie.domain})")
    
    time.sleep(1)
    
    print("\n2️⃣ 로그인 페이지 접속")
    login_page = session.get('https://regtech.fsec.or.kr/login/loginForm')
    print(f"상태: {login_page.status_code}")
    print("현재 쿠키:")
    for cookie in session.cookies:
        print(f"  - {cookie.name}: {cookie.value[:50]}... (domain: {cookie.domain})")
    
    time.sleep(1)
    
    print("\n3️⃣ 로그인 시도")
    login_data = {
        'login_error': '',
        'txId': '',
        'token': '',
        'memberId': '',
        'smsTimeExcess': 'N',
        'username': 'nextrade',
        'password': 'Sprtmxm1@3'
    }
    
    login_resp = session.post(
        'https://regtech.fsec.or.kr/login/addLogin',
        data=login_data,
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://regtech.fsec.or.kr',
            'Referer': 'https://regtech.fsec.or.kr/login/loginForm',
        },
        allow_redirects=True
    )
    
    print(f"상태: {login_resp.status_code}")
    print(f"최종 URL: {login_resp.url}")
    print("\n🍪 로그인 후 전체 쿠키:")
    for cookie in session.cookies:
        print(f"\n쿠키명: {cookie.name}")
        print(f"  값: {cookie.value[:100]}...")
        print(f"  도메인: {cookie.domain}")
        print(f"  경로: {cookie.path}")
        print(f"  만료: {cookie.expires}")
        print(f"  Secure: {cookie.secure}")
        print(f"  HttpOnly: {cookie.has_nonstandard_attr('HttpOnly')}")
    
    # Bearer 토큰 찾기
    bearer_token = None
    for cookie in session.cookies:
        if cookie.name == 'regtech-va' and cookie.value.startswith('Bearer'):
            bearer_token = cookie.value
            print(f"\n✅ Bearer Token 발견: {bearer_token[:50]}...")
    
    # Advisory 페이지 접속 테스트
    print("\n4️⃣ Advisory 페이지 접속")
    advisory_resp = session.get('https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList')
    print(f"상태: {advisory_resp.status_code}")
    print(f"URL: {advisory_resp.url}")
    
    if 'login' in advisory_resp.url:
        print("❌ 로그인 페이지로 리다이렉트됨")
    else:
        print("✅ 인증 성공")
        
        # 페이지 내용 일부 확인
        if '요주의' in advisory_resp.text:
            print("✅ 요주의 IP 페이지 확인")
    
    print("\n📋 세션 요약:")
    print(f"총 쿠키 수: {len(session.cookies)}")
    print("주요 쿠키:")
    for cookie in session.cookies:
        if cookie.name in ['regtech-va', 'JSESSIONID', 'regtech-front']:
            print(f"  - {cookie.name}: 존재")

if __name__ == "__main__":
    test_full_session()