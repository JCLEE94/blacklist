#!/usr/bin/env python3
"""
REGTECH 완전한 인증 및 Excel 다운로드 테스트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
import time
from datetime import datetime, timedelta
import io

def test_full_auth():
    print("🔍 REGTECH 완전한 인증 테스트\n")
    
    # 세션 생성
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    })
    
    # 1. 메인 페이지 접속
    print("1️⃣ 메인 페이지 접속")
    main_resp = session.get('https://regtech.fsec.or.kr/main/main')
    print(f"   상태: {main_resp.status_code}")
    time.sleep(1)
    
    # 2. 로그인 페이지
    print("\n2️⃣ 로그인 페이지 접속")
    login_page = session.get('https://regtech.fsec.or.kr/login/loginForm')
    print(f"   상태: {login_page.status_code}")
    time.sleep(1)
    
    # 3. 로그인
    print("\n3️⃣ 로그인 수행")
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
    
    print(f"   상태: {login_resp.status_code}")
    print(f"   최종 URL: {login_resp.url}")
    
    # 현재 쿠키 확인
    print("\n🍪 현재 쿠키:")
    bearer_token = None
    for cookie in session.cookies:
        print(f"   - {cookie.name}: {'Bearer...' if cookie.value.startswith('Bearer') else 'Session'}")
        if cookie.name == 'regtech-va' and cookie.value.startswith('Bearer'):
            bearer_token = cookie.value
    
    if not bearer_token:
        print("❌ Bearer 토큰을 찾을 수 없음")
        return
    
    # Authorization 헤더 설정
    session.headers['Authorization'] = bearer_token
    
    # 4. Advisory 페이지 테스트
    print("\n4️⃣ Advisory 페이지 접근")
    advisory_resp = session.get('https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList')
    print(f"   상태: {advisory_resp.status_code}")
    print(f"   URL: {advisory_resp.url}")
    
    if 'login' in advisory_resp.url:
        print("   ❌ 로그인 페이지로 리다이렉트됨")
        return
    
    print("   ✅ 인증 성공")
    
    # 5. Excel 다운로드
    print("\n5️⃣ Excel 다운로드 시도")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    excel_data = {
        'page': '0',
        'tabSort': 'blacklist',
        'excelDownload': 'blacklist,',
        'cveId': '',
        'ipId': '',
        'estId': '',
        'startDate': start_date.strftime('%Y%m%d'),
        'endDate': end_date.strftime('%Y%m%d'),
        'findCondition': 'all',
        'findKeyword': '',
        'excelDown': 'blacklist',
        'size': '10'
    }
    
    excel_resp = session.post(
        'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryListDownloadXlsx',
        data=excel_data,
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://regtech.fsec.or.kr',
            'Referer': 'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList'
        }
    )
    
    print(f"   상태: {excel_resp.status_code}")
    print(f"   Content-Type: {excel_resp.headers.get('Content-Type', 'unknown')}")
    print(f"   크기: {len(excel_resp.content)} bytes")
    
    # 응답 헤더 전체 확인
    print("\n📋 응답 헤더:")
    for k, v in excel_resp.headers.items():
        print(f"   {k}: {v}")
    
    # 파일 검사
    if excel_resp.content[:2] == b'PK':
        print("\n✅ Excel 파일 확인!")
        
        # pandas로 읽기
        try:
            import pandas as pd
            df = pd.read_excel(io.BytesIO(excel_resp.content))
            print(f"✅ Excel 로드 성공: {len(df)} rows")
            print(f"컬럼: {list(df.columns)}")
            
            # 처음 5개 IP 출력
            if 'IP' in df.columns:
                print("\n첫 5개 IP:")
                for idx, ip in enumerate(df['IP'].head(5)):
                    print(f"   {idx+1}. {ip}")
            
            with open('test_download.xlsx', 'wb') as f:
                f.write(excel_resp.content)
            print("\n파일 저장: test_download.xlsx")
            
        except Exception as e:
            print(f"Excel 읽기 오류: {e}")
    else:
        print("\n❌ Excel이 아님")
        print(f"내용 시작: {excel_resp.content[:200]}")
        
        # HTML인 경우 파싱
        if b'<' in excel_resp.content[:10]:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(excel_resp.content, 'html.parser')
            title = soup.find('title')
            if title:
                print(f"페이지 제목: {title.text}")

if __name__ == "__main__":
    test_full_auth()