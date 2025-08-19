#!/usr/bin/env python3
"""
REGTECH 브라우저 자동화로 실제 데이터 수집
Playwright를 사용하여 실제 브라우저처럼 동작
"""

import os
import re
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def collect_with_browser():
    """브라우저 자동화로 데이터 수집"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright not installed. Installing...")
        os.system("pip install playwright")
        os.system("playwright install chromium")
        from playwright.sync_api import sync_playwright
    
    username = os.getenv('REGTECH_USERNAME', '')
    password = os.getenv('REGTECH_PASSWORD', '')
    base_url = "https://regtech.fsec.or.kr"
    
    collected_ips = []
    
    with sync_playwright() as p:
        # 브라우저 실행 (서버에서는 headless 모드 필수)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # 네트워크 요청 모니터링
        def handle_response(response):
            """응답 모니터링"""
            url = response.url
            if 'blacklist' in url.lower() or 'advisory' in url.lower() or 'threat' in url.lower():
                print(f"📡 Response from: {url}")
                if response.status == 200:
                    try:
                        # JSON 응답 처리
                        if 'json' in response.headers.get('content-type', '').lower():
                            data = response.json()
                            print(f"  JSON Data: {json.dumps(data, indent=2)[:500]}")
                            
                            # IP 추출 로직
                            if isinstance(data, dict):
                                # list, data, items 등의 키에서 IP 찾기
                                for key in ['list', 'data', 'items', 'result', 'ipList']:
                                    if key in data and isinstance(data[key], list):
                                        for item in data[key]:
                                            if isinstance(item, dict):
                                                for ip_key in ['ip', 'ipAddress', 'address', 'maliciousIp']:
                                                    if ip_key in item:
                                                        ip = item[ip_key]
                                                        if re.match(r'\d+\.\d+\.\d+\.\d+', str(ip)):
                                                            collected_ips.append(ip)
                                                            print(f"    ✅ Found IP: {ip}")
                    except:
                        pass
        
        page.on("response", handle_response)
        
        # 1. 로그인
        print(f"🔐 Logging in as {username}...")
        page.goto(f'{base_url}/login/loginForm')
        page.wait_for_load_state('networkidle')
        
        # ID/PW 입력
        page.fill('input[name="loginId"]', username)
        page.fill('input[name="loginPw"]', password)
        
        # 로그인 버튼 클릭
        page.click('button:has-text("로그인")')
        page.wait_for_load_state('networkidle')
        
        # 로그인 확인
        if 'login' not in page.url.lower():
            print("✅ Login successful!")
        else:
            print("❌ Login failed")
            browser.close()
            return []
        
        # 2. 메뉴 탐색 - 보안 정보 관련 메뉴 찾기
        print("\n🔍 Looking for security advisory menus...")
        
        # 가능한 메뉴 경로들
        menu_paths = [
            '/fcti/securityAdvisory/advisoryList',
            '/fcti/securityAdvisory/blackListView',
            '/board/boardList?menuCode=HPHB0620101',
            '/threat/blacklist',
            '/security/malicious/ip',
        ]
        
        for path in menu_paths:
            try:
                print(f"\n📄 Trying: {path}")
                page.goto(f'{base_url}{path}', wait_until='networkidle')
                page.wait_for_timeout(2000)  # 2초 대기
                
                # 현재 페이지 URL 확인
                current_url = page.url
                print(f"  Current URL: {current_url}")
                
                # 페이지 내용에서 IP 패턴 찾기
                content = page.content()
                
                # IP 패턴 매칭
                ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
                found_ips = ip_pattern.findall(content)
                
                # 유효한 IP만 필터링
                for ip in found_ips:
                    octets = ip.split('.')
                    if all(0 <= int(o) <= 255 for o in octets):
                        # 로컬 IP나 예약된 IP 제외
                        if not ip.startswith(('127.', '192.168.', '10.', '172.', '0.')):
                            if ip not in collected_ips:
                                collected_ips.append(ip)
                                print(f"  ✅ Found IP: {ip}")
                
                # 테이블 데이터 확인
                tables = page.query_selector_all('table')
                print(f"  Found {len(tables)} tables")
                
                for table in tables:
                    rows = table.query_selector_all('tr')
                    for row in rows:
                        cells = row.query_selector_all('td')
                        for cell in cells:
                            text = cell.inner_text()
                            ips = ip_pattern.findall(text)
                            for ip in ips:
                                octets = ip.split('.')
                                try:
                                    if all(0 <= int(o) <= 255 for o in octets):
                                        if not ip.startswith(('127.', '192.168.', '10.', '172.', '0.')):
                                            if ip not in collected_ips:
                                                collected_ips.append(ip)
                                                print(f"  ✅ Found IP in table: {ip}")
                                except:
                                    pass
                
                # JavaScript 변수에서 IP 찾기
                js_result = page.evaluate("""
                    () => {
                        let ips = [];
                        // window 객체의 모든 변수 확인
                        for (let key in window) {
                            if (key.toLowerCase().includes('ip') || 
                                key.toLowerCase().includes('blacklist') ||
                                key.toLowerCase().includes('threat')) {
                                let val = window[key];
                                if (typeof val === 'string' && val.match(/\\d+\\.\\d+\\.\\d+\\.\\d+/)) {
                                    ips.push(val);
                                } else if (Array.isArray(val)) {
                                    val.forEach(item => {
                                        if (typeof item === 'string' && item.match(/\\d+\\.\\d+\\.\\d+\\.\\d+/)) {
                                            ips.push(item);
                                        } else if (typeof item === 'object' && item) {
                                            for (let prop in item) {
                                                if (typeof item[prop] === 'string' && 
                                                    item[prop].match(/\\d+\\.\\d+\\.\\d+\\.\\d+/)) {
                                                    ips.push(item[prop]);
                                                }
                                            }
                                        }
                                    });
                                }
                            }
                        }
                        return ips;
                    }
                """)
                
                if js_result:
                    for ip in js_result:
                        if ip not in collected_ips:
                            collected_ips.append(ip)
                            print(f"  ✅ Found IP in JS: {ip}")
                
                # Excel 다운로드 버튼 찾기
                excel_buttons = page.query_selector_all('button:has-text("Excel"), a:has-text("Excel"), button:has-text("엑셀"), a:has-text("엑셀")')
                if excel_buttons:
                    print(f"  Found {len(excel_buttons)} Excel download buttons")
                    for button in excel_buttons[:1]:  # 첫 번째 버튼만
                        try:
                            # 다운로드 대기 설정
                            with page.expect_download() as download_info:
                                button.click()
                                download = download_info.value
                                
                                # 파일 저장
                                download_path = f"/tmp/regtech_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                                download.save_as(download_path)
                                print(f"  📥 Downloaded: {download_path}")
                                
                                # Excel 파일 파싱
                                try:
                                    import pandas as pd
                                    df = pd.read_excel(download_path)
                                    print(f"  Excel shape: {df.shape}")
                                    
                                    # IP 컬럼 찾기
                                    for col in df.columns:
                                        if 'ip' in col.lower() or '주소' in col:
                                            for val in df[col].dropna():
                                                ip_str = str(val)
                                                ips = ip_pattern.findall(ip_str)
                                                for ip in ips:
                                                    if ip not in collected_ips:
                                                        collected_ips.append(ip)
                                                        print(f"  ✅ Found IP in Excel: {ip}")
                                except Exception as e:
                                    print(f"  Excel parsing error: {e}")
                        except Exception as e:
                            print(f"  Download error: {e}")
                
                # 페이지네이션 확인
                pagination = page.query_selector_all('a.page-link, button.page-link')
                if pagination and len(collected_ips) > 0:
                    print(f"  Found pagination with {len(pagination)} pages")
                    # 최대 5페이지까지만
                    for i in range(min(5, len(pagination))):
                        try:
                            pagination[i].click()
                            page.wait_for_timeout(1000)
                            # 위의 IP 수집 로직 반복...
                        except:
                            pass
                
            except Exception as e:
                print(f"  Error accessing {path}: {e}")
                continue
        
        # 3. 스크린샷 저장 (디버깅용)
        if len(collected_ips) == 0:
            screenshot_path = f"/home/jclee/app/blacklist/regtech_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            page.screenshot(path=screenshot_path)
            print(f"\n📸 Screenshot saved: {screenshot_path}")
        
        browser.close()
    
    # 결과
    print(f"\n{'='*60}")
    print(f"📊 총 {len(collected_ips)}개 IP 수집")
    
    if collected_ips:
        # 중복 제거
        unique_ips = list(set(collected_ips))
        print(f"   중복 제거 후: {len(unique_ips)}개")
        
        print("\n처음 10개 IP:")
        for i, ip in enumerate(unique_ips[:10], 1):
            print(f"  {i}. {ip}")
        
        # IP 데이터 형식 변환
        ip_data_list = []
        for ip in unique_ips:
            ip_data_list.append({
                "ip": ip,
                "source": "REGTECH",
                "description": "Malicious IP from browser automation",
                "detection_date": datetime.now().strftime('%Y-%m-%d'),
                "confidence": "high"
            })
        
        return ip_data_list
    
    return []


if __name__ == "__main__":
    print("🚀 REGTECH Browser Automation Collection")
    print("="*60)
    
    ips = collect_with_browser()
    
    if ips:
        print(f"\n✅ 성공! {len(ips)}개 실제 IP 수집")
        
        # PostgreSQL에 저장
        from src.core.data_storage_fixed import FixedDataStorage
        storage = FixedDataStorage()
        result = storage.store_ips(ips, "REGTECH")
        
        if result.get("success"):
            print(f"✅ PostgreSQL 저장 완료: {result.get('imported_count')}개")
        else:
            print(f"❌ 저장 실패: {result.get('error')}")
    else:
        print("\n❌ 브라우저 자동화로도 데이터를 찾을 수 없음")
        print("REGTECH 사이트에 실제로 데이터가 없거나 접근 권한이 없을 수 있습니다.")