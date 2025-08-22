#!/usr/bin/env python3
"""
REGTECH 쿠키 자동 추출 및 수집 시스템
"""

import time
import json
import os
from datetime import datetime


def extract_cookies_with_playwright():
    """Playwright로 쿠키 자동 추출"""
    try:
        from playwright.sync_api import sync_playwright

        print("🍪 Playwright로 REGTECH 쿠키 자동 추출...")

        with sync_playwright() as p:
            # 브라우저 실행
            browser = p.chromium.launch(
                headless=False
            )  # headless=False로 브라우저 화면 보기
            context = browser.new_context()
            page = context.new_page()

            # 1. 로그인 페이지 접속
            print("1️⃣ REGTECH 로그인 페이지 접속...")
            page.goto("https://regtech.fsec.or.kr/login/loginForm")
            page.wait_for_load_state("networkidle")

            # 2. 자동 로그인
            print("2️⃣ 자동 로그인 시도...")
            page.fill('input[name="loginID"]', "nextrade")
            page.fill('input[name="loginPW"]', "Sprtmxm1@3")

            # 로그인 버튼 클릭
            page.click('button[type="submit"], input[type="submit"]')
            page.wait_for_load_state("networkidle")

            # 3. 로그인 성공 확인
            current_url = page.url
            if "login" not in current_url.lower():
                print("✅ 로그인 성공!")

                # 4. 쿠키 추출
                print("3️⃣ 쿠키 추출...")
                cookies = context.cookies()

                important_cookies = {}
                for cookie in cookies:
                    if cookie["name"] in ["JSESSIONID", "regtech-front"]:
                        important_cookies[cookie["name"]] = cookie["value"]
                        print(f"   {cookie['name']}: {cookie['value']}")

                if important_cookies:
                    # 쿠키 문자열 생성
                    cookie_string = "; ".join(
                        [f"{name}={value}" for name, value in important_cookies.items()]
                    )

                    # 환경 변수에 설정
                    os.environ["REGTECH_COOKIES"] = cookie_string

                    # 파일에 저장
                    cookie_data = {
                        "cookies": important_cookies,
                        "cookie_string": cookie_string,
                        "extracted_at": datetime.now().isoformat(),
                        "url": current_url,
                    }

                    with open("regtech_cookies.json", "w") as f:
                        json.dump(cookie_data, f, indent=2)

                    print(f"✅ 쿠키 추출 완료: {len(important_cookies)}개")
                    print(f"💾 저장: regtech_cookies.json")

                    browser.close()
                    return cookie_string
                else:
                    print("❌ 중요한 쿠키를 찾을 수 없음")
            else:
                print("❌ 로그인 실패")

            browser.close()
            return None

    except ImportError:
        print(
            "❌ Playwright 설치 필요: pip install playwright && playwright install chromium"
        )
        return None
    except Exception as e:
        print(f"❌ 쿠키 추출 실패: {e}")
        return None


def extract_cookies_with_selenium():
    """Selenium으로 쿠키 자동 추출"""
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options

        print("🍪 Selenium으로 REGTECH 쿠키 자동 추출...")

        # Chrome 옵션
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=chrome_options)

        try:
            # 1. 로그인 페이지 접속
            print("1️⃣ REGTECH 로그인 페이지 접속...")
            driver.get("https://regtech.fsec.or.kr/login/loginForm")
            time.sleep(2)

            # 2. 자동 로그인
            print("2️⃣ 자동 로그인 시도...")
            driver.find_element(By.NAME, "loginID").send_keys("nextrade")
            driver.find_element(By.NAME, "loginPW").send_keys("Sprtmxm1@3")

            # 로그인 버튼 클릭
            driver.find_element(
                By.CSS_SELECTOR, 'button[type="submit"], input[type="submit"]'
            ).click()
            time.sleep(3)

            # 3. 로그인 성공 확인 및 쿠키 추출
            current_url = driver.current_url
            if "login" not in current_url.lower():
                print("✅ 로그인 성공!")

                print("3️⃣ 쿠키 추출...")
                cookies = driver.get_cookies()

                important_cookies = {}
                for cookie in cookies:
                    if cookie["name"] in ["JSESSIONID", "regtech-front"]:
                        important_cookies[cookie["name"]] = cookie["value"]
                        print(f"   {cookie['name']}: {cookie['value']}")

                if important_cookies:
                    cookie_string = "; ".join(
                        [f"{name}={value}" for name, value in important_cookies.items()]
                    )

                    # 파일에 저장
                    cookie_data = {
                        "cookies": important_cookies,
                        "cookie_string": cookie_string,
                        "extracted_at": datetime.now().isoformat(),
                        "method": "selenium",
                    }

                    with open("regtech_cookies_selenium.json", "w") as f:
                        json.dump(cookie_data, f, indent=2)

                    print(f"✅ 쿠키 추출 완료: {len(important_cookies)}개")
                    return cookie_string
            else:
                print("❌ 로그인 실패")

        finally:
            driver.quit()

    except ImportError:
        print("❌ Selenium 설치 필요: pip install selenium")
        return None
    except Exception as e:
        print(f"❌ 쿠키 추출 실패: {e}")
        return None


