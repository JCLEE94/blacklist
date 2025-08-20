#!/usr/bin/env python3
"""
Fixed REGTECH Authentication Module
Based on analysis of the actual login form structure
"""

import logging
import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class FixedRegtechAuth:
    """
    Fixed REGTECH authentication class with correct form handling
    """

    def __init__(self, base_url: str, username: str, password: str, timeout: int = 30):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.timeout = timeout
        self.session = None
        self.authenticated = False

    def create_session(self) -> requests.Session:
        """Create new session with proper headers"""
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/91.0.4472.124 Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;"
                    "q=0.9,image/webp,*/*;q=0.8"
                ),
                "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )
        return session

    def login(self) -> Optional[requests.Session]:
        """
        Perform REGTECH login with fixed form handling

        Returns:
            requests.Session: Authenticated session or None
        """
        try:
            # Create new session
            self.session = self.create_session()

            # Step 1: Get login page
            login_url = f"{self.base_url}/login/loginForm"
            logger.info(f"Accessing login page: {login_url}")

            response = self.session.get(login_url, timeout=self.timeout, verify=False)
            response.raise_for_status()

            # Step 2: Parse login form
            soup = BeautifulSoup(response.text, "html.parser")

            # Find the login form (Form #4 from analysis)
            login_form = None
            forms = soup.find_all("form")

            for form in forms:
                # Look for form with username and password fields
                username_field = form.find("input", {"name": "username"})
                password_field = form.find("input", {"type": "password"})

                if username_field and password_field:
                    login_form = form
                    break

            if not login_form:
                logger.error("Login form with username/password fields not found")
                return None

            # Step 3: Prepare login data
            login_data = {"username": self.username, "password": self.password}

            # Add any hidden fields from the form
            hidden_fields = login_form.find_all("input", {"type": "hidden"})
            for field in hidden_fields:
                name = field.get("name")
                value = field.get("value", "")
                if name:
                    login_data[name] = value
                    logger.debug(f"Added hidden field: {name} = {value}")

            # Step 4: Determine form action
            action = login_form.get("action")
            if not action:
                # Try to submit to the same page
                action = "/login/loginForm"

            if not action.startswith("http"):
                action = f"{self.base_url}{action}"

            logger.info(f"Submitting login to: {action}")
            logger.info(f"Login data fields: {list(login_data.keys())}")

            # Step 5: Submit login form
            method = login_form.get("method", "post").lower()
            if method == "post":
                response = self.session.post(
                    action,
                    data=login_data,
                    timeout=self.timeout,
                    verify=False,
                    allow_redirects=True,
                )
            else:
                response = self.session.get(
                    action,
                    params=login_data,
                    timeout=self.timeout,
                    verify=False,
                    allow_redirects=True,
                )

            logger.info(f"Login response status: {response.status_code}")
            logger.info(f"Final URL: {response.url}")

            # Step 6: Verify login success
            if self._verify_login_success(response):
                logger.info("✅ REGTECH login successful")
                self.authenticated = True
                return self.session
            else:
                logger.error("❌ REGTECH login failed")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during REGTECH login: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during REGTECH login: {e}")
            return None

    def _verify_login_success(self, response: requests.Response) -> bool:
        """Verify login success with multiple indicators"""

        # Method 1: Check URL - successful login should redirect away from login
        if "/login" not in response.url.lower():
            logger.info("Login success indicator: Redirected away from login page")
            return True

        # Method 2: Check for logout link or main page elements
        response_text = response.text.lower()
        success_indicators = [
            "로그아웃",
            "logout",
            "대시보드",
            "dashboard",
            "메인",
            "main",
            "마이페이지",
            "mypage",
        ]

        for indicator in success_indicators:
            if indicator in response_text:
                logger.info(f"Login success indicator: Found '{indicator}' in response")
                return True

        # Method 3: Check for absence of login failure messages
        failure_indicators = [
            "로그인 실패",
            "login failed",
            "잘못된 사용자",
            "invalid credentials",
            "비밀번호가 올바르지 않습니다",
            "아이디 또는 비밀번호",
            "id or password",
        ]

        has_failure = False
        for indicator in failure_indicators:
            if indicator in response_text:
                logger.warning(
                    f"Login failure indicator: Found '{indicator}' in response"
                )
                has_failure = True
                break

        if not has_failure:
            logger.info("Login success indicator: No failure messages found")
            return True

        return False

    def test_authenticated_access(self) -> bool:
        """Test if we can access protected resources"""
        if not self.session or not self.authenticated:
            return False

        try:
            # Try to access main page or dashboard
            test_urls = [
                f"{self.base_url}/main",
                f"{self.base_url}/dashboard",
                f"{self.base_url}/board/boardList?menuCode=HPHB0620101",  # Blacklist board
            ]

            for test_url in test_urls:
                try:
                    response = self.session.get(
                        test_url, timeout=self.timeout, verify=False
                    )
                    if (
                        response.status_code == 200
                        and "/login" not in response.url.lower()
                    ):
                        logger.info(f"✅ Authenticated access confirmed: {test_url}")
                        return True
                except Exception:
                    continue

            return False

        except Exception as e:
            logger.error(f"Error testing authenticated access: {e}")
            return False

    def logout(self) -> bool:
        """Logout from REGTECH"""
        if not self.session:
            return True

        try:
            logout_url = f"{self.base_url}/logout"
            response = self.session.get(logout_url, timeout=self.timeout, verify=False)

            logger.info("REGTECH logout completed")
            self.authenticated = False
            return True

        except Exception as e:
            logger.warning(f"Logout failed (non-critical): {e}")
            return False
        finally:
            if self.session:
                self.session.close()
                self.session = None


if __name__ == "__main__":
    """Test the fixed authentication"""
    import os
    import sys

    from dotenv import load_dotenv

    all_validation_failures = []
    total_tests = 0

    load_dotenv()

    username = os.getenv("REGTECH_USERNAME")
    password = os.getenv("REGTECH_PASSWORD")
    base_url = "https://regtech.fsec.or.kr"

    if not username or not password:
        print("❌ REGTECH credentials not set in environment")
        sys.exit(1)

    # Test 1: Basic authentication
    total_tests += 1
    try:
        auth = FixedRegtechAuth(base_url, username, password)
        session = auth.login()
        if not session:
            all_validation_failures.append(
                "Authentication failed - no session returned"
            )
    except Exception as e:
        all_validation_failures.append(f"Authentication test failed: {e}")

    # Test 2: Authenticated access test
    total_tests += 1
    try:
        if session:
            access_confirmed = auth.test_authenticated_access()
            if not access_confirmed:
                all_validation_failures.append("Authenticated access test failed")
        else:
            all_validation_failures.append(
                "Cannot test authenticated access - no session"
            )
    except Exception as e:
        all_validation_failures.append(f"Authenticated access test error: {e}")

    # Test 3: Logout test
    total_tests += 1
    try:
        if session:
            logout_success = auth.logout()
            if not logout_success:
                all_validation_failures.append("Logout failed")
    except Exception as e:
        all_validation_failures.append(f"Logout test error: {e}")

    # Final validation result
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
        print("Fixed REGTECH authentication is validated and ready for use")
        sys.exit(0)
