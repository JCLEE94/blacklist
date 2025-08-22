#!/usr/bin/env python3
"""
REGTECH 브라우저 자동화 모듈
쿠키 추출을 위한 Playwright 및 Selenium 브라우저 자동화
"""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class RegtechBrowserAutomation:
    """
    REGTECH 쿠키 추출을 위한 브라우저 자동화 클래스
    Playwright 우선, Selenium fallback 지원
    """

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.username = username
        self.password = password

    def extract_cookies_with_playwright(self) -> str:
        """Playwright로 자동 쿠키 추출"""
        try:
            from playwright.sync_api import sync_playwright

            logger.info("🍪 Extracting cookies with Playwright...")

            with sync_playwright() as p:
                # 브라우저 실행 (headless 모드)
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()

                # 1. 로그인 페이지 접속
                logger.info("Accessing REGTECH login page...")
                page.goto(f"{self.base_url}/login/loginForm")
                page.wait_for_load_state("networkidle")

                # 2. 자동 로그인
                logger.info("Attempting automatic login...")
                page.fill('input[name="loginID"]', self.username)
                page.fill('input[name="loginPW"]', self.password)

                # 로그인 버튼 클릭
                page.click('button[type="submit"], input[type="submit"]')
                page.wait_for_load_state("networkidle")

                # 3. 로그인 성공 확인
                current_url = page.url
                if "login" not in current_url.lower():
                    logger.info("✅ Login successful!")

                    # 4. 쿠키 추출
                    logger.info("Extracting cookies...")
                    cookies = context.cookies()

                    important_cookies = {}
                    for cookie in cookies:
                        if cookie["name"] in ["JSESSIONID", "regtech-front"]:
                            important_cookies[cookie["name"]] = cookie["value"]

                    if important_cookies:
                        cookie_string = "; ".join(
                            [
                                f"{name}={value}"
                                for name, value in important_cookies.items()
                            ]
                        )

                        browser.close()
                        logger.info(
                            f"✅ Cookies extracted successfully: {len(important_cookies)} cookies"
                        )
                        return cookie_string
                    else:
                        logger.warning("❌ No important cookies found")
                else:
                    logger.warning("❌ Login failed - still on login page")

                browser.close()
                return ""

        except ImportError:
            logger.warning(
                "Playwright not available - install with: pip install playwright && playwright install chromium"
            )
            return ""
        except Exception as e:
            logger.error(f"Cookie extraction with Playwright failed: {e}")
            return ""

    def extract_cookies_with_selenium(self) -> str:
        """Selenium으로 자동 쿠키 추출 (fallback)"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By

            logger.info("🍪 Extracting cookies with Selenium...")

            # Chrome 옵션 (headless)
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")

            driver = webdriver.Chrome(options=chrome_options)

            try:
                # 1. 로그인 페이지 접속
                logger.info("Accessing REGTECH login page...")
                driver.get(f"{self.base_url}/login/loginForm")
                time.sleep(2)

                # 2. 자동 로그인
                logger.info("Attempting automatic login...")
                driver.find_element(By.NAME, "loginID").send_keys(self.username)
                driver.find_element(By.NAME, "loginPW").send_keys(self.password)

                # 로그인 버튼 클릭
                driver.find_element(
                    By.CSS_SELECTOR, 'button[type="submit"], input[type="submit"]'
                ).click()
                time.sleep(3)

                # 3. 로그인 성공 확인 및 쿠키 추출
                current_url = driver.current_url
                if "login" not in current_url.lower():
                    logger.info("✅ Login successful!")

                    logger.info("Extracting cookies...")
                    cookies = driver.get_cookies()

                    important_cookies = {}
                    for cookie in cookies:
                        if cookie["name"] in ["JSESSIONID", "regtech-front"]:
                            important_cookies[cookie["name"]] = cookie["value"]

                    if important_cookies:
                        cookie_string = "; ".join(
                            [
                                f"{name}={value}"
                                for name, value in important_cookies.items()
                            ]
                        )
                        logger.info(
                            f"✅ Cookies extracted successfully: {len(important_cookies)} cookies"
                        )
                        return cookie_string
                else:
                    logger.warning("❌ Login failed - still on login page")

            finally:
                driver.quit()

        except ImportError:
            logger.warning(
                "Selenium not available - install with: pip install selenium"
            )
            return ""
        except Exception as e:
            logger.error(f"Cookie extraction with Selenium failed: {e}")
            return ""

        return ""

    def auto_extract_cookies(self) -> Optional[str]:
        """자동 쿠키 추출 (Playwright 우선, Selenium fallback)"""
        if not self.username or not self.password:
            logger.warning("Username or password not provided for cookie extraction")
            return None

        logger.info("🔄 Attempting automatic cookie extraction...")

        # 1. Playwright 시도
        cookie_string = self.extract_cookies_with_playwright()

        # 2. Playwright 실패 시 Selenium 시도
        if not cookie_string:
            logger.info("Playwright failed, trying Selenium...")
            cookie_string = self.extract_cookies_with_selenium()

        if cookie_string:
            logger.info("✅ Automatic cookie extraction successful")
            return cookie_string
        else:
            logger.error("❌ All cookie extraction methods failed")
            return None


if __name__ == "__main__":
    # 브라우저 자동화 테스트
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: 기본 브라우저 자동화 객체 생성
    total_tests += 1
    try:
        browser_automation = RegtechBrowserAutomation(
            "https://regtech.fsec.or.kr", "test_user", "test_pass"
        )
        if not hasattr(browser_automation, "base_url"):
            all_validation_failures.append("기본 속성 누락")
    except Exception as e:
        all_validation_failures.append(f"브라우저 자동화 객체 생성 실패: {e}")

    # Test 2: 메서드 존재 확인
    total_tests += 1
    try:
        browser_automation = RegtechBrowserAutomation(
            "https://regtech.fsec.or.kr", "test_user", "test_pass"
        )
        required_methods = [
            "extract_cookies_with_playwright",
            "extract_cookies_with_selenium",
            "auto_extract_cookies",
        ]
        for method_name in required_methods:
            if not hasattr(browser_automation, method_name):
                all_validation_failures.append(f"필수 메서드 누락: {method_name}")
    except Exception as e:
        all_validation_failures.append(f"메서드 확인 테스트 실패: {e}")

    # Test 3: 자격증명 없이 추출 시 None 반환 확인
    total_tests += 1
    try:
        browser_automation = RegtechBrowserAutomation(
            "https://regtech.fsec.or.kr", None, None
        )
        result = browser_automation.auto_extract_cookies()
        if result is not None:
            all_validation_failures.append("자격증명 없이도 결과 반환됨")
    except Exception as e:
        all_validation_failures.append(f"자격증명 테스트 실패: {e}")

    # 최종 검증 결과
    if all_validation_failures:
        print(
            f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print("RegtechBrowserAutomation module is validated and ready for use")
        sys.exit(0)