def use_extracted_cookies_for_collection(cookie_string):
    """추출된 쿠키로 데이터 수집"""
    if not cookie_string:
        print("❌ 쿠키가 없어서 수집 불가")
        return False

    print("\n4️⃣ 추출된 쿠키로 데이터 수집...")

    import requests

    try:
        # 1. 수집 활성화
        response = requests.post("http://localhost:32542/api/collection/enable")
        if response.status_code == 200:
            print("✅ 수집 활성화 완료")

        # 2. 쿠키 기반 수집 API 호출
        collection_data = {
            "cookies": cookie_string,
            "force": True,
            "start_date": "2025-08-12",
            "end_date": "2025-08-19",
        }

        response = requests.post(
            "http://localhost:32542/api/collection/regtech/trigger",
            json=collection_data,
        )

        print(f"수집 API 응답: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"결과: {result.get('message')}")
            return True
        else:
            print(f"응답: {response.text}")
            return False

    except Exception as e:
        print(f"❌ API 호출 실패: {e}")
        return False


def load_existing_cookies():
    """기존 저장된 쿠키 로드"""
    try:
        if os.path.exists("regtech_cookies.json"):
            with open("regtech_cookies.json", "r") as f:
                data = json.load(f)
                print(f"📂 기존 쿠키 로드: {data.get('extracted_at')}")
                return data.get("cookie_string")
    except:
        pass
    return None


def manual_cookie_input():
    """수동 쿠키 입력"""
    print("\n🖐️ 수동 쿠키 입력 모드")
    print("브라우저에서 직접 로그인 후 쿠키를 복사하세요:")
    print("1. https://regtech.fsec.or.kr/login/loginForm 로그인")
    print("2. F12 → Application → Cookies → regtech.fsec.or.kr")
    print("3. JSESSIONID와 regtech-front 값 복사")

    jsessionid = input("\nJSESSIONID 값 입력: ")
    regtech_front = input("regtech-front 값 입력: ")

    if jsessionid and regtech_front:
        cookie_string = f"JSESSIONID={jsessionid}; regtech-front={regtech_front}"

        # 저장
        cookie_data = {
            "cookies": {"JSESSIONID": jsessionid, "regtech-front": regtech_front},
            "cookie_string": cookie_string,
            "extracted_at": datetime.now().isoformat(),
            "method": "manual",
        }

        with open("regtech_cookies_manual.json", "w") as f:
            json.dump(cookie_data, f, indent=2)

        print("✅ 쿠키 저장 완료")
        return cookie_string

    return None


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("🍪 REGTECH 쿠키 자동 추출 및 수집")
    print("=" * 60)

    cookie_string = None

    # 1. 기존 쿠키 확인
    cookie_string = load_existing_cookies()

    if not cookie_string:
        print("\n추출 방법을 선택하세요:")
        print("1. Playwright 자동 추출 (권장)")
        print("2. Selenium 자동 추출")
        print("3. 수동 입력")

        choice = input("\n선택 (1-3): ").strip()

        if choice == "1":
            cookie_string = extract_cookies_with_playwright()
        elif choice == "2":
            cookie_string = extract_cookies_with_selenium()
        elif choice == "3":
            cookie_string = manual_cookie_input()
        else:
            print("❌ 잘못된 선택")
            return

    # 2. 추출된 쿠키로 수집 실행
    if cookie_string:
        success = use_extracted_cookies_for_collection(cookie_string)

        if success:
            print("\n✅ 전체 프로세스 완료!")
            print("📊 대시보드 확인: http://localhost:32542/")
        else:
            print("\n⚠️ 수집 단계에서 문제 발생")
    else:
        print("\n❌ 쿠키 추출 실패")


if __name__ == "__main__":
    main()
