#!/usr/bin/env python3
"""
REGTECH 전체 세션 시뮬레이션 - 로그인부터 시작
"""
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import time

def collect_with_full_session():
    """완전한 로그인 세션으로 REGTECH 수집"""
    print("🧪 REGTECH 전체 세션 시뮬레이션")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    })
    
    try:
        # 1. 메인 페이지 접속 (쿠키 초기화)
        print("\n1. 메인 페이지 접속...")
        main_resp = session.get('https://regtech.fsec.or.kr/main/main', timeout=30)
        print(f"메인 페이지: {main_resp.status_code}")
        
        # 2. 로그인 페이지
        print("\n2. 로그인 페이지 접속...")
        login_page = session.get('https://regtech.fsec.or.kr/login/loginForm', timeout=30)
        print(f"로그인 페이지: {login_page.status_code}")
        
        # 3. 로그인 수행
        print("\n3. 로그인 시도...")
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
        print(f"로그인 응답 내용: {login_resp.text[:200]}")
        
        # 로그인 성공 확인
        if login_resp.status_code == 200:
            # JSON 응답 확인
            try:
                login_result = login_resp.json()
                print(f"로그인 결과: {login_result}")
            except:
                print("로그인 응답이 JSON이 아님")
        
        # 4. Advisory 페이지 접속
        print("\n4. Advisory 페이지 접속...")
        advisory_resp = session.get(
            'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList',
            timeout=30
        )
        print(f"Advisory 페이지: {advisory_resp.status_code}")
        
        # 5. 블랙리스트 데이터 요청
        print("\n5. 블랙리스트 데이터 요청...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # 다양한 날짜 범위 시도
        date_ranges = [
            (30, "최근 30일"),
            (90, "최근 90일"),
            (180, "최근 180일"),
            (365, "최근 1년")
        ]
        
        for days, desc in date_ranges:
            print(f"\n📅 {desc} 데이터 요청...")
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            start_date_str = start_date.strftime('%Y%m%d')
            end_date_str = end_date.strftime('%Y%m%d')
            
            form_data = {
                'page': '0',
                'tabSort': 'blacklist',
                'excelDownload': '',
                'cveId': '',
                'ipId': '',
                'estId': '',
                'startDate': start_date_str,
                'endDate': end_date_str,
                'findCondition': 'all',
                'findKeyword': '',
                'size': '100'  # 더 많은 데이터 요청
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
                # HTML 파싱
                soup = BeautifulSoup(data_resp.text, 'html.parser')
                
                # 요주의 IP 테이블 찾기
                tables = soup.find_all('table')
                
                for table in tables:
                    caption = table.find('caption')
                    if caption and '요주의 IP' in caption.text:
                        tbody = table.find('tbody')
                        if tbody:
                            rows = tbody.find_all('tr')
                            
                            if rows:
                                print(f"✅ {len(rows)}개의 IP 발견!")
                                
                                # 처음 5개만 출력
                                for i, row in enumerate(rows[:5]):
                                    cells = row.find_all('td')
                                    if len(cells) >= 6:
                                        ip = cells[0].get_text(strip=True)
                                        country = cells[1].get_text(strip=True)
                                        attack_type = cells[2].get_text(strip=True)
                                        print(f"  - {ip} ({country}) - {attack_type}")
                                
                                if len(rows) > 5:
                                    print(f"  ... 그리고 {len(rows) - 5}개 더")
                                
                                return True
                
                # IP를 찾지 못한 경우
                print(f"❌ {desc}에 IP 데이터 없음")
                
                # 총 건수 확인
                total_pattern = r'총\s*(\d+)\s*건'
                matches = re.findall(total_pattern, data_resp.text)
                if matches:
                    print(f"  총 건수: {matches[0]}건")
                
                # 디버깅: 응답 저장
                if days == 30:  # 첫 번째만 저장
                    with open('regtech_session_response.html', 'w', encoding='utf-8') as f:
                        f.write(data_resp.text)
                    print("  💾 응답이 regtech_session_response.html로 저장됨")
        
        # 6. 현재 세션 쿠키 확인
        print("\n🍪 현재 세션 쿠키:")
        for cookie in session.cookies:
            print(f"  - {cookie.name}: {cookie.value[:50]}...")
        
        return False
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = collect_with_full_session()
    if success:
        print("\n🎉 전체 세션으로 데이터 수집 성공!")
    else:
        print("\n💥 전체 세션에서도 데이터를 찾을 수 없음")