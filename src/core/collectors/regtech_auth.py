#!/usr/bin/env python3
"""
REGTECH 인증 모듈
regtech_collector.py에서 분리된 인증 관련 기능
"""

import logging
import re
import requests
from bs4 import BeautifulSoup
from typing import Optional

logger = logging.getLogger(__name__)


class RegtechAuth:
    """
REGTECH 인증 처리 전담 클래스
    """
    
    def __init__(self, base_url: str, username: str, password: str, timeout: int = 30):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.timeout = timeout
        self.session = None
    def create_session(self) -> requests.Session:
        """새로운 세션 생성"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/91.0.4472.124 Safari/537.36'),
            'Accept': ('text/html,application/xhtml+xml,application/xml;'
                      'q=0.9,image/webp,*/*;q=0.8'),
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        return session
        
    def login(self) -> Optional[requests.Session]:
        """
        REGTECH 로그인 수행

        Returns:
            requests.Session: 로그인된 세션 또는 None
        """
        try:
            # 새 세션 생성
            self.session = self.create_session()
            
            # 로그인 페이지 접근
            login_url = f"{self.base_url}/login"
            logger.info(f"Accessing login page: {login_url}")

            response = self.session.get(login_url, timeout=self.timeout)
            response.raise_for_status()

            # 로그인 폼 처리
            soup = BeautifulSoup(response.text, 'html.parser')
            login_form = soup.find('form')

            if not login_form:
                logger.error("Login form not found")
                return None

            # 로그인 데이터 준비
            login_data = {
                'username': self.username,
                'password': self.password
            }

            # CSRF 토큰 처리 (있는 경우)
            csrf_input = soup.find('input', {
                'name': re.compile(r'csrf|token', re.I)
            })
            if csrf_input and csrf_input.get('value'):
                login_data[csrf_input['name']] = csrf_input['value']

            # 로그인 요청 전송
            login_submit_url = login_form.get('action', login_url)
            if not login_submit_url.startswith('http'):
                login_submit_url = f"{self.base_url}{login_submit_url}"

            logger.info(f"Submitting login to: {login_submit_url}")

            response = self.session.post(
                login_submit_url,
                data=login_data,
                timeout=self.timeout,
                allow_redirects=True
            )
            response.raise_for_status()

            # 로그인 성공 확인
            if self._verify_login_success(response):
                logger.info("REGTECH login successful")
                return self.session
            else:
                logger.error("REGTECH login failed")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during REGTECH login: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during REGTECH login: {e}")
            return None
            
    def _verify_login_success(self, response: requests.Response) -> bool:
        """로그인 성공 여부 확인"""
        # 로그인 실패 지표들 확인
        failure_indicators = [
            '로그인 실패',
            'login failed',
            '잘못된 사용자',
            'invalid credentials',
            '비밀번호가 올바르지 않습니다'
        ]

        response_text = response.text.lower()

        for indicator in failure_indicators:
            if indicator.lower() in response_text:
                return False

        # 로그인 성공 지표들 확인
        success_indicators = [
            '대시보드',
            'dashboard',
            '메인 페이지',
            '로그아웃',
            'logout'
        ]

        for indicator in success_indicators:
            if indicator.lower() in response_text:
                return True

        # URL 기반 확인 (로그인 후 리다이렉트)
        if '/login' not in response.url and response.status_code == 200:
            return True

        return False
        
    def logout(self) -> bool:
        """로그아웃 수행"""
        if not self.session:
            return True

        try:
            logout_url = f"{self.base_url}/logout"
            response = self.session.get(logout_url, timeout=self.timeout)
            response.raise_for_status()

            logger.info("REGTECH logout successful")
            return True

        except Exception as e:
            logger.warning(f"Logout failed (non-critical): {e}")
            return False
        finally:
            if self.session:
                self.session.close()
                self.session = None
