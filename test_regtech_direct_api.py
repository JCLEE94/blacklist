#!/usr/bin/env python3
"""
REGTECH 직접 API 호출로 데이터 수집
username/password 필드 사용
"""

import os
import re
import json
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

def collect_direct_api():
    """직접 API 호출로 데이터 수집"""
    
    username = os.getenv('REGTECH_USERNAME', '')
    password = os.getenv('REGTECH_PASSWORD', '')
    base_url = "https://regtech.fsec.or.kr"
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Origin': base_url,
        'Referer': f'{base_url}/login/loginForm'
    })
    
    # 1. 로그인 페이지 접속 (세션 쿠키 획득)
    print(f"🔐 Step 1: Accessing login page...")
    login_page_resp = session.get(f'{base_url}/login/loginForm')
    print(f"  Status: {login_page_resp.status_code}")
    print(f"  Cookies: {list(session.cookies.keys())}")
    
    # 2. 로그인 시도 - username/password 사용
    print(f"\n🔐 Step 2: Logging in as {username}...")
    login_data = {
        'username': username,
        'password': password,
        'url': '',
        'certRec': '',
        'certNum': '',
        'ciValue': '',
        'memberName': '',
        'birthDay1': ''
    }
    
    login_resp = session.post(
        f'{base_url}/login/loginProcess',
        data=login_data,
        allow_redirects=False
    )
    
    print(f"  Status: {login_resp.status_code}")
    print(f"  Cookies: {list(session.cookies.keys())}")
    
    # 리다이렉트 확인
    if login_resp.status_code in [302, 303]:
        redirect_url = login_resp.headers.get('Location', '')
        print(f"  Redirect to: {redirect_url}")
        
        if redirect_url and not redirect_url.startswith('http'):
            redirect_url = f"{base_url}{redirect_url}"
        
        if redirect_url:
            follow_resp = session.get(redirect_url)
            print(f"  Follow status: {follow_resp.status_code}")
    
    # 3. 로그인 성공 확인
    important_cookies = ['JSESSIONID', 'regtech-front']
    has_cookies = any(cookie in session.cookies for cookie in important_cookies)
    
    if not has_cookies:
        # 다른 로그인 방식 시도 - loginId/loginPw
        print("\n🔐 Trying alternative login method (loginId/loginPw)...")
        login_data2 = {
            'loginId': username,
            'loginPw': password
        }
        
        login_resp2 = session.post(
            f'{base_url}/login/loginProcess',
            data=login_data2,
            allow_redirects=False
        )
        
        print(f"  Status: {login_resp2.status_code}")
        print(f"  Cookies: {list(session.cookies.keys())}")
    
    # 4. 메인 페이지 확인
    print("\n📄 Step 3: Accessing main page...")
    main_resp = session.get(f'{base_url}/main')
    print(f"  Status: {main_resp.status_code}")
    
    # HTML에서 로그인 상태 확인
    if '로그아웃' in main_resp.text or 'logout' in main_resp.text.lower():
        print("  ✅ Login confirmed (logout button found)")
    elif username in main_resp.text:
        print(f"  ✅ Login confirmed (username '{username}' found)")
    else:
        print("  ⚠️ Login status uncertain")
    
    # 5. 데이터 수집 시도
    collected_ips = []
    
    # 5-1. Advisory List 페이지
    print("\n🔍 Step 4: Collecting data from advisoryList...")
    
    # GET 요청으로 먼저 시도
    advisory_url = f"{base_url}/fcti/securityAdvisory/advisoryList"
    advisory_resp = session.get(advisory_url)
    print(f"  GET Status: {advisory_resp.status_code}")
    
    if advisory_resp.status_code == 200:
        # HTML 파싱
        soup = BeautifulSoup(advisory_resp.text, 'html.parser')
        
        # 테이블 찾기
        tables = soup.find_all('table')
        print(f"  Tables found: {len(tables)}")
        
        # tbody의 tr 찾기
        rows = soup.select('tbody tr')
        print(f"  Rows found: {len(rows)}")
        
        # IP 패턴 찾기
        ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        
        for row in rows:
            text = row.get_text()
            ips = ip_pattern.findall(text)
            for ip in ips:
                octets = ip.split('.')
                try:
                    if all(0 <= int(o) <= 255 for o in octets):
                        if not ip.startswith(('127.', '192.168.', '10.', '172.', '0.')):
                            if ip not in collected_ips:
                                collected_ips.append(ip)
                                print(f"    ✅ Found IP: {ip}")
                except:
                    pass
    
    # POST 요청으로도 시도
    if len(collected_ips) == 0:
        print("\n  Trying POST request...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        post_data = {
            'page': '1',
            'size': '100',
            'startDate': start_date.strftime('%Y%m%d'),
            'endDate': end_date.strftime('%Y%m%d'),
            'tabSort': 'blacklist',
            'findCondition': 'all',
            'findKeyword': ''
        }
        
        advisory_post_resp = session.post(advisory_url, data=post_data)
        print(f"  POST Status: {advisory_post_resp.status_code}")
        
        if advisory_post_resp.status_code == 200:
            soup = BeautifulSoup(advisory_post_resp.text, 'html.parser')
            
            # IP 패턴 찾기
            for text in soup.stripped_strings:
                ips = ip_pattern.findall(text)
                for ip in ips:
                    octets = ip.split('.')
                    try:
                        if all(0 <= int(o) <= 255 for o in octets):
                            if not ip.startswith(('127.', '192.168.', '10.', '172.', '0.')):
                                if ip not in collected_ips:
                                    collected_ips.append(ip)
                                    print(f"    ✅ Found IP: {ip}")
                    except:
                        pass
    
    # 5-2. Board List 페이지
    if len(collected_ips) == 0:
        print("\n🔍 Trying boardList...")
        board_url = f"{base_url}/board/boardList"
        board_params = {'menuCode': 'HPHB0620101'}
        
        board_resp = session.get(board_url, params=board_params)
        print(f"  Status: {board_resp.status_code}")
        
        if board_resp.status_code == 200:
            soup = BeautifulSoup(board_resp.text, 'html.parser')
            
            # 게시판 내용에서 IP 찾기
            for text in soup.stripped_strings:
                ips = ip_pattern.findall(text)
                for ip in ips:
                    octets = ip.split('.')
                    try:
                        if all(0 <= int(o) <= 255 for o in octets):
                            if not ip.startswith(('127.', '192.168.', '10.', '172.', '0.')):
                                if ip not in collected_ips:
                                    collected_ips.append(ip)
                                    print(f"    ✅ Found IP: {ip}")
                    except:
                        pass
    
    # 5-3. API 엔드포인트 시도
    if len(collected_ips) == 0:
        print("\n🔍 Trying API endpoints...")
        
        api_endpoints = [
            '/api/blacklist/list',
            '/api/threat/blacklist',
            '/board/selectIpPoolList',
            '/fcti/api/blacklist'
        ]
        
        for endpoint in api_endpoints:
            try:
                api_url = f"{base_url}{endpoint}"
                print(f"  Trying: {api_url}")
                
                api_resp = session.post(api_url, json={})
                if api_resp.status_code == 200:
                    try:
                        data = api_resp.json()
                        print(f"    Response type: {type(data)}")
                        
                        # JSON 응답에서 IP 찾기
                        if isinstance(data, dict):
                            for key in ['list', 'data', 'items', 'result']:
                                if key in data and isinstance(data[key], list):
                                    for item in data[key]:
                                        if isinstance(item, dict):
                                            for ip_key in ['ip', 'ipAddress', 'address']:
                                                if ip_key in item:
                                                    ip = item[ip_key]
                                                    if ip not in collected_ips:
                                                        collected_ips.append(ip)
                                                        print(f"    ✅ Found IP: {ip}")
                    except:
                        pass
            except Exception as e:
                print(f"    Error: {e}")
    
    # 6. 결과
    print(f"\n{'='*60}")
    print(f"📊 총 {len(collected_ips)}개 IP 수집")
    
    if collected_ips:
        print("\n처음 10개 IP:")
        for i, ip in enumerate(collected_ips[:10], 1):
            print(f"  {i}. {ip}")
        
        # IP 데이터 형식 변환
        ip_data_list = []
        for ip in collected_ips:
            ip_data_list.append({
                "ip": ip,
                "source": "REGTECH",
                "description": "Malicious IP from REGTECH API",
                "detection_date": datetime.now().strftime('%Y-%m-%d'),
                "confidence": "high"
            })
        
        return ip_data_list
    
    return []


if __name__ == "__main__":
    print("🚀 REGTECH Direct API Collection")
    print("="*60)
    
    ips = collect_direct_api()
    
    if ips:
        print(f"\n✅ 성공! {len(ips)}개 실제 IP 수집")
        
        # PostgreSQL에 저장
        try:
            from src.core.data_storage_fixed import FixedDataStorage
            storage = FixedDataStorage()
            result = storage.store_ips(ips, "REGTECH")
            
            if result.get("success"):
                print(f"✅ PostgreSQL 저장 완료: {result.get('imported_count')}개")
            else:
                print(f"❌ 저장 실패: {result.get('error')}")
        except Exception as e:
            print(f"❌ 저장 중 오류: {e}")
    else:
        print("\n❌ 데이터를 찾을 수 없음")
        print("가능한 원인:")
        print("1. REGTECH 사이트에 현재 데이터가 없음")
        print("2. 접근 권한 부족")
        print("3. API 경로 변경")