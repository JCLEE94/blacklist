#!/usr/bin/env python3
"""
SECUDIUM 로그인 후 실제 페이지 탐색
"""
import requests
from bs4 import BeautifulSoup
import re
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

BASE_URL = "https://secudium.skinfosec.co.kr"
USERNAME = "nextrade"
PASSWORD = "Sprtmxm1@3"

def explore_secudium_after_login():
    """로그인 후 SECUDIUM 페이지 탐색"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    print("1. 로그인...")
    try:
        # 메인 페이지 접속
        session.get(BASE_URL, verify=False)
        
        # 로그인 (GET 방식으로 성공했으므로)
        login_data = {
            'lang': 'ko',
            'is_otp': 'N', 
            'is_expire': 'N',
            'login_name': USERNAME,
            'password': PASSWORD,
            'otp_value': ''
        }
        
        login_resp = session.get(f"{BASE_URL}/login", params=login_data, verify=False)
        print(f"   로그인 상태: {login_resp.status_code}")
        
    except Exception as e:
        print(f"   로그인 실패: {e}")
        return
    
    print("\n2. 메인 대시보드 탐색...")
    main_pages = ['/', '/main', '/dashboard', '/home', '/index']
    
    for page in main_pages:
        try:
            resp = session.get(f"{BASE_URL}{page}", verify=False)
            if resp.status_code == 200:
                print(f"\n   페이지: {page}")
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # 네비게이션 메뉴 찾기
                nav_links = soup.find_all('a', href=True)
                menu_items = []
                
                for link in nav_links:
                    href = link['href']
                    text = link.text.strip()
                    
                    # 블랙리스트, 위협, IP 관련 링크 찾기
                    if any(keyword in text.lower() for keyword in ['black', '차단', 'ip', '위협', 'threat', 'scan', '탐지']):
                        menu_items.append((text, href))
                    elif any(keyword in href.lower() for keyword in ['black', 'threat', 'ip', 'scan', 'detect']):
                        menu_items.append((text, href))
                
                if menu_items:
                    print("   관련 메뉴 항목:")
                    for text, href in menu_items:
                        print(f"      {text}: {href}")
                        
                        # 실제 페이지 접근해보기
                        if href.startswith('/'):
                            try:
                                sub_resp = session.get(f"{BASE_URL}{href}", verify=False)
                                print(f"         → 상태: {sub_resp.status_code}")
                                
                                if sub_resp.status_code == 200:
                                    # IP 패턴 찾기
                                    ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
                                    ips = ip_pattern.findall(sub_resp.text)
                                    if ips:
                                        unique_ips = list(set(ips))
                                        print(f"         → IP 발견: {len(unique_ips)}개")
                                        if len(unique_ips) > 0:
                                            print(f"         → 샘플: {unique_ips[:3]}")
                                    
                                    # 테이블 구조 찾기
                                    sub_soup = BeautifulSoup(sub_resp.text, 'html.parser')
                                    tables = sub_soup.find_all('table')
                                    if tables:
                                        print(f"         → 테이블 {len(tables)}개 발견")
                                        
                                        for i, table in enumerate(tables):
                                            rows = table.find_all('tr')
                                            if len(rows) > 1:  # 헤더 + 데이터
                                                print(f"         → 테이블 {i+1}: {len(rows)}행")
                                                
                                                # 첫 번째 데이터 행 확인
                                                if len(rows) > 1:
                                                    first_row = rows[1]
                                                    cells = first_row.find_all(['td', 'th'])
                                                    cell_texts = [cell.text.strip() for cell in cells]
                                                    print(f"         → 샘플 데이터: {cell_texts}")
                            except:
                                print(f"         → 접근 실패")
                
                # JavaScript에서 API 호출 찾기
                scripts = soup.find_all('script')
                api_calls = []
                
                for script in scripts:
                    if script.string:
                        # API 호출 패턴 찾기
                        api_patterns = re.findall(r'["\']([^"\']*api[^"\']*)["\']', script.string)
                        api_calls.extend(api_patterns)
                        
                        # Ajax 호출 패턴 찾기
                        ajax_patterns = re.findall(r'url\s*:\s*["\']([^"\']+)["\']', script.string)
                        api_calls.extend(ajax_patterns)
                
                if api_calls:
                    unique_apis = list(set(api_calls))
                    print("   발견된 API 패턴:")
                    for api in unique_apis[:10]:
                        if 'api' in api or api.startswith('/'):
                            print(f"      {api}")
                            
                            # API 테스트
                            if api.startswith('/'):
                                try:
                                    api_resp = session.get(f"{BASE_URL}{api}", verify=False)
                                    if api_resp.status_code == 200:
                                        print(f"         → 성공: {api_resp.status_code}")
                                        
                                        # JSON 응답 체크
                                        try:
                                            json_data = api_resp.json()
                                            print(f"         → JSON: {type(json_data)}")
                                            if isinstance(json_data, list) and len(json_data) > 0:
                                                print(f"         → 데이터: {len(json_data)}개")
                                        except:
                                            pass
                                except:
                                    pass
                
        except Exception as e:
            print(f"   페이지 {page} 오류: {e}")

if __name__ == "__main__":
    explore_secudium_after_login()