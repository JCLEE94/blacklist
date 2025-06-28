#!/usr/bin/env python3
"""
REGTECH 인증 상태 디버깅
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def debug_regtech_auth():
    """REGTECH 인증 상태 확인"""
    print("🔍 REGTECH 인증 디버깅\n")
    
    # Bearer Token (from PowerShell script)
    bearer_token = "BearereyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJuZXh0cmFkZSIsIm9yZ2FubmFtZSI6IuuEpeyKpO2KuOugiOydtOuTnCIsImlkIjoibmV4dHJhZGUiLCJleHAiOjE3NTExMTkyNzYsInVzZXJuYW1lIjoi7J6l7ZmN7KSAIn0.YwZHoHZCVqDnaryluB0h5_ituxYcaRz4voT7GRfgrNrP86W8TfvBuJbHMON4tJa4AQmNP-XhC_PuAVPQTjJADA"
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    })
    
    # Test 1: Bearer Token in cookie
    print("1. Bearer Token 쿠키 테스트")
    session.cookies.set('regtech-va', bearer_token, domain='regtech.fsec.or.kr', path='/')
    
    # 날짜 설정
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    form_data = {
        'page': '0',
        'tabSort': 'blacklist',
        'excelDownload': '',
        'cveId': '',
        'ipId': '',
        'estId': '',
        'startDate': start_date.strftime('%Y%m%d'),
        'endDate': end_date.strftime('%Y%m%d'),
        'findCondition': 'all',
        'findKeyword': '',
        'size': '10'
    }
    
    response = session.post(
        'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList',
        data=form_data,
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList'
        },
        timeout=30,
        allow_redirects=False  # 리다이렉트 확인
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Redirected: {'Location' in response.headers}")
    if 'Location' in response.headers:
        print(f"Redirect to: {response.headers['Location']}")
    
    # HTML 분석
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 로그인 페이지 체크
        if 'login' in response.url or soup.find('form', {'id': 'loginForm'}):
            print("❌ 로그인 페이지로 리다이렉트됨 - 인증 실패")
            
            # 일반 로그인 시도
            print("\n2. 일반 로그인 방식 시도")
            return try_normal_login()
        else:
            print("✅ Advisory 페이지 접속 성공")
            
            # 총 건수 확인
            import re
            total_pattern = r'총\s*(\d+)\s*건'
            matches = re.findall(total_pattern, response.text)
            if matches:
                print(f"총 데이터: {matches[0]}건")
            
            # 테이블 확인
            tables = soup.find_all('table')
            for table in tables:
                caption = table.find('caption')
                if caption and '요주의 IP' in caption.text:
                    tbody = table.find('tbody')
                    if tbody:
                        rows = tbody.find_all('tr')
                        print(f"요주의 IP 테이블: {len(rows)}개 행")
                        if rows:
                            # 첫 번째 행 샘플
                            cells = rows[0].find_all('td')
                            if len(cells) >= 6:
                                ip = cells[0].get_text(strip=True)
                                country = cells[1].get_text(strip=True)
                                print(f"첫 번째 IP: {ip} ({country})")
                                return True
            
            # 응답 저장
            with open('regtech_auth_response.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("💾 응답이 regtech_auth_response.html로 저장됨")
    
    return False

def try_normal_login():
    """일반 로그인 방식"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    })
    
    try:
        # 메인 페이지
        main_resp = session.get('https://regtech.fsec.or.kr/main/main', timeout=30)
        print(f"메인 페이지: {main_resp.status_code}")
        
        # 로그인 페이지
        login_page = session.get('https://regtech.fsec.or.kr/login/loginForm', timeout=30)
        print(f"로그인 페이지: {login_page.status_code}")
        
        # 로그인
        login_data = {
            'memberId': 'nextrade',
            'memberPw': 'Sprtmxm1@3'
        }
        
        login_resp = session.post(
            'https://regtech.fsec.or.kr/login/addLogin',
            data=login_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': 'https://regtech.fsec.or.kr/login/loginForm'
            },
            timeout=30
        )
        
        print(f"로그인 응답: {login_resp.status_code}")
        if login_resp.status_code == 200:
            try:
                result = login_resp.json()
                print(f"로그인 결과: {result}")
            except:
                print(f"로그인 응답: {login_resp.text[:200]}")
        
        # Advisory 페이지 테스트
        advisory_resp = session.get(
            'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList',
            timeout=30
        )
        
        if advisory_resp.status_code == 200:
            soup = BeautifulSoup(advisory_resp.text, 'html.parser')
            if 'login' not in advisory_resp.url and not soup.find('form', {'id': 'loginForm'}):
                print("✅ 로그인 성공!")
                
                # 다시 데이터 요청
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
                
                form_data = {
                    'page': '0',
                    'tabSort': 'blacklist',
                    'startDate': start_date.strftime('%Y%m%d'),
                    'endDate': end_date.strftime('%Y%m%d'),
                    'findCondition': 'all',
                    'findKeyword': '',
                    'size': '10'
                }
                
                data_resp = session.post(
                    'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList',
                    data=form_data,
                    headers={
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Referer': 'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList'
                    },
                    timeout=30
                )
                
                if data_resp.status_code == 200:
                    soup = BeautifulSoup(data_resp.text, 'html.parser')
                    tables = soup.find_all('table')
                    for table in tables:
                        caption = table.find('caption')
                        if caption and '요주의 IP' in caption.text:
                            tbody = table.find('tbody')
                            if tbody:
                                rows = tbody.find_all('tr')
                                if rows:
                                    print(f"✅ 요주의 IP 데이터 발견: {len(rows)}개")
                                    return True
                
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ 로그인 오류: {e}")
        return False

if __name__ == "__main__":
    success = debug_regtech_auth()
    if success:
        print("\n✅ REGTECH 인증 및 데이터 접근 성공!")
    else:
        print("\n❌ REGTECH 인증 또는 데이터 접근 실패")