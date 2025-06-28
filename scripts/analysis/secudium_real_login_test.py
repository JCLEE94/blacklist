#!/usr/bin/env python3
"""
SECUDIUM 실제 로그인 성공 테스트
로그인 후 실제 대시보드/메인 페이지 접근 확인
"""
import requests
from bs4 import BeautifulSoup
import re
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

BASE_URL = "https://secudium.skinfosec.co.kr"
USERNAME = "nextrade"
PASSWORD = "Sprtmxm1@3"

def test_real_login_success():
    """실제 로그인 성공 여부 확인"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    print("=== SECUDIUM 실제 로그인 테스트 ===")
    
    print("\n1. 로그인 전 상태 확인...")
    before_resp = session.get(BASE_URL, verify=False)
    before_soup = BeautifulSoup(before_resp.text, 'html.parser')
    before_title = before_soup.title.string if before_soup.title else 'None'
    print(f"   로그인 전 제목: {before_title}")
    print(f"   로그인 전 URL: {before_resp.url}")
    print(f"   로그인 전 쿠키: {dict(session.cookies)}")
    
    print("\n2. 다양한 로그인 방법 시도...")
    
    login_methods = [
        # 방법 1: 기존 GET 방식
        {
            'name': 'GET 방식 (기존)',
            'method': 'GET',
            'url': f"{BASE_URL}/login",
            'data': {
                'lang': 'ko',
                'is_otp': 'N',
                'is_expire': 'N',
                'login_name': USERNAME,
                'password': PASSWORD,
                'otp_value': ''
            }
        },
        # 방법 2: 메인 페이지에 POST
        {
            'name': 'POST to main page',
            'method': 'POST',
            'url': BASE_URL,
            'data': {
                'lang': 'ko',
                'is_otp': 'N',
                'is_expire': 'N',
                'login_name': USERNAME,
                'password': PASSWORD,
                'otp_value': ''
            }
        },
        # 방법 3: 로그인 폼 action 확인 후 POST
        {
            'name': 'POST to form action',
            'method': 'POST',
            'url': f"{BASE_URL}/loginProcess",
            'data': {
                'lang': 'ko',
                'is_otp': 'N',
                'is_expire': 'N',
                'login_name': USERNAME,
                'password': PASSWORD,
                'otp_value': ''
            }
        }
    ]
    
    successful_login = None
    
    for method_info in login_methods:
        print(f"\n   시도: {method_info['name']}")
        
        try:
            # 새 세션으로 시작
            test_session = requests.Session()
            test_session.headers.update(session.headers)
            
            # 메인 페이지 접속으로 초기화
            test_session.get(BASE_URL, verify=False)
            
            if method_info['method'] == 'GET':
                resp = test_session.get(method_info['url'], params=method_info['data'], 
                                      verify=False, allow_redirects=True)
            else:
                resp = test_session.post(method_info['url'], data=method_info['data'], 
                                       verify=False, allow_redirects=True)
            
            print(f"      응답: {resp.status_code}")
            print(f"      최종 URL: {resp.url}")
            print(f"      쿠키: {dict(test_session.cookies)}")
            
            # 로그인 후 페이지 확인
            soup = BeautifulSoup(resp.text, 'html.parser')
            title = soup.title.string if soup.title else 'None'
            print(f"      제목: {title}")
            
            # 로그인 성공 여부 판단
            if title != '::: Login :::' and 'login' not in title.lower():
                print(f"      ✅ 로그인 성공!")
                successful_login = (method_info, test_session, resp)
                break
            else:
                print(f"      ❌ 여전히 로그인 페이지")
                
        except Exception as e:
            print(f"      오류: {e}")
    
    if not successful_login:
        print("\n❌ 모든 로그인 방법 실패")
        return None
    
    print(f"\n3. 성공한 로그인으로 페이지 탐색...")
    
    method_info, login_session, login_resp = successful_login
    
    # 로그인 성공 후 다양한 페이지 접근
    test_pages = [
        '/',
        '/main',
        '/dashboard',
        '/home',
        '/index',
        '/menu',
        '/secinfo',
        '/data',
        '/report'
    ]
    
    accessible_pages = []
    
    for page in test_pages:
        try:
            resp = login_session.get(f"{BASE_URL}{page}", verify=False)
            print(f"\n   {page}: {resp.status_code}")
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                title = soup.title.string if soup.title else 'None'
                print(f"      제목: {title}")
                
                # 로그인 페이지가 아닌 경우
                if 'login' not in title.lower():
                    accessible_pages.append((page, resp))
                    print(f"      ✅ 접근 가능한 페이지!")
                    
                    # 페이지 내용 분석
                    analyze_authenticated_page(page, resp, login_session)
                else:
                    print(f"      ❌ 로그인 페이지로 리다이렉트됨")
            
        except Exception as e:
            print(f"   {page} 오류: {e}")
    
    return accessible_pages

def analyze_authenticated_page(page_name, response, session):
    """인증된 페이지 상세 분석"""
    print(f"\n      📋 {page_name} 페이지 분석:")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 링크 분석
    links = soup.find_all('a', href=True)
    data_links = []
    
    for link in links:
        href = link['href']
        text = link.get_text(strip=True)
        
        keywords = ['데이터', '리포트', '블랙리스트', '위협', '보안', 
                   'data', 'report', 'blacklist', 'threat', 'security',
                   'list', 'export', 'download']
        
        if any(keyword in text.lower() for keyword in keywords) or \
           any(keyword in href.lower() for keyword in keywords):
            data_links.append((text, href))
    
    if data_links:
        print(f"         데이터 관련 링크: {len(data_links)}개")
        for text, href in data_links[:5]:
            print(f"            {text}: {href}")
    
    # 테이블 분석
    tables = soup.find_all('table')
    if tables:
        print(f"         테이블: {len(tables)}개")
        for i, table in enumerate(tables):
            rows = table.find_all('tr')
            if len(rows) > 1:  # 헤더 + 데이터
                print(f"            테이블 {i+1}: {len(rows)}행")
                
                # 첫 번째 데이터 행 확인
                first_data_row = rows[1] if len(rows) > 1 else None
                if first_data_row:
                    cells = [td.get_text(strip=True) for td in first_data_row.find_all('td')]
                    print(f"               첫 번째 행: {cells}")
                    
                    # IP 패턴 체크
                    for cell in cells:
                        if re.match(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', cell):
                            print(f"               🎯 IP 발견: {cell}")
    
    # JavaScript 분석
    scripts = soup.find_all('script')
    ajax_urls = []
    
    for script in scripts:
        if script.string:
            # API 호출 패턴
            patterns = [
                r'url\s*:\s*["\']([^"\']+)["\']',
                r'fetch\s*\(["\']([^"\']+)["\']',
                r'api_host\s*=\s*["\']([^"\']+)["\']'
            ]
            
            for pattern in patterns:
                urls = re.findall(pattern, script.string)
                ajax_urls.extend(urls)
    
    if ajax_urls:
        print(f"         AJAX URL: {len(set(ajax_urls))}개")
        for url in list(set(ajax_urls))[:3]:
            print(f"            {url}")
    
    # 실제 데이터 링크 테스트
    if data_links:
        print(f"         데이터 링크 접근 테스트:")
        for text, href in data_links[:3]:  # 처음 3개만
            if href.startswith('/'):
                try:
                    test_resp = session.get(f"{BASE_URL}{href}", verify=False)
                    print(f"            {href}: {test_resp.status_code}")
                    
                    if test_resp.status_code == 200:
                        # IP 패턴 찾기
                        ips = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', test_resp.text)
                        real_ips = [ip for ip in ips if not ip.startswith(('127.', '192.168.', '10.', '172.'))]
                        
                        if real_ips:
                            print(f"               🎉 실제 IP {len(real_ips)}개 발견!")
                            print(f"               샘플: {real_ips[:5]}")
                except:
                    pass

if __name__ == "__main__":
    accessible_pages = test_real_login_success()
    
    if accessible_pages:
        print(f"\n🎉 성공! {len(accessible_pages)}개 인증된 페이지 접근 가능!")
        for page, _ in accessible_pages:
            print(f"   ✅ {page}")
    else:
        print(f"\n💔 실제 로그인에 실패했습니다.")
        print(f"SECUDIUM 계정 상태나 인증 방식을 확인해야 할 것 같습니다.")