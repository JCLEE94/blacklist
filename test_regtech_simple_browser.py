#!/usr/bin/env python3
"""
REGTECH 브라우저로 페이지 구조 분석
"""

import os
from dotenv import load_dotenv

load_dotenv()

def analyze_page():
    """페이지 구조 분석"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Installing playwright...")
        os.system("pip install playwright")
        os.system("playwright install chromium")
        from playwright.sync_api import sync_playwright
    
    username = os.getenv('REGTECH_USERNAME', '')
    password = os.getenv('REGTECH_PASSWORD', '')
    base_url = "https://regtech.fsec.or.kr"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # 로그인 페이지 접속
        print(f"🔍 Accessing {base_url}/login/loginForm ...")
        page.goto(f'{base_url}/login/loginForm', wait_until='networkidle')
        
        # 페이지 HTML 저장
        html = page.content()
        with open('regtech_login_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("✅ Login page HTML saved to regtech_login_page.html")
        
        # 입력 필드 찾기
        print("\n📌 Finding input fields...")
        
        # 모든 input 필드 찾기
        inputs = page.query_selector_all('input')
        print(f"Found {len(inputs)} input fields:")
        
        for inp in inputs[:10]:  # 처음 10개만
            try:
                name = inp.get_attribute('name') or ''
                id_val = inp.get_attribute('id') or ''
                type_val = inp.get_attribute('type') or ''
                placeholder = inp.get_attribute('placeholder') or ''
                print(f"  - name='{name}', id='{id_val}', type='{type_val}', placeholder='{placeholder}'")
            except:
                pass
        
        # ID/PW 필드 찾기 시도
        possible_id_selectors = [
            'input[name="loginId"]',
            'input[name="loginID"]', 
            'input[name="id"]',
            'input[name="userId"]',
            'input[name="username"]',
            'input[id="loginId"]',
            'input[id="loginID"]',
            'input[type="text"]'
        ]
        
        possible_pw_selectors = [
            'input[name="loginPw"]',
            'input[name="loginPW"]',
            'input[name="password"]',
            'input[name="passwd"]',
            'input[name="pw"]',
            'input[id="loginPw"]',
            'input[id="loginPW"]',
            'input[type="password"]'
        ]
        
        print("\n🔑 Looking for login fields...")
        id_field = None
        pw_field = None
        
        for selector in possible_id_selectors:
            try:
                field = page.query_selector(selector)
                if field and field.is_visible():
                    id_field = selector
                    print(f"  ✅ ID field found: {selector}")
                    break
            except:
                pass
        
        for selector in possible_pw_selectors:
            try:
                field = page.query_selector(selector)
                if field and field.is_visible():
                    pw_field = selector
                    print(f"  ✅ PW field found: {selector}")
                    break
            except:
                pass
        
        # 로그인 시도
        if id_field and pw_field:
            print(f"\n🔐 Attempting login with {username}...")
            page.fill(id_field, username)
            page.fill(pw_field, password)
            
            # 로그인 버튼 찾기
            login_buttons = [
                'button:has-text("로그인")',
                'button:has-text("Login")',
                'input[type="submit"]',
                'button[type="submit"]',
                'a:has-text("로그인")',
                '#loginBtn',
                '.login-btn'
            ]
            
            for btn_selector in login_buttons:
                try:
                    btn = page.query_selector(btn_selector)
                    if btn and btn.is_visible():
                        print(f"  ✅ Login button found: {btn_selector}")
                        btn.click()
                        page.wait_for_load_state('networkidle', timeout=10000)
                        break
                except:
                    pass
            
            # 로그인 후 URL 확인
            print(f"\n📍 After login URL: {page.url}")
            
            if 'login' not in page.url.lower():
                print("✅ Login successful!")
                
                # 쿠키 확인
                cookies = context.cookies()
                print(f"\n🍪 Cookies ({len(cookies)} total):")
                for cookie in cookies:
                    if cookie['name'] in ['JSESSIONID', 'regtech-front']:
                        print(f"  - {cookie['name']}: {cookie['value'][:20]}...")
                
                # 메인 페이지 HTML 저장
                html = page.content()
                with open('regtech_main_page.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                print("\n✅ Main page HTML saved to regtech_main_page.html")
                
                # 메뉴 링크 찾기
                print("\n📋 Finding menu links...")
                links = page.query_selector_all('a')
                
                blacklist_links = []
                for link in links:
                    try:
                        href = link.get_attribute('href') or ''
                        text = link.inner_text() or ''
                        
                        if any(keyword in href.lower() or keyword in text.lower() 
                               for keyword in ['blacklist', 'advisory', '악성', 'threat', '차단']):
                            blacklist_links.append((text.strip(), href))
                            print(f"  - {text.strip()}: {href}")
                    except:
                        pass
                
                # 특정 URL 직접 시도
                print("\n🔍 Trying specific URLs...")
                test_urls = [
                    '/fcti/securityAdvisory/advisoryList',
                    '/fcti/securityAdvisory/blackListView',
                    '/board/boardList?menuCode=HPHB0620101'
                ]
                
                for url_path in test_urls:
                    try:
                        full_url = f"{base_url}{url_path}"
                        print(f"\n  Accessing: {full_url}")
                        page.goto(full_url, wait_until='networkidle', timeout=10000)
                        
                        # 현재 URL
                        print(f"    Current URL: {page.url}")
                        
                        # 테이블 찾기
                        tables = page.query_selector_all('table')
                        print(f"    Tables found: {len(tables)}")
                        
                        # 데이터 행 찾기
                        rows = page.query_selector_all('tbody tr')
                        print(f"    Data rows found: {len(rows)}")
                        
                        if rows:
                            # 첫 번째 행 내용 확인
                            first_row = rows[0]
                            cells = first_row.query_selector_all('td')
                            print(f"    First row cells: {len(cells)}")
                            for i, cell in enumerate(cells[:5]):
                                text = cell.inner_text().strip()
                                print(f"      Cell {i}: {text[:50]}")
                    except Exception as e:
                        print(f"    Error: {e}")
            else:
                print("❌ Login failed - still on login page")
        else:
            print("❌ Could not find login fields")
        
        browser.close()


if __name__ == "__main__":
    analyze_page()