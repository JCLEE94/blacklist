#!/usr/bin/env python3
"""
향상된 REGTECH 수집기 - BaseCollector 상속 및 강화된 에러 핸들링
"""

import asyncio
import logging
import os
import json
import time
from datetime import datetime
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup

from ..common.ip_utils import IPUtils
from .helpers.data_transform import RegtechDataTransform
from .helpers.request_utils import RegtechRequestUtils
from .helpers.validation_utils import RegtechValidationUtils
from .unified_collector import BaseCollector, CollectionConfig

logger = logging.getLogger(__name__)


class RegtechCollector(BaseCollector):
    """
    BaseCollector를 상속받은 REGTECH 수집기
    강화된 에러 핸들링과 복구 메커니즘 포함
    """

    def __init__(self, config: CollectionConfig):
        super().__init__("REGTECH", config)

        # 기본 설정
        self.base_url = "https://regtech.fsec.or.kr"
        self.config_data = {}
        
        # 쿠키 기반 인증 설정
        self.cookie_string = None
        self.session_cookies = {}
        self.cookie_file_path = 'regtech_cookies.json'
        self.auto_extract_cookies = True  # 자동 쿠키 추출 활성화
        
        # 환경 변수에서 설정 로드
        self.username = os.getenv('REGTECH_USERNAME')
        self.password = os.getenv('REGTECH_PASSWORD')
        
        # 쿠키 설정 (환경 변수 또는 파일에서)
        self.cookie_string = os.getenv('REGTECH_COOKIES', '')
        
        # 저장된 쿠키 로드 시도
        if not self.cookie_string:
            self.cookie_string = self._load_saved_cookies()
        
        # DB에서 설정 로드 (선택적)
        try:
            from ..database.collection_settings import CollectionSettingsDB
            self.db = CollectionSettingsDB()
            
            # DB에서 REGTECH 설정 가져오기
            source_config = self.db.get_source_config("regtech")
            credentials = self.db.get_credentials("regtech")
            
            if source_config:
                self.base_url = source_config.get("base_url", self.base_url)
                self.config_data = source_config.get("config", {})
            
            if credentials:
                self.username = credentials["username"]
                self.password = credentials["password"]
            else:
                # 환경변수 fallback
                self.username = os.getenv("REGTECH_USERNAME")
                self.password = os.getenv("REGTECH_PASSWORD")
                
        except ImportError:
            # DB 없으면 기본값/환경변수 사용
            self.base_url = "https://regtech.fsec.or.kr"
            self.username = os.getenv("REGTECH_USERNAME")
            self.password = os.getenv("REGTECH_PASSWORD")
            self.config_data = {}

        # 에러 핸들링 설정
        self.max_page_errors = 5  # 연속 페이지 에러 허용 횟수
        self.session_retry_limit = 3  # 세션 재시도 횟수
        self.request_timeout = 30  # 요청 타임아웃 (초)
        self.page_delay = 1  # 페이지 간 지연 (초)

        # 상태 추적
        self.current_session = None
        self.page_error_count = 0
        self.total_collected = 0
        self.cookie_auth_mode = False  # 쿠키 인증 모드

        # Helper 객체들 초기화
        self.request_utils = RegtechRequestUtils(self.base_url, self.request_timeout)
        self.data_transform = RegtechDataTransform()
        self.validation_utils = RegtechValidationUtils()
        self.validation_utils.set_ip_utils(IPUtils)

        # 쿠키가 있으면 쿠키 모드, 없으면 자동 추출 시도
        if self.cookie_string:
            self.cookie_auth_mode = True
            self._parse_cookie_string()
            logger.info("REGTECH collector initialized in cookie mode")
        elif self.auto_extract_cookies and self.username and self.password:
            logger.info("No cookies found - will attempt automatic extraction")
            self.cookie_auth_mode = False  # 처음에는 False, 추출 성공 시 True로 변경
        elif not self.username or not self.password:
            logger.warning("No REGTECH credentials or cookies provided - collector may not work")
        else:
            logger.info("REGTECH collector initialized in login mode")

    def _parse_cookie_string(self):
        """쿠키 문자열 파싱"""
        if not self.cookie_string:
            return
        
        for cookie in self.cookie_string.split(';'):
            cookie = cookie.strip()
            if '=' in cookie:
                name, value = cookie.split('=', 1)
                self.session_cookies[name.strip()] = value.strip()
        
        logger.info(f"Parsed {len(self.session_cookies)} cookies")

    def _load_saved_cookies(self) -> str:
        """저장된 쿠키 파일에서 로드"""
        try:
            if os.path.exists(self.cookie_file_path):
                with open(self.cookie_file_path, 'r') as f:
                    data = json.load(f)
                    cookie_string = data.get('cookie_string', '')
                    if cookie_string:
                        # 쿠키 유효성 간단 체크 (생성 시간 확인)
                        extracted_at = data.get('extracted_at', '')
                        if extracted_at:
                            logger.info(f"Loaded saved cookies from {extracted_at}")
                        return cookie_string
        except Exception as e:
            logger.debug(f"Failed to load saved cookies: {e}")
        return ''

    def _save_cookies(self, cookie_string: str, method: str = 'auto_extracted'):
        """쿠키를 파일에 저장"""
        try:
            cookie_data = {
                'cookie_string': cookie_string,
                'cookies': self.session_cookies,
                'extracted_at': datetime.now().isoformat(),
                'method': method,
                'username': self.username
            }
            with open(self.cookie_file_path, 'w') as f:
                json.dump(cookie_data, f, indent=2)
            logger.info(f"Cookies saved to {self.cookie_file_path}")
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")

    def _extract_cookies_with_playwright(self) -> str:
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
                page.goto(f'{self.base_url}/login/loginForm')
                page.wait_for_load_state('networkidle')
                
                # 2. 자동 로그인
                logger.info("Attempting automatic login...")
                page.fill('input[name="loginID"]', self.username)
                page.fill('input[name="loginPW"]', self.password)
                
                # 로그인 버튼 클릭
                page.click('button[type="submit"], input[type="submit"]')
                page.wait_for_load_state('networkidle')
                
                # 3. 로그인 성공 확인
                current_url = page.url
                if 'login' not in current_url.lower():
                    logger.info("✅ Login successful!")
                    
                    # 4. 쿠키 추출
                    logger.info("Extracting cookies...")
                    cookies = context.cookies()
                    
                    important_cookies = {}
                    for cookie in cookies:
                        if cookie['name'] in ['JSESSIONID', 'regtech-front']:
                            important_cookies[cookie['name']] = cookie['value']
                    
                    if important_cookies:
                        cookie_string = '; '.join([f"{name}={value}" for name, value in important_cookies.items()])
                        
                        browser.close()
                        logger.info(f"✅ Cookies extracted successfully: {len(important_cookies)} cookies")
                        return cookie_string
                    else:
                        logger.warning("❌ No important cookies found")
                else:
                    logger.warning("❌ Login failed - still on login page")
                
                browser.close()
                return ''
                
        except ImportError:
            logger.warning("Playwright not available - install with: pip install playwright && playwright install chromium")
            return ''
        except Exception as e:
            logger.error(f"Cookie extraction with Playwright failed: {e}")
            return ''

    def _extract_cookies_with_selenium(self) -> str:
        """Selenium으로 자동 쿠키 추출 (fallback)"""
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.chrome.options import Options
            
            logger.info("🍪 Extracting cookies with Selenium...")
            
            # Chrome 옵션 (headless)
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            driver = webdriver.Chrome(options=chrome_options)
            
            try:
                # 1. 로그인 페이지 접속
                logger.info("Accessing REGTECH login page...")
                driver.get(f'{self.base_url}/login/loginForm')
                time.sleep(2)
                
                # 2. 자동 로그인
                logger.info("Attempting automatic login...")
                driver.find_element(By.NAME, 'loginID').send_keys(self.username)
                driver.find_element(By.NAME, 'loginPW').send_keys(self.password)
                
                # 로그인 버튼 클릭
                driver.find_element(By.CSS_SELECTOR, 'button[type="submit"], input[type="submit"]').click()
                time.sleep(3)
                
                # 3. 로그인 성공 확인 및 쿠키 추출
                current_url = driver.current_url
                if 'login' not in current_url.lower():
                    logger.info("✅ Login successful!")
                    
                    logger.info("Extracting cookies...")
                    cookies = driver.get_cookies()
                    
                    important_cookies = {}
                    for cookie in cookies:
                        if cookie['name'] in ['JSESSIONID', 'regtech-front']:
                            important_cookies[cookie['name']] = cookie['value']
                    
                    if important_cookies:
                        cookie_string = '; '.join([f"{name}={value}" for name, value in important_cookies.items()])
                        logger.info(f"✅ Cookies extracted successfully: {len(important_cookies)} cookies")
                        return cookie_string
                else:
                    logger.warning("❌ Login failed - still on login page")
                    
            finally:
                driver.quit()
                
        except ImportError:
            logger.warning("Selenium not available - install with: pip install selenium")
            return ''
        except Exception as e:
            logger.error(f"Cookie extraction with Selenium failed: {e}")
            return ''
        
        return ''

    def _auto_extract_cookies(self) -> bool:
        """자동 쿠키 추출 (Playwright 우선, Selenium fallback)"""
        if not self.auto_extract_cookies or not self.username or not self.password:
            return False
        
        logger.info("🔄 Attempting automatic cookie extraction...")
        
        # 1. Playwright 시도
        cookie_string = self._extract_cookies_with_playwright()
        
        # 2. Playwright 실패 시 Selenium 시도
        if not cookie_string:
            logger.info("Playwright failed, trying Selenium...")
            cookie_string = self._extract_cookies_with_selenium()
        
        # 3. 추출 성공 시 설정
        if cookie_string:
            self.cookie_string = cookie_string
            self.cookie_auth_mode = True
            self._parse_cookie_string()
            self._save_cookies(cookie_string, 'auto_extracted')
            logger.info("✅ Automatic cookie extraction successful - switched to cookie mode")
            return True
        else:
            logger.error("❌ All cookie extraction methods failed")
            return False

    def _is_cookie_expired(self, response) -> bool:
        """쿠키 만료 여부 확인"""
        if not response:
            return True
            
        # 로그인 페이지로 리다이렉트 확인
        if response.status_code == 302:
            location = response.headers.get('Location', '')
            if 'login' in location.lower():
                return True
        
        # 현재 URL이 로그인 페이지인지 확인
        if 'login' in response.url.lower():
            return True
            
        # 인증 오류 응답 확인
        if response.status_code in [401, 403]:
            return True
            
        return False

    def set_cookie_string(self, cookie_string: str):
        """외부에서 쿠키 문자열 설정"""
        self.cookie_string = cookie_string
        self.cookie_auth_mode = True
        self._parse_cookie_string()
        self._save_cookies(cookie_string, 'manual')
        logger.info("Cookie string updated - switched to cookie mode")

    @property
    def source_type(self) -> str:
        return "REGTECH"

    async def _collect_data(self) -> List[Any]:
        """
        메인 데이터 수집 메서드 - 자동 쿠키 관리 포함
        """
        # 1. 쿠키가 없으면 자동 추출 시도
        if not self.cookie_auth_mode and self.auto_extract_cookies:
            logger.info("🔄 No cookies available - attempting automatic extraction...")
            if self._auto_extract_cookies():
                logger.info("✅ Automatic cookie extraction successful")
            else:
                logger.warning("❌ Automatic cookie extraction failed - falling back to login mode")
                return await self._collect_with_login()
        
        # 2. 쿠키 기반 수집 시도
        if self.cookie_auth_mode:
            collected_data = await self._collect_with_cookies()
            
            # 3. 수집 결과가 없거나 쿠키 만료 의심 시 재추출 시도
            if not collected_data and self.auto_extract_cookies:
                logger.warning("🔄 No data collected - cookies might be expired, attempting re-extraction...")
                if self._auto_extract_cookies():
                    logger.info("✅ Cookie re-extraction successful - retrying collection...")
                    collected_data = await self._collect_with_cookies()
                else:
                    logger.error("❌ Cookie re-extraction failed - falling back to login mode")
                    return await self._collect_with_login()
            
            return collected_data
        else:
            return await self._collect_with_login()

    async def _collect_with_cookies(self) -> List[Any]:
        """쿠키 기반 데이터 수집"""
        collected_ips = []
        
        try:
            # 세션 생성 및 쿠키 설정
            session = requests.Session()
            
            # 쿠키 설정
            for name, value in self.session_cookies.items():
                session.cookies.set(name, value)
            
            # 헤더 설정
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': f'{self.base_url}/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8'
            })
            
            logger.info("Starting cookie-based data collection")
            
            # 블랙리스트 페이지들 시도
            blacklist_urls = [
                '/board/boardList?menuCode=HPHB0620101',  # 악성IP차단
                '/board/excelDownload?menuCode=HPHB0620101',  # Excel 다운로드
                '/threat/blacklist/list',
                '/api/blacklist/search'
            ]
            
            for path in blacklist_urls:
                try:
                    url = f"{self.base_url}{path}"
                    logger.info(f"Trying URL: {url}")
                    
                    response = session.get(url, verify=False, timeout=self.request_timeout)
                    
                    # 쿠키 만료 확인
                    if self._is_cookie_expired(response):
                        logger.warning(f"Cookies expired at {url} - will trigger re-extraction")
                        return []  # 빈 결과 반환하여 상위에서 재추출 트리거
                    
                    if response.status_code == 200:
                        content_type = response.headers.get('content-type', '').lower()
                        
                        # Excel 파일 처리
                        if 'excel' in content_type or 'spreadsheet' in content_type:
                            ips = await self._process_excel_response(response)
                            if ips:
                                collected_ips.extend(ips)
                                logger.info(f"Collected {len(ips)} IPs from Excel download")
                                break
                        
                        # HTML 페이지 처리
                        elif 'text/html' in content_type:
                            ips = await self._process_html_response(response)
                            if ips:
                                collected_ips.extend(ips)
                                logger.info(f"Collected {len(ips)} IPs from HTML page")
                                if len(ips) > 10:  # 충분한 데이터가 있으면 중단
                                    break
                        
                        # JSON 응답 처리
                        elif 'application/json' in content_type:
                            ips = await self._process_json_response(response)
                            if ips:
                                collected_ips.extend(ips)
                                logger.info(f"Collected {len(ips)} IPs from JSON API")
                                break
                    
                    elif response.status_code == 302 and 'login' in response.headers.get('Location', ''):
                        logger.warning("Redirected to login - cookies may be expired")
                        break
                    
                except Exception as e:
                    logger.error(f"Error accessing {path}: {e}")
                    continue
            
            # 수집된 데이터 검증 및 변환
            if collected_ips:
                validated_ips = []
                for ip_data in collected_ips:
                    if self.validation_utils.validate_ip_data(ip_data):
                        validated_ips.append(ip_data)
                
                logger.info(f"Validated {len(validated_ips)} out of {len(collected_ips)} collected IPs")
                return validated_ips
            else:
                logger.warning("No IPs collected - check cookies or access permissions")
                return []
                
        except Exception as e:
            logger.error(f"Cookie-based collection failed: {e}")
            return []

    async def _process_excel_response(self, response) -> List[Dict[str, Any]]:
        """Excel 응답 처리"""
        try:
            import pandas as pd
            from io import BytesIO
            
            # Excel 파일 저장
            filename = f"regtech_blacklist_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            # Excel 파일 읽기
            df = pd.read_excel(BytesIO(response.content))
            
            # IP 컬럼 찾기
            ip_columns = [col for col in df.columns if 'ip' in str(col).lower() or 'IP' in str(col)]
            
            if not ip_columns:
                # 첫 번째 컬럼이 IP일 가능성
                ip_columns = [df.columns[0]]
            
            ips = []
            for _, row in df.iterrows():
                for ip_col in ip_columns:
                    ip_value = str(row[ip_col]).strip()
                    if self.validation_utils.is_valid_ip(ip_value):
                        ips.append({
                            'ip': ip_value,
                            'source': 'REGTECH',
                            'threat_level': 'medium',
                            'detection_date': datetime.now().strftime('%Y-%m-%d'),
                            'method': 'excel_download',
                            'description': f'Blacklisted IP from REGTECH Excel export'
                        })
                        break
            
            logger.info(f"Processed Excel file: {filename}, extracted {len(ips)} IPs")
            return ips
            
        except ImportError:
            logger.warning("pandas not available - cannot process Excel files")
            return []
        except Exception as e:
            logger.error(f"Error processing Excel response: {e}")
            return []

    async def _process_html_response(self, response) -> List[Dict[str, Any]]:
        """HTML 응답 처리"""
        try:
            import re
            
            # IP 패턴으로 추출
            ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
            ips_found = re.findall(ip_pattern, response.text)
            
            ips = []
            for ip in set(ips_found):  # 중복 제거
                if self.validation_utils.is_valid_ip(ip):
                    ips.append({
                        'ip': ip,
                        'source': 'REGTECH',
                        'threat_level': 'medium',
                        'detection_date': datetime.now().strftime('%Y-%m-%d'),
                        'method': 'html_parsing',
                        'description': f'Blacklisted IP from REGTECH web page'
                    })
            
            # BeautifulSoup로 테이블 파싱 시도
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 테이블에서 IP 추출
                tables = soup.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows[1:]:  # 헤더 제외
                        cells = row.find_all(['td', 'th'])
                        for cell in cells:
                            text = cell.get_text().strip()
                            if re.match(ip_pattern, text) and self.validation_utils.is_valid_ip(text):
                                # 중복 확인
                                if not any(ip_data['ip'] == text for ip_data in ips):
                                    ips.append({
                                        'ip': text,
                                        'source': 'REGTECH',
                                        'threat_level': 'medium',
                                        'detection_date': datetime.now().strftime('%Y-%m-%d'),
                                        'method': 'table_parsing',
                                        'description': f'Blacklisted IP from REGTECH table'
                                    })
            except:
                pass  # BeautifulSoup 파싱 실패해도 기본 regex 결과 사용
            
            return ips[:100]  # 최대 100개로 제한
            
        except Exception as e:
            logger.error(f"Error processing HTML response: {e}")
            return []

    async def _process_json_response(self, response) -> List[Dict[str, Any]]:
        """JSON 응답 처리"""
        try:
            data = response.json()
            ips = []
            
            # 다양한 JSON 구조 처리
            if isinstance(data, dict):
                # 데이터 배열 찾기
                items = None
                for key in ['data', 'items', 'list', 'blacklist', 'ips', 'results']:
                    if key in data and isinstance(data[key], list):
                        items = data[key]
                        break
                
                if items:
                    for item in items:
                        if isinstance(item, dict):
                            # IP 필드 찾기
                            ip_value = None
                            for ip_key in ['ip', 'ipAddress', 'target_ip', 'source_ip', 'addr']:
                                if ip_key in item:
                                    ip_value = str(item[ip_key]).strip()
                                    break
                            
                            if ip_value and self.validation_utils.is_valid_ip(ip_value):
                                ips.append({
                                    'ip': ip_value,
                                    'source': 'REGTECH',
                                    'threat_level': item.get('threat_level', 'medium'),
                                    'detection_date': item.get('date', datetime.now().strftime('%Y-%m-%d')),
                                    'method': 'json_api',
                                    'description': item.get('description', 'Blacklisted IP from REGTECH API')
                                })
                        elif isinstance(item, str) and self.validation_utils.is_valid_ip(item):
                            ips.append({
                                'ip': item,
                                'source': 'REGTECH',
                                'threat_level': 'medium',
                                'detection_date': datetime.now().strftime('%Y-%m-%d'),
                                'method': 'json_api',
                                'description': 'Blacklisted IP from REGTECH API'
                            })
            
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, str) and self.validation_utils.is_valid_ip(item):
                        ips.append({
                            'ip': item,
                            'source': 'REGTECH',
                            'threat_level': 'medium',
                            'detection_date': datetime.now().strftime('%Y-%m-%d'),
                            'method': 'json_api',
                            'description': 'Blacklisted IP from REGTECH API'
                        })
            
            return ips
            
        except Exception as e:
            logger.error(f"Error processing JSON response: {e}")
            return []

    async def _collect_with_login(self) -> List[Any]:
        """기존 로그인 기반 데이터 수집"""
        collected_ips = []
        session_retry_count = 0

        while session_retry_count < self.session_retry_limit:
            try:
                # 세션 초기화
                session = self.request_utils.create_session()
                self.current_session = session

                # 로그인 시도
                if not await self._robust_login(session):
                    raise Exception("로그인 실패 후 재시도 한계 도달")

                # 데이터 수집
                start_date, end_date = self.data_transform.get_date_range(self.config)
                collected_ips = await self._robust_collect_ips(
                    session, start_date, end_date
                )

                # 성공적으로 수집 완료
                self.logger.info(f"REGTECH 수집 완료: {len(collected_ips)}개 IP")
                break

            except requests.exceptions.ConnectionError as e:
                session_retry_count += 1
                self.logger.warning(
                    f"연결 오류 (재시도 {session_retry_count}/{self.session_retry_limit}): {e}"
                )
                if session_retry_count < self.session_retry_limit:
                    await asyncio.sleep(5 * session_retry_count)  # 지수적 백오프

            except requests.exceptions.Timeout as e:
                session_retry_count += 1
                self.logger.warning(
                    f"타임아웃 오류 (재시도 {session_retry_count}/{self.session_retry_limit}): {e}"
                )
                if session_retry_count < self.session_retry_limit:
                    await asyncio.sleep(3 * session_retry_count)

            except Exception as e:
                self.logger.error(f"예상치 못한 오류: {e}")
                session_retry_count += 1
                if session_retry_count < self.session_retry_limit:
                    await asyncio.sleep(2 * session_retry_count)

            finally:
                if hasattr(self, "current_session") and self.current_session:
                    self.current_session.close()
                    self.current_session = None

        if session_retry_count >= self.session_retry_limit:
            raise Exception(f"최대 재시도 횟수 ({self.session_retry_limit}) 초과")

        return collected_ips

    async def _robust_login(self, session: requests.Session) -> bool:
        """강화된 로그인 로직"""
        login_attempts = 0
        max_login_attempts = 3

        while login_attempts < max_login_attempts:
            try:
                self.logger.info(
                    f"로그인 시도 {login_attempts + 1}/{max_login_attempts}"
                )

                # 로그인 페이지 접근
                login_page_url = f"{self.base_url}/login/loginForm"
                response = session.get(login_page_url)

                if response.status_code != 200:
                    raise Exception(f"로그인 페이지 접근 실패: {response.status_code}")

                # CSRF 토큰이나 숨겨진 필드 추출 시도
                soup = BeautifulSoup(response.text, "html.parser")
                hidden_inputs = soup.find_all("input", type="hidden")
                login_data = {
                    "username": self.username,
                    "password": self.password,
                    "login_error": "",
                    "txId": "",
                    "token": "",
                    "memberId": "",
                    "smsTimeExcess": "N",
                }

                # 숨겨진 필드들 추가
                for hidden_input in hidden_inputs:
                    name = hidden_input.get("name")
                    value = hidden_input.get("value", "")
                    if name:
                        login_data[name] = value

                # 로그인 요청
                login_url = f"{self.base_url}/login/addLogin"
                login_response = session.post(
                    login_url,
                    data=login_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    allow_redirects=True,
                )

                # 로그인 성공 확인
                if self.validation_utils.verify_login_success(login_response):
                    self.logger.info("로그인 성공")
                    return True
                else:
                    login_attempts += 1
                    if login_attempts < max_login_attempts:
                        self.logger.warning(f"로그인 실패, {2} 초 후 재시도")
                        await asyncio.sleep(2)

            except Exception as e:
                login_attempts += 1
                self.logger.error(f"로그인 중 오류: {e}")
                if login_attempts < max_login_attempts:
                    await asyncio.sleep(3)

        self.logger.error("로그인 최대 시도 횟수 초과")
        return False

    async def _robust_collect_ips(
        self, session: requests.Session, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """강화된 IP 수집 로직"""
        all_ips = []
        page = 0
        consecutive_errors = 0
        max_pages = 100  # 안전장치

        self.logger.info(f"IP 수집 시작: {start_date} ~ {end_date}")

        while page < max_pages and consecutive_errors < self.max_page_errors:
            try:
                # 취소 요청 확인
                if self.validation_utils.should_cancel(
                    getattr(self, "_cancel_event", None)
                ):
                    self.logger.info("사용자 취소 요청으로 수집 중단")
                    break

                # 페이지 지연
                if page > 0:
                    await asyncio.sleep(self.page_delay)

                # 페이지 데이터 수집
                page_ips = await self.request_utils.collect_single_page(
                    session, page, start_date, end_date
                )

                # IP 유효성 검사 적용
                valid_page_ips = []
                for ip_data in page_ips:
                    if self.validation_utils.is_valid_ip(ip_data.get("ip", "")):
                        valid_page_ips.append(ip_data)
                page_ips = valid_page_ips

                if not page_ips:
                    self.logger.info(
                        f"페이지 {page + 1}에서 더 이상 데이터 없음, 수집 종료"
                    )
                    break

                all_ips.extend(page_ips)
                consecutive_errors = 0  # 성공 시 에러 카운트 리셋

                self.logger.info(
                    f"페이지 {page + 1}: {len(page_ips)}개 수집 (총 {len(all_ips)}개)"
                )
                page += 1

            except requests.exceptions.RequestException as e:
                consecutive_errors += 1
                self.logger.warning(
                    f"페이지 {page + 1} 수집 실패 (연속 에러: {consecutive_errors}/{self.max_page_errors}): {e}"
                )

                if consecutive_errors < self.max_page_errors:
                    await asyncio.sleep(2 * consecutive_errors)  # 점진적 지연

            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"페이지 {page + 1} 처리 중 예상치 못한 오류: {e}")

                if consecutive_errors < self.max_page_errors:
                    await asyncio.sleep(1)

        if consecutive_errors >= self.max_page_errors:
            self.logger.error(f"연속 페이지 에러 한계 도달 ({self.max_page_errors})")

        # 중복 제거
        unique_ips = self.data_transform.remove_duplicates(all_ips)
        self.logger.info(f"중복 제거 후 최종 수집: {len(unique_ips)}개 IP")

        return unique_ips

    def _transform_data(self, raw_data: dict) -> dict:
        """데이터 변환 - 헬퍼 모듈 위임"""
        return self.data_transform.transform_data(raw_data)

    def collect_from_web(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        웹 수집 인터페이스 메서드 (동기 래퍼)
        collection_service.py에서 호출하는 인터페이스
        """
        import asyncio
        
        try:
            # 날짜 범위 설정
            if not start_date or not end_date:
                from datetime import datetime, timedelta
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            # 비동기 수집 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                collected_data = loop.run_until_complete(self._collect_data())
                return {
                    "success": True,
                    "data": collected_data,
                    "count": len(collected_data),
                    "message": f"REGTECH에서 {len(collected_data)}개 IP 수집 완료"
                }
            finally:
                loop.close()
                
        except Exception as e:
            self.logger.error(f"REGTECH 웹 수집 실패: {e}")
            return {
                "success": False,
                "data": [],
                "count": 0,
                "error": str(e),
                "message": f"REGTECH 수집 중 오류: {e}"
            }
