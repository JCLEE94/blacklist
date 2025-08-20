#!/usr/bin/env python3
"""
REGTECH Authentication Module
Provides authentication and session management for REGTECH collector

Third-party packages:
- requests: https://docs.python-requests.org/
- bs4: https://www.crummy.com/software/BeautifulSoup/

Sample input: username, password credentials
Expected output: authenticated session, login status
"""

import logging
import os
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class AuthenticationManager:
    """Manages REGTECH authentication and session lifecycle"""

    def __init__(self, username: str = None, password: str = None):
        self.base_url = "https://regtech.fsec.or.kr"
        self.username = username or os.getenv("REGTECH_USERNAME")
        self.password = password or os.getenv("REGTECH_PASSWORD")
        self.session = None
        self.authenticated = False
        self.timeout = 30

        if not self.username or not self.password:
            raise ValueError("REGTECH credentials not provided")

    def create_session(self) -> requests.Session:
        """Create session with proper headers"""
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/91.0.4472.124 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )
        return session

    def authenticate(self) -> bool:
        """Authenticate with REGTECH system"""
        try:
            logger.info("🔑 Starting REGTECH authentication...")
            
            # Create new session
            self.session = self.create_session()
            
            # Step 1: Get login page
            logger.info("🌍 Getting login page...")
            login_page_resp = self.session.get(
                f"{self.base_url}/login", timeout=self.timeout
            )
            
            if login_page_resp.status_code != 200:
                logger.error(f"Failed to get login page: {login_page_resp.status_code}")
                return False

            # Parse login page for tokens or hidden fields
            soup = BeautifulSoup(login_page_resp.text, "html.parser")
            
            # Step 2: Perform login
            logger.info("🔑 Performing actual login...")
            login_form_data = {
                "username": self.username,
                "password": self.password,
                "login_error": "",
                "txId": "",
                "token": "",
                "memberId": "",
                "smsTimeExcess": "N",
            }

            login_resp = self.session.post(
                f"{self.base_url}/login/addLogin",
                data=login_form_data,
                timeout=self.timeout,
                allow_redirects=True,
            )

            # Check login success
            if login_resp.status_code == 200 and "main" in login_resp.url:
                if "logout" in login_resp.text.lower() or "로그아웃" in login_resp.text:
                    logger.info("✅ REGTECH authentication successful!")
                    self.authenticated = True
                    return True

            logger.error(
                "❌ REGTECH authentication failed - redirect or content check failed"
            )
            logger.debug(f"Response URL: {login_resp.url}")
            logger.debug(f"Response status: {login_resp.status_code}")
            return False

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    def check_login_success(self, response: requests.Response) -> bool:
        """Check if login was successful"""
        text = response.text.lower()

        # Success indicators
        success_indicators = ["로그아웃", "logout", "대시보드", "main"]
        for indicator in success_indicators:
            if indicator in text:
                return True

        # Failure indicators
        failure_indicators = ["로그인 실패", "login failed", "잘못된", "invalid"]
        for indicator in failure_indicators:
            if indicator in text:
                return False

        # If redirected away from login, assume success
        return "/login" not in response.url.lower()

    def is_authenticated(self) -> bool:
        """Check if session is authenticated"""
        return self.authenticated and self.session is not None

    def get_session(self) -> Optional[requests.Session]:
        """Get the authenticated session"""
        if self.is_authenticated():
            return self.session
        return None

    def logout(self) -> bool:
        """Logout from REGTECH system"""
        try:
            if not self.session:
                return True

            logout_resp = self.session.get(
                f"{self.base_url}/login/logout", timeout=self.timeout
            )
            
            self.authenticated = False
            self.session = None
            
            logger.info("🚪 REGTECH logout completed")
            return logout_resp.status_code == 200

        except Exception as e:
            logger.error(f"Logout error: {e}")
            self.authenticated = False
            self.session = None
            return False

    def refresh_session(self) -> bool:
        """Refresh authentication session"""
        logger.info("🔄 Refreshing REGTECH session...")
        self.logout()
        return self.authenticate()

    def test_connection(self) -> bool:
        """Test connection to REGTECH system"""
        try:
            test_session = self.create_session()
            response = test_session.get(f"{self.base_url}/login", timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def get_csrf_token(self, page_content: str) -> Optional[str]:
        """Extract CSRF token from page content"""
        try:
            soup = BeautifulSoup(page_content, "html.parser")
            
            # Look for common CSRF token patterns
            csrf_inputs = soup.find_all("input", {"name": ["_token", "csrf_token", "authenticity_token"]})
            for csrf_input in csrf_inputs:
                if csrf_input.get("value"):
                    return csrf_input.get("value")
            
            # Look for meta tags
            csrf_meta = soup.find("meta", {"name": ["csrf-token", "_token"]})
            if csrf_meta and csrf_meta.get("content"):
                return csrf_meta.get("content")
            
            return None
            
        except Exception as e:
            logger.debug(f"CSRF token extraction failed: {e}")
            return None

    def get_session_info(self) -> dict:
        """Get current session information"""
        return {
            "authenticated": self.authenticated,
            "username": self.username,
            "base_url": self.base_url,
            "session_active": self.session is not None,
        }


if __name__ == "__main__":
    import sys
    
    # Test authentication functionality
    all_validation_failures = []
    total_tests = 0
    
    # Test 1: Session creation
    total_tests += 1
    try:
        auth_mgr = AuthenticationManager("test_user", "test_pass")
        session = auth_mgr.create_session()
        
        if not isinstance(session, requests.Session):
            all_validation_failures.append("Session creation: Result is not a requests.Session")
        
        required_headers = ["User-Agent", "Accept"]
        for header in required_headers:
            if header not in session.headers:
                all_validation_failures.append(f"Session creation: Missing header '{header}'")
                
    except Exception as e:
        all_validation_failures.append(f"Session creation: Exception occurred - {e}")
    
    # Test 2: Login success check
    total_tests += 1
    try:
        auth_mgr = AuthenticationManager("test_user", "test_pass")
        
        # Create mock response objects for testing
        class MockResponse:
            def __init__(self, text, url):
                self.text = text
                self.url = url
        
        success_response = MockResponse("로그아웃 button", "https://regtech.fsec.or.kr/main")
        failure_response = MockResponse("로그인 실패", "https://regtech.fsec.or.kr/login")
        
        if not auth_mgr.check_login_success(success_response):
            all_validation_failures.append("Login check: Success response not recognized")
        
        if auth_mgr.check_login_success(failure_response):
            all_validation_failures.append("Login check: Failure response not recognized")
            
    except Exception as e:
        all_validation_failures.append(f"Login check: Exception occurred - {e}")
    
    # Test 3: Session information
    total_tests += 1
    try:
        auth_mgr = AuthenticationManager("test_user", "test_pass")
        session_info = auth_mgr.get_session_info()
        
        required_keys = ["authenticated", "username", "base_url", "session_active"]
        for key in required_keys:
            if key not in session_info:
                all_validation_failures.append(f"Session info: Missing key '{key}'")
        
        if session_info["username"] != "test_user":
            all_validation_failures.append("Session info: Username mismatch")
            
    except Exception as e:
        all_validation_failures.append(f"Session info: Exception occurred - {e}")
    
    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Authentication module is validated and formal tests can now be written")
        sys.exit(0)
