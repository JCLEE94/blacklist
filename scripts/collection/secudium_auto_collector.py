#!/usr/bin/env python3
"""
SECUDIUM 자동 수집기 - OTP 문제 해결 시도
다양한 자동화 방법 시도
"""
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
import json
import time
import logging

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

class SECUDIUMAutoCollector:
    """SECUDIUM 자동 수집기"""
    
    def __init__(self):
        self.base_url = "https://secudium.skinfosec.co.kr"
        self.username = os.getenv('BLACKLIST_USERNAME', 'nextrade')
        self.password = os.getenv('BLACKLIST_PASSWORD', 'Sprtmxm1@3')
        self.download_dir = Path("data/downloads/secudium")
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
    async def try_browser_automation(self):
        """브라우저 자동화로 시도 (OTP 대기 포함)"""
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                # 헤드있는 브라우저로 시작 (OTP 입력 위해)
                browser = await p.chromium.launch(
                    headless=False,  # OTP 입력을 위해 헤드있게
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
                
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                
                page = await context.new_page()
                
                print("🌐 SECUDIUM 로그인 페이지 접속...")
                await page.goto(f"{self.base_url}/member/login.jsp", wait_until='networkidle')
                
                # 로그인 폼 입력
                print("👤 로그인 정보 입력...")
                await page.fill('input[name="loginId"]', self.username)
                await page.fill('input[name="password"]', self.password)
                
                # 로그인 버튼 클릭
                await page.click('button[type="submit"], input[type="submit"]')
                
                # OTP 페이지 대기
                print("📱 OTP 입력 페이지 대기 중...")
                try:
                    await page.wait_for_selector('input[name*="otp"], input[id*="otp"]', timeout=10000)
                    print("⏰ OTP 입력이 필요합니다!")
                    print("📱 휴대폰으로 받은 OTP를 브라우저에 입력해주세요.")
                    print("⏳ 5분 동안 대기합니다...")
                    
                    # OTP 입력 완료까지 대기 (최대 5분)
                    for i in range(300):  # 5분 = 300초
                        try:
                            # 로그인 완료 후 페이지가 변경되었는지 확인
                            current_url = page.url
                            if 'login' not in current_url.lower():
                                print("✅ 로그인 성공!")
                                break
                            
                            await asyncio.sleep(1)
                            
                            if i % 30 == 0:  # 30초마다 알림
                                remaining = (300 - i) // 60
                                print(f"⏳ 남은 시간: {remaining}분...")
                                
                        except:
                            pass
                    else:
                        print("❌ OTP 입력 시간 초과")
                        await browser.close()
                        return None
                
                except:
                    # OTP 없이 바로 로그인된 경우도 있을 수 있음
                    print("🔍 로그인 상태 확인 중...")
                    await page.wait_for_timeout(3000)
                
                # 블랙리스트 페이지로 이동
                print("📋 블랙리스트 페이지로 이동...")
                
                # 다양한 메뉴 링크 시도
                menu_selectors = [
                    'a:has-text("블랙리스트")',
                    'a:has-text("blacklist")',
                    'a[href*="blacklist"]',
                    'a[href*="threat"]',
                    'a[href*="malware"]'
                ]
                
                menu_found = False
                for selector in menu_selectors:
                    try:
                        menu = page.locator(selector).first
                        if await menu.count() > 0:
                            await menu.click()
                            menu_found = True
                            print(f"✅ 메뉴 발견: {selector}")
                            break
                    except:
                        continue
                
                if not menu_found:
                    # 직접 URL 시도
                    blacklist_urls = [
                        f"{self.base_url}/blacklist/list.jsp",
                        f"{self.base_url}/threat/blacklist.jsp",
                        f"{self.base_url}/data/blacklist.jsp"
                    ]
                    
                    for url in blacklist_urls:
                        try:
                            await page.goto(url, wait_until='networkidle')
                            if page.url != url:  # 리다이렉트되지 않았다면
                                continue
                            print(f"✅ 블랙리스트 페이지 접근: {url}")
                            menu_found = True
                            break
                        except:
                            continue
                
                if not menu_found:
                    print("⚠️ 블랙리스트 메뉴를 찾을 수 없음")
                    print("🔍 사용 가능한 메뉴 분석 중...")
                    
                    # 모든 링크 분석
                    links = await page.locator('a').all()
                    print(f"발견된 링크 수: {len(links)}")
                    
                    for i, link in enumerate(links[:20]):  # 최대 20개만
                        try:
                            text = await link.inner_text()
                            href = await link.get_attribute('href')
                            if text and href:
                                print(f"  링크 {i}: {text} -> {href}")
                        except:
                            pass
                
                await page.wait_for_timeout(2000)
                
                # 엑셀 다운로드 버튼 찾기
                print("📥 엑셀 다운로드 버튼 찾는 중...")
                
                download_selectors = [
                    'button:has-text("엑셀")',
                    'button:has-text("Excel")',
                    'button:has-text("다운로드")',
                    'a:has-text("엑셀")',
                    'input[value*="엑셀"]',
                    'button[onclick*="excel"]'
                ]
                
                download_found = False
                for selector in download_selectors:
                    try:
                        download_btn = page.locator(selector).first
                        if await download_btn.count() > 0:
                            print(f"✅ 다운로드 버튼 발견: {selector}")
                            
                            # 다운로드 시작
                            async with page.expect_download() as download_info:
                                await download_btn.click()
                                download_found = True
                                break
                    except:
                        continue
                
                if download_found:
                    download = await download_info.value
                    
                    # 파일 저장
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"SECUDIUM_블랙리스트_{timestamp}.xlsx"
                    filepath = self.download_dir / filename
                    
                    await download.save_as(filepath)
                    
                    print(f"✅ 다운로드 성공!")
                    print(f"📁 저장 위치: {filepath}")
                    
                    await browser.close()
                    return str(filepath)
                else:
                    print("❌ 다운로드 버튼을 찾을 수 없음")
                    print("💡 수동으로 다운로드 버튼을 클릭해주세요.")
                    print("⏳ 30초 동안 대기합니다...")
                    
                    # 사용자가 수동으로 다운로드할 시간 제공
                    await page.wait_for_timeout(30000)
                
                await browser.close()
                return None
                
        except ImportError:
            print("❌ Playwright가 설치되지 않음")
            print("설치 명령어: pip install playwright && playwright install chromium")
            return None
        except Exception as e:
            print(f"❌ 브라우저 자동화 실패: {e}")
            logger.error(f"SECUDIUM 브라우저 자동화 오류: {e}")
            return None
    
    def try_api_request(self):
        """API 요청으로 시도 (제한적)"""
        print("🔄 API 요청 시도...")
        
        import requests
        
        session = requests.Session()
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json'
        }
        
        try:
            # 로그인 시도
            login_data = {
                'loginId': self.username,
                'password': self.password
            }
            
            login_response = session.post(
                f"{self.base_url}/api/auth/login",
                json=login_data,
                headers=headers
            )
            
            print(f"로그인 응답: {login_response.status_code}")
            
            if login_response.status_code == 200:
                # API 토큰이 있다면 블랙리스트 데이터 요청
                blacklist_response = session.get(
                    f"{self.base_url}/api/blacklist/export",
                    headers=headers
                )
                
                print(f"블랙리스트 응답: {blacklist_response.status_code}")
                
                if blacklist_response.status_code == 200:
                    # 데이터 저장
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"SECUDIUM_API_{timestamp}.json"
                    filepath = self.download_dir / filename
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(blacklist_response.json(), f, ensure_ascii=False, indent=2)
                    
                    print(f"✅ API 데이터 저장: {filepath}")
                    return str(filepath)
            
            print("❌ API 요청 실패 (OTP 또는 인증 문제)")
            return None
            
        except Exception as e:
            print(f"❌ API 요청 오류: {e}")
            return None

