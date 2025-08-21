#!/usr/bin/env python3
"""
REGTECH 브라우저 자동화를 통한 실제 데이터 수집
Selenium 또는 Playwright를 사용한 웹 자동화
"""

import json
import os
import time
from datetime import datetime, timedelta


def test_with_playwright():
    """Playwright를 사용한 REGTECH 로그인 및 데이터 수집"""
    try:
        from playwright.sync_api import sync_playwright

        print("=" * 60)
        print("REGTECH 브라우저 자동화 테스트 (Playwright)")
        print("=" * 60)

        with sync_playwright() as p:
            # 브라우저 실행 (headless=False로 실제 브라우저 확인 가능)
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            )
            page = context.new_page()

            # 1. 로그인 페이지 접속
            print("\n1️⃣ 로그인 페이지 접속...")
            page.goto("https://regtech.fsec.or.kr/login/loginForm")
            page.wait_for_load_state("networkidle")

            # 스크린샷 저장
            page.screenshot(path="docs/regtech_login_page.png")
            print("   📸 스크린샷: docs/regtech_login_page.png")

            # 2. 로그인 정보 입력
            print("\n2️⃣ 로그인 정보 입력...")

            # ID 입력
            page.fill('input[name="loginID"]', "nextrade")
            print("   ✅ ID 입력: nextrade")

            # 비밀번호 입력
            page.fill('input[name="loginPW"]', "Sprtmxm1@3")
            print("   ✅ 비밀번호 입력: ********")

            # 스크린샷
            page.screenshot(path="docs/regtech_login_filled.png")
            print("   📸 스크린샷: docs/regtech_login_filled.png")

            # 3. 로그인 버튼 클릭
            print("\n3️⃣ 로그인 시도...")

            # 로그인 버튼 찾기 및 클릭
            login_button = (
                page.locator('button[type="submit"]')
                .or_(page.locator('input[type="submit"]'))
                .or_(page.locator('button:has-text("로그인")'))
            )
            login_button.click()

            # 페이지 로드 대기
            page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(2)

            # 로그인 후 URL 확인
            current_url = page.url
            print(f"   현재 URL: {current_url}")

            # 스크린샷
            page.screenshot(path="docs/regtech_after_login.png")
            print("   📸 스크린샷: docs/regtech_after_login.png")

            # 로그인 성공 여부 확인
            if "login" not in current_url.lower():
                print("   ✅ 로그인 성공!")

                # 4. 블랙리스트 페이지 이동
                print("\n4️⃣ 블랙리스트 페이지 찾기...")

                # 메뉴에서 블랙리스트 관련 링크 찾기
                blacklist_links = [
                    'a:has-text("악성IP")',
                    'a:has-text("블랙리스트")',
                    'a:has-text("차단")',
                    'a[href*="blacklist"]',
                    'a[href*="HPHB0620101"]',
                ]

                for selector in blacklist_links:
                    try:
                        link = page.locator(selector).first
                        if link.is_visible():
                            print(f"   📌 링크 발견: {selector}")
                            link.click()
                            page.wait_for_load_state("networkidle")
                            break
                    except:
                        continue

                # 현재 페이지 스크린샷
                page.screenshot(path="docs/regtech_blacklist_page.png")
                print("   📸 스크린샷: docs/regtech_blacklist_page.png")

                # 5. 데이터 추출
                print("\n5️⃣ 데이터 추출...")

                # 테이블 또는 IP 목록 찾기
                ip_pattern = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
                page_content = page.content()

                import re

                ips = re.findall(ip_pattern, page_content)
                unique_ips = list(set(ips))

                if unique_ips:
                    print(f"   ✅ {len(unique_ips)}개 고유 IP 발견")

                    # 데이터 저장
                    data = {
                        "source": "REGTECH",
                        "collected_at": datetime.now().isoformat(),
                        "total_ips": len(unique_ips),
                        "ips": unique_ips[:100],  # 처음 100개만
                    }

                    with open(
                        "regtech_collected_data.json", "w", encoding="utf-8"
                    ) as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)

                    print(f"   💾 데이터 저장: regtech_collected_data.json")
                    print(f"\n   샘플 IP (처음 5개):")
                    for ip in unique_ips[:5]:
                        print(f"     • {ip}")
                else:
                    print("   ⚠️ IP 데이터를 찾을 수 없음")

                    # 다운로드 버튼 찾기
                    download_button = page.locator('button:has-text("다운로드")').or_(
                        page.locator('a:has-text("엑셀")')
                    )
                    if download_button.is_visible():
                        print("   📥 다운로드 버튼 발견")

            else:
                print("   ❌ 로그인 실패")

                # 에러 메시지 확인
                error_messages = page.locator(
                    '.error, .alert, .warning, [class*="error"], [class*="alert"]'
                )
                if error_messages.count() > 0:
                    error_text = error_messages.first.text_content()
                    print(f"   오류 메시지: {error_text}")

            browser.close()

    except ImportError:
        print("❌ Playwright가 설치되지 않음")
        print("설치 명령: pip install playwright && playwright install chromium")
        return False
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False

    return True


