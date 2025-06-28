#!/usr/bin/env python3
"""
SECUDIUM BeautifulSoup4 분석
로그인 후 실제 페이지 구조 분석하여 데이터 위치 찾기
"""
import requests
from bs4 import BeautifulSoup
import re
import json
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

BASE_URL = "https://secudium.skinfosec.co.kr"
USERNAME = "nextrade"
PASSWORD = "Sprtmxm1@3"

def analyze_secudium_with_bs4():
    """BeautifulSoup4로 SECUDIUM 전체 분석"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    print("=== SECUDIUM BS4 분석 시작 ===")
    
    print("\n1. 로그인...")
    # 메인 페이지 접속
    main_resp = session.get(BASE_URL, verify=False)
    print(f"   메인 페이지: {main_resp.status_code}")
    
    # 로그인
    login_data = {
        'lang': 'ko',
        'is_otp': 'N',
        'is_expire': 'N',
        'login_name': USERNAME,
        'password': PASSWORD,
        'otp_value': ''
    }
    
    login_resp = session.get(f"{BASE_URL}/login", params=login_data, verify=False)
    print(f"   로그인: {login_resp.status_code}")
    
    print("\n2. 로그인 후 메인 페이지 BS4 분석...")
    
    # 로그인 후 메인 페이지 다시 가져오기
    post_login_resp = session.get(BASE_URL, verify=False)
    soup = BeautifulSoup(post_login_resp.text, 'html.parser')
    
    print(f"   페이지 제목: {soup.title.string if soup.title else 'None'}")
    print(f"   HTML 길이: {len(post_login_resp.text)} bytes")
    
    # 모든 링크 분석
    print(f"\n3. 모든 링크 분석...")
    links = soup.find_all('a', href=True)
    print(f"   총 링크 개수: {len(links)}")
    
    interesting_links = []
    for link in links:
        href = link['href']
        text = link.get_text(strip=True)
        
        # 관심있는 키워드
        keywords = ['보안', '데이터', '리포트', '통계', '분석', '목록', '리스트', 
                   'security', 'data', 'report', 'list', 'blacklist', 'threat', 
                   'malware', 'ip', 'scan', 'dashboard', 'main', 'menu']
        
        if any(keyword in text.lower() for keyword in keywords) or \
           any(keyword in href.lower() for keyword in keywords):
            interesting_links.append((text, href))
    
    print(f"   관심있는 링크: {len(interesting_links)}개")
    for text, href in interesting_links[:10]:  # 처음 10개만
        print(f"      {text}: {href}")
    
    print(f"\n4. 네비게이션/메뉴 구조 분석...")
    
    # 네비게이션 요소들 찾기
    nav_elements = soup.find_all(['nav', 'menu', 'ul'])
    nav_elements.extend(soup.find_all(class_=re.compile(r'nav|menu|sidebar', re.I)))
    nav_elements.extend(soup.find_all(id=re.compile(r'nav|menu|sidebar', re.I)))
    
    print(f"   네비게이션 요소: {len(nav_elements)}개")
    
    for i, nav in enumerate(nav_elements):
        print(f"\n   네비게이션 {i+1}: {nav.name}")
        if nav.get('class'):
            print(f"      클래스: {nav.get('class')}")
        if nav.get('id'):
            print(f"      ID: {nav.get('id')}")
        
        # 네비게이션 내부 링크
        nav_links = nav.find_all('a', href=True)
        if nav_links:
            print(f"      내부 링크: {len(nav_links)}개")
            for link in nav_links[:5]:  # 처음 5개만
                print(f"         {link.get_text(strip=True)}: {link['href']}")
    
    print(f"\n5. 폼 분석...")
    
    forms = soup.find_all('form')
    print(f"   폼 개수: {len(forms)}")
    
    for i, form in enumerate(forms):
        print(f"\n   폼 {i+1}:")
        print(f"      액션: {form.get('action', 'None')}")
        print(f"      메서드: {form.get('method', 'GET')}")
        
        inputs = form.find_all(['input', 'select', 'textarea'])
        print(f"      입력 필드: {len(inputs)}개")
        
        for inp in inputs:
            name = inp.get('name', '')
            input_type = inp.get('type', inp.name)
            value = inp.get('value', '')
            if name:
                print(f"         {name}: {input_type} = {value}")
    
    print(f"\n6. JavaScript 분석...")
    
    scripts = soup.find_all('script')
    print(f"   스크립트 태그: {len(scripts)}개")
    
    js_urls = []
    js_functions = []
    ajax_urls = []
    
    for script in scripts:
        # 외부 스크립트
        if script.get('src'):
            js_urls.append(script['src'])
        
        # 인라인 스크립트 분석
        if script.string:
            script_content = script.string
            
            # 함수 찾기
            functions = re.findall(r'function\s+(\w+)\s*\(', script_content)
            js_functions.extend(functions)
            
            # AJAX URL 찾기
            ajax_patterns = [
                r'url\s*:\s*["\']([^"\']+)["\']',
                r'fetch\s*\(\s*["\']([^"\']+)["\']',
                r'\.get\s*\(\s*["\']([^"\']+)["\']',
                r'\.post\s*\(\s*["\']([^"\']+)["\']'
            ]
            
            for pattern in ajax_patterns:
                urls = re.findall(pattern, script_content)
                ajax_urls.extend(urls)
    
    print(f"      외부 JS 파일: {len(js_urls)}개")
    for url in js_urls[:5]:
        print(f"         {url}")
    
    print(f"      함수: {len(set(js_functions))}개")
    for func in list(set(js_functions))[:10]:
        print(f"         {func}()")
    
    print(f"      AJAX URL: {len(set(ajax_urls))}개")
    for url in list(set(ajax_urls))[:10]:
        print(f"         {url}")
    
    print(f"\n7. 테이블 구조 분석...")
    
    tables = soup.find_all('table')
    print(f"   테이블 개수: {len(tables)}")
    
    for i, table in enumerate(tables):
        print(f"\n   테이블 {i+1}:")
        
        rows = table.find_all('tr')
        print(f"      행 개수: {len(rows)}")
        
        if rows:
            # 헤더 분석
            header_row = rows[0]
            headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
            print(f"      헤더: {headers}")
            
            # 데이터 행 샘플
            for j, row in enumerate(rows[1:3]):  # 처음 2개 데이터 행
                cells = [td.get_text(strip=True) for td in row.find_all('td')]
                if cells:
                    print(f"      데이터 {j+1}: {cells}")
    
    print(f"\n8. 숨겨진 요소 및 동적 컨텐츠 분석...")
    
    # 숨겨진 div들
    hidden_divs = soup.find_all('div', style=re.compile(r'display\s*:\s*none', re.I))
    hidden_divs.extend(soup.find_all(class_=re.compile(r'hidden', re.I)))
    
    print(f"   숨겨진 요소: {len(hidden_divs)}개")
    
    for div in hidden_divs[:5]:
        div_id = div.get('id', 'no-id')
        div_class = div.get('class', [])
        print(f"      ID: {div_id}, 클래스: {div_class}")
        
        # 숨겨진 요소 내부의 링크나 데이터
        hidden_links = div.find_all('a', href=True)
        if hidden_links:
            print(f"         숨겨진 링크: {len(hidden_links)}개")
            for link in hidden_links[:3]:
                print(f"            {link.get_text(strip=True)}: {link['href']}")
    
    print(f"\n9. 실제 페이지 접근 테스트...")
    
    # 발견한 링크들 실제 접근해보기
    test_links = [link[1] for link in interesting_links if link[1].startswith('/')]
    
    found_data_pages = []
    
    for link in test_links[:15]:  # 처음 15개만 테스트
        try:
            resp = session.get(f"{BASE_URL}{link}", verify=False, timeout=10)
            print(f"\n   {link}: {resp.status_code}")
            
            if resp.status_code == 200:
                # 페이지 내용 분석
                page_soup = BeautifulSoup(resp.text, 'html.parser')
                
                # IP 패턴 찾기
                page_text = page_soup.get_text()
                ips = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', page_text)
                real_ips = [ip for ip in ips if not ip.startswith(('127.', '192.168.', '10.', '172.'))]
                
                if real_ips:
                    print(f"      ✅ IP 발견: {len(real_ips)}개")
                    print(f"      샘플: {real_ips[:5]}")
                    found_data_pages.append((link, real_ips))
                
                # 테이블이나 리스트 확인
                page_tables = page_soup.find_all('table')
                page_lists = page_soup.find_all(['ul', 'ol'])
                
                if page_tables:
                    print(f"      테이블: {len(page_tables)}개")
                if page_lists:
                    print(f"      리스트: {len(page_lists)}개")
                
                # 다운로드 링크 확인
                download_links = page_soup.find_all('a', href=re.compile(r'\.(xlsx?|csv|json|xml)$', re.I))
                if download_links:
                    print(f"      다운로드 링크: {len(download_links)}개")
                    for dl in download_links[:3]:
                        print(f"         {dl.get_text(strip=True)}: {dl['href']}")
                
        except Exception as e:
            print(f"   {link}: 오류 - {e}")
    
    print(f"\n10. AJAX 엔드포인트 테스트...")
    
    # 발견한 AJAX URL들 테스트
    unique_ajax_urls = list(set(ajax_urls))
    
    for ajax_url in unique_ajax_urls[:10]:  # 처음 10개만
        if ajax_url.startswith('/'):
            try:
                # AJAX 스타일 헤더로 요청
                session.headers.update({
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json, text/javascript, */*; q=0.01'
                })
                
                resp = session.get(f"{BASE_URL}{ajax_url}", verify=False, timeout=10)
                print(f"\n   AJAX {ajax_url}: {resp.status_code}")
                
                if resp.status_code == 200:
                    content_type = resp.headers.get('Content-Type', '')
                    print(f"      Content-Type: {content_type}")
                    
                    if 'json' in content_type:
                        try:
                            data = resp.json()
                            print(f"      JSON: {type(data)}")
                            
                            if isinstance(data, list) and len(data) > 0:
                                print(f"      데이터 개수: {len(data)}")
                                print(f"      첫 번째: {data[0]}")
                            elif isinstance(data, dict):
                                print(f"      키: {list(data.keys())}")
                                
                        except ValueError:
                            print(f"      JSON 파싱 실패")
                    else:
                        print(f"      응답 길이: {len(resp.text)}")
                        if len(resp.text) < 500:
                            print(f"      내용: {resp.text}")
                            
            except Exception as e:
                print(f"   AJAX {ajax_url}: 오류 - {e}")
    
    print(f"\n=== 분석 결과 요약 ===")
    print(f"✅ 링크: {len(interesting_links)}개 발견")
    print(f"✅ 네비게이션: {len(nav_elements)}개 발견") 
    print(f"✅ 폼: {len(forms)}개 발견")
    print(f"✅ 테이블: {len(tables)}개 발견")
    print(f"✅ AJAX URL: {len(unique_ajax_urls)}개 발견")
    
    if found_data_pages:
        print(f"🎉 데이터 페이지: {len(found_data_pages)}개 발견!")
        for page, ips in found_data_pages:
            print(f"   {page}: {len(ips)}개 IP")
    else:
        print(f"❌ 실제 데이터 페이지를 찾지 못함")
    
    return found_data_pages

if __name__ == "__main__":
    data_pages = analyze_secudium_with_bs4()
    
    if data_pages:
        print(f"\n🎯 성공! 총 {len(data_pages)}개 데이터 페이지 발견!")
        total_ips = sum(len(ips) for _, ips in data_pages)
        print(f"전체 IP: {total_ips}개")
    else:
        print(f"\n💔 실제 SECUDIUM 데이터를 찾지 못했습니다.")
        print(f"수동 다운로드나 API 토큰이 필요할 것 같습니다.")