async def main():
    """메인 실행 함수"""
    collector = SECUDIUMAutoCollector()
    
    print("🚀 SECUDIUM 자동 수집 시작")
    print("="*50)
    print("⚠️ 주의: SMS OTP 인증이 필요할 수 있습니다.")
    print()
    
    # 1. 브라우저 자동화 시도 (OTP 포함)
    filepath = await collector.try_browser_automation()
    
    # 2. 실패 시 API 시도
    if not filepath:
        print("\n🔄 브라우저 자동화 실패, API 시도...")
        filepath = collector.try_api_request()
    
    # 3. 결과 처리
    if filepath and os.path.exists(filepath):
        print(f"\n✅ 수집 성공!")
        print(f"📁 파일: {filepath}")
        
        # 파일 분석
        try:
            if filepath.endswith('.xlsx'):
                import pandas as pd
                df = pd.read_excel(filepath)
                print(f"📊 엑셀 데이터 분석:")
                print(f"  - 행 수: {len(df)}")
                print(f"  - 컬럼: {df.columns.tolist()}")
            elif filepath.endswith('.json'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"📊 JSON 데이터 분석:")
                print(f"  - 키: {list(data.keys()) if isinstance(data, dict) else 'Array'}")
        except Exception as e:
            print(f"⚠️ 파일 분석 실패: {e}")
        
        print(f"\n다음 명령어로 시스템에 임포트:")
        print(f"python3 scripts/import_secudium_excel.py '{filepath}'")
        
    else:
        print("\n❌ 자동 수집 실패")
        print("수동 다운로드 필요:")
        print("1. https://secudium.skinfosec.co.kr")
        print("2. ID/PW: nextrade/Sprtmxm1@3")
        print("3. SMS OTP 입력")
        print("4. 블랙리스트 메뉴 → 엑셀 다운로드")

if __name__ == "__main__":
    asyncio.run(main())