def test_with_selenium():
    """Selenium을 사용한 대체 방법"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        print("=" * 60)
        print("REGTECH 브라우저 자동화 테스트 (Selenium)")
        print("=" * 60)

        # Chrome 옵션 설정
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=chrome_options)

        try:
            # 1. 로그인 페이지 접속
            print("\n1️⃣ 로그인 페이지 접속...")
            driver.get("https://regtech.fsec.or.kr/login/loginForm")
            time.sleep(2)

            # 2. 로그인 정보 입력
            print("\n2️⃣ 로그인 정보 입력...")

            # ID 입력
            id_input = driver.find_element(By.NAME, "loginID")
            id_input.send_keys("nextrade")

            # 비밀번호 입력
            pw_input = driver.find_element(By.NAME, "loginPW")
            pw_input.send_keys("Sprtmxm1@3")

            # 3. 로그인 버튼 클릭
            print("\n3️⃣ 로그인 시도...")
            login_btn = driver.find_element(
                By.CSS_SELECTOR, 'button[type="submit"], input[type="submit"]'
            )
            login_btn.click()

            time.sleep(3)

            # 로그인 성공 확인
            current_url = driver.current_url
            print(f"   현재 URL: {current_url}")

            if "login" not in current_url.lower():
                print("   ✅ 로그인 성공!")

                # 페이지 소스에서 IP 추출
                page_source = driver.page_source
                import re

                ip_pattern = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
                ips = re.findall(ip_pattern, page_source)
                unique_ips = list(set(ips))

                if unique_ips:
                    print(f"   ✅ {len(unique_ips)}개 고유 IP 발견")
            else:
                print("   ❌ 로그인 실패")

        finally:
            driver.quit()

    except ImportError:
        print("❌ Selenium이 설치되지 않음")
        print("설치 명령: pip install selenium")
        return False
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False

    return True


def main():
    """메인 실행 함수"""

    # Playwright 시도
    success = test_with_playwright()

    if not success:
        print("\n" + "=" * 60)
        print("Playwright 실패, Selenium 시도...")
        print("=" * 60)

        # Selenium 시도
        success = test_with_selenium()

    if success:
        print("\n" + "=" * 60)
        print("✅ 테스트 완료")
        print("=" * 60)

        # 수집된 데이터 확인
        if os.path.exists("regtech_collected_data.json"):
            with open("regtech_collected_data.json", "r") as f:
                data = json.load(f)
                print(f"\n📊 수집 결과:")
                print(f"   - 총 IP 수: {data.get('total_ips', 0)}")
                print(f"   - 수집 시간: {data.get('collected_at', 'N/A')}")
    else:
        print("\n" + "=" * 60)
        print("❌ 모든 방법 실패")
        print("=" * 60)
        print("\n필요한 패키지 설치:")
        print("pip install playwright && playwright install chromium")
        print("또는")
        print("pip install selenium webdriver-manager")


if __name__ == "__main__":
    main()
