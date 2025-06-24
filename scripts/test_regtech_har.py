#!/usr/bin/env python3
"""
HAR 분석 결과를 바탕으로 REGTECH 테스트
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import requests
import json
import os
from dotenv import load_dotenv
from src.config.settings import settings

# .env 파일 로드
load_dotenv()

def test_regtech_with_har_params():
    """HAR 파일 분석 결과로 REGTECH 테스트"""
    username = settings.regtech_username
    password = settings.regtech_password
    base_url = settings.regtech_base_url
    
    print(f"=== HAR 기반 REGTECH 테스트 ===")
    print(f"Username: {username}")
    
    session = requests.Session()
    
    # HAR에서 추출한 헤더 사용
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    })
    
    # 1. 메인 페이지 접속
    print("\n1. 메인 페이지 접속...")
    main_resp = session.get(f"{base_url}/main/main")
    print(f"Status: {main_resp.status_code}")
    
    # 2. 로그인 폼 페이지
    print("\n2. 로그인 폼 접속...")
    login_form_resp = session.get(f"{base_url}/login/loginForm")
    print(f"Status: {login_form_resp.status_code}")
    
    # 3. 로그인 시도 (기존 방법)
    print("\n3. 로그인 시도...")
    login_data = {
        'memberId': username,
        'memberPw': password,
        'userType': '1'
    }
    
    login_resp = session.post(
        f"{base_url}/login/addLogin",
        data=login_data,
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': base_url,
            'Referer': f"{base_url}/login/loginForm",
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        }
    )
    
    print(f"Login Status: {login_resp.status_code}")
    print(f"Final URL: {login_resp.url}")
    print(f"Cookies: {dict(session.cookies)}")
    
    # 로그인 실패 시 직접 접근 시도
    if 'error=true' in login_resp.url:
        print("❌ 로그인 실패 - 직접 엔드포인트 접근 시도")
        
        # 4. HAR에서 추출한 정확한 파라미터로 요청
        print("\n4. HAR 파라미터로 직접 접근...")
        har_params = {
            'page': '0',
            'tabSort': 'blacklist', 
            'excelDownload': 'security,blacklist,weakpoint,',
            'cveId': '',
            'ipId': '',
            'estId': '',
            'startDate': '20241201',  # 최근 날짜로 수정
            'endDate': '20250620',
            'findCondition': 'all',
            'findKeyword': '',
            'excelDown': ['security', 'blacklist', 'weakpoint'],
            'size': '100'  # 더 큰 사이즈
        }
        
        # Excel 다운로드 엔드포인트 시도
        excel_resp = session.post(
            f"{base_url}/fcti/securityAdvisory/advisoryListDownloadXlsx",
            data=har_params,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': base_url,
                'Referer': f"{base_url}/fcti/securityAdvisory/advisoryList",
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin'
            }
        )
        
        print(f"Excel Download Status: {excel_resp.status_code}")
        print(f"Content-Type: {excel_resp.headers.get('Content-Type')}")
        print(f"Content-Length: {excel_resp.headers.get('Content-Length')}")
        
        if excel_resp.status_code == 200:
            content_type = excel_resp.headers.get('Content-Type', '')
            if 'excel' in content_type or 'spreadsheet' in content_type:
                print("✅ Excel 파일 다운로드 성공!")
                # 임시 파일로 저장
                with open('/tmp/regtech_test.xlsx', 'wb') as f:
                    f.write(excel_resp.content)
                print("파일 저장: /tmp/regtech_test.xlsx")
            else:
                print(f"Response: {excel_resp.text[:200]}...")
        
        # 5. 일반 리스트 페이지도 시도
        print("\n5. 일반 advisoryList 페이지 접근...")
        list_resp = session.post(
            f"{base_url}/fcti/securityAdvisory/advisoryList",
            data=har_params
        )
        
        print(f"List Status: {list_resp.status_code}")
        if list_resp.status_code == 200:
            # HTML에서 IP 추출 시도
            html_content = list_resp.text
            if 'IP' in html_content or 'blacklist' in html_content:
                print("✅ HTML 데이터 응답 받음")
                print(f"응답 길이: {len(html_content)}")
                
                # IP 패턴 찾기
                import re
                ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
                ips = re.findall(ip_pattern, html_content)
                if ips:
                    print(f"발견된 IP: {len(set(ips))}개")
                    print(f"예시: {list(set(ips))[:5]}")
            else:
                print("❌ 블랙리스트 데이터 없음")

if __name__ == "__main__":
    test_regtech_with_har_params()