#!/usr/bin/env python3
"""
테스트: 저장된 인증 정보로 Excel 다운로드
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.regtech_auto_login import get_regtech_auth
import requests
from datetime import datetime, timedelta

def test_auth_flow():
    print("1. 인증 모듈 초기화...")
    auth = get_regtech_auth()
    
    print("2. 토큰 획득...")
    token = auth.get_valid_token()
    
    if not token:
        print("❌ 토큰 획득 실패")
        return
        
    print(f"✅ 토큰 획득: {token[:50]}...")
    
    # 세션 생성
    print("\n3. 세션 생성 및 인증...")
    session = requests.Session()
    session.cookies.set('regtech-va', token, domain='regtech.fsec.or.kr', path='/')
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Authorization': token
    })
    
    # Advisory 페이지 테스트
    print("\n4. Advisory 페이지 접근 테스트...")
    test_resp = session.get('https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList')
    print(f"   상태: {test_resp.status_code}")
    print(f"   URL: {test_resp.url}")
    
    if 'login' in test_resp.url:
        print("   ❌ 로그인 페이지로 리다이렉트됨")
        return
    else:
        print("   ✅ 인증 성공")
    
    # Excel 다운로드 시도
    print("\n5. Excel 다운로드 시도...")
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
    
    # 파일 검사
    if excel_resp.content[:2] == b'PK':
        print("   ✅ Excel 파일 확인!")
        
        # pandas로 읽기
        try:
            import pandas as pd
            import io
            df = pd.read_excel(io.BytesIO(excel_resp.content))
            print(f"   ✅ Excel 로드 성공: {len(df)} rows")
            print(f"   컬럼: {list(df.columns)}")
            
            with open('test_download.xlsx', 'wb') as f:
                f.write(excel_resp.content)
            print("   파일 저장: test_download.xlsx")
            
        except Exception as e:
            print(f"   Excel 읽기 오류: {e}")
    else:
        print("   ❌ Excel이 아님")
        print(f"   내용 시작: {excel_resp.content[:100]}")

if __name__ == "__main__":
    test_auth_flow()