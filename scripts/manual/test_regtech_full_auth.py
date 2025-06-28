#!/usr/bin/env python3
"""
REGTECH 완전한 인증 흐름 테스트
로그인 → Bearer Token 획득 → Excel 다운로드
"""
import requests
from datetime import datetime, timedelta
import pandas as pd
import time

def full_auth_and_download():
    """완전한 인증 후 Excel 다운로드"""
    print("🔐 REGTECH 완전한 인증 흐름 테스트\n")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    })
    
    try:
        # 1. 메인 페이지 접속 (세션 초기화)
        print("1. 메인 페이지 접속...")
        main_resp = session.get('https://regtech.fsec.or.kr/main/main', timeout=30)
        print(f"   상태: {main_resp.status_code}")
        time.sleep(1)
        
        # 2. 로그인 페이지 접속
        print("\n2. 로그인 페이지 접속...")
        login_page = session.get('https://regtech.fsec.or.kr/login/loginForm', timeout=30)
        print(f"   상태: {login_page.status_code}")
        time.sleep(1)
        
        # 3. 로그인 수행
        print("\n3. 로그인 시도...")
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
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            },
            allow_redirects=True,  # 리다이렉트 자동 따라가기
            timeout=30
        )
        
        print(f"   최종 URL: {login_resp.url}")
        print(f"   상태: {login_resp.status_code}")
        
        # Bearer Token 확인
        bearer_token = None
        for cookie in session.cookies:
            if cookie.name == 'regtech-va' and cookie.value.startswith('Bearer'):
                bearer_token = cookie.value
                print(f"   ✅ Bearer Token 획득: {bearer_token[:50]}...")
                break
        
        if not bearer_token:
            print("   ❌ Bearer Token을 찾을 수 없음")
            return False
        
        # 4. Advisory 페이지 접속 (로그인 확인)
        print("\n4. Advisory 페이지 접속...")
        time.sleep(1)
        advisory_resp = session.get(
            'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList',
            timeout=30
        )
        print(f"   상태: {advisory_resp.status_code}")
        print(f"   URL: {advisory_resp.url}")
        
        if 'login' in advisory_resp.url:
            print("   ❌ 로그인 페이지로 리다이렉트됨")
            return False
        
        # 5. Excel 다운로드
        print("\n5. Excel 다운로드 시도...")
        time.sleep(1)
        
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
        
        print(f"   날짜 범위: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        
        excel_resp = session.post(
            'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryListDownloadXlsx',
            data=excel_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://regtech.fsec.or.kr',
                'Referer': 'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin'
            },
            timeout=60
        )
        
        print(f"   상태: {excel_resp.status_code}")
        print(f"   Content-Type: {excel_resp.headers.get('Content-Type', 'unknown')}")
        print(f"   Content-Length: {excel_resp.headers.get('Content-Length', 'unknown')}")
        
        if excel_resp.status_code == 200:
            # 파일 저장
            filename = 'regtech_full_auth_test.xlsx'
            with open(filename, 'wb') as f:
                f.write(excel_resp.content)
            
            import os
            file_size = os.path.getsize(filename)
            print(f"   파일 크기: {file_size:,} bytes")
            
            # 내용 확인
            with open(filename, 'rb') as f:
                header = f.read(10)
                
            if header.startswith(b'PK'):  # Excel 파일 시그니처
                print("   ✅ Excel 파일 형식 확인")
                
                try:
                    df = pd.read_excel(filename)
                    print(f"\n📊 Excel 데이터 로드 성공!")
                    print(f"   행 수: {len(df)}")
                    print(f"   열: {list(df.columns)}")
                    
                    if len(df) > 0:
                        print(f"\n✅ 성공! {len(df)}개의 IP 수집")
                        print("\n샘플 데이터:")
                        print(df.head())
                        
                        print(f"\n🎉 Bearer Token: {bearer_token}")
                        return True
                        
                except Exception as e:
                    print(f"   Excel 읽기 오류: {e}")
            else:
                print("   ❌ Excel 파일이 아님 (HTML일 가능성)")
                
                # HTML 내용 확인
                with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(500)
                    if 'login' in content.lower():
                        print("   로그인 페이지를 받음")
                    else:
                        print(f"   내용: {content[:200]}...")
        
        return False
        
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = full_auth_and_download()
    if not success:
        print("\n💥 전체 흐름 실패")
        print("\n디버깅 제안:")
        print("1. 브라우저에서 수동 로그인 테스트")
        print("2. 비밀번호 확인 (Sprtmxm1@3)")
        print("3. 계정 상태 확인")
        print("4. PowerShell 스크립트로 다시 시도")