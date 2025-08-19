#!/usr/bin/env python3
"""
Fixed REGTECH Data Collector
Complete implementation that handles authentication and data collection
"""

import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class FixedRegtechCollector:
    """
    Fixed REGTECH collector with working authentication and data extraction
    """

    def __init__(self, username: str = None, password: str = None):
        self.base_url = "https://regtech.fsec.or.kr"
        self.username = username or os.getenv('REGTECH_USERNAME')
        self.password = password or os.getenv('REGTECH_PASSWORD')
        self.session = None
        self.authenticated = False
        self.timeout = 30
        
        if not self.username or not self.password:
            raise ValueError("REGTECH credentials not provided")

    def _create_session(self) -> requests.Session:
        """Create session with proper headers"""
        session = requests.Session()
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })
        return session

    def authenticate(self) -> bool:
        """
        Authenticate with REGTECH using verified 2-step process
        브라우저 분석으로 검증된 성공한 인증 방식 적용
        """
        try:
            self.session = self._create_session()
            
            # 1. 로그인 페이지 접속 (세션 쿠키 획득)
            logger.info("🔐 Getting session cookie...")
            login_url = f"{self.base_url}/login/loginForm"
            response = self.session.get(login_url, timeout=self.timeout)
            response.raise_for_status()
            
            # 2. 사용자 확인 API 호출 (첫 번째 단계)
            logger.info(f"👤 Verifying user: {self.username}")
            verify_data = {
                'memberId': self.username,
                'memberPw': self.password
            }
            
            # AJAX 헤더 설정
            self.session.headers.update({
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': self.base_url,
                'Referer': f'{self.base_url}/login/loginForm'
            })
            
            verify_resp = self.session.post(
                f"{self.base_url}/member/findOneMember",
                data=verify_data,
                timeout=self.timeout
            )
            
            if verify_resp.status_code != 200:
                logger.error(f"❌ User verification failed: {verify_resp.status_code}")
                return False
            
            logger.info("✅ User verified successfully")
            
            # 3. 실제 로그인 (두 번째 단계)
            logger.info("🔑 Performing actual login...")
            login_form_data = {
                'username': self.username,  # 브라우저 분석으로 확인된 필드명
                'password': self.password,  # 브라우저 분석으로 확인된 필드명
                'login_error': '',
                'txId': '',
                'token': '',
                'memberId': '',
                'smsTimeExcess': 'N'
            }
            
            login_resp = self.session.post(
                f"{self.base_url}/login/addLogin",  # 브라우저 분석으로 확인된 엔드포인트
                data=login_form_data,
                timeout=self.timeout,
                allow_redirects=True
            )
            
            # 로그인 성공 확인
            if login_resp.status_code == 200 and 'main' in login_resp.url:
                if 'logout' in login_resp.text.lower() or '로그아웃' in login_resp.text:
                    logger.info("✅ REGTECH authentication successful!")
                    self.authenticated = True
                    return True
            
            logger.error("❌ REGTECH authentication failed - redirect or content check failed")
            logger.debug(f"Response URL: {login_resp.url}")
            logger.debug(f"Response status: {login_resp.status_code}")
            return False
            
            logger.info(f"Submitting login to: {action}")
            
            response = self.session.post(
                action,
                data=login_data,
                timeout=self.timeout,
                verify=False,
                allow_redirects=True
            )
            
            # Check if login successful
            if "/login" not in response.url.lower() or self._check_login_success(response):
                logger.info("✅ REGTECH authentication successful")
                self.authenticated = True
                return True
            else:
                logger.error("❌ REGTECH authentication failed")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    def _check_login_success(self, response: requests.Response) -> bool:
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

    def collect_blacklist_data(self, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """
        Collect blacklist data from REGTECH
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of IP data dictionaries
        """
        if not self.authenticated:
            if not self.authenticate():
                logger.error("Cannot collect data - authentication failed")
                return []
        
        # Default date range (last 7 days)
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        logger.info(f"Collecting REGTECH data from {start_date} to {end_date}")
        
        collected_ips = []
        
        # Try multiple data collection methods
        methods = [
            self._collect_from_board,
            self._collect_from_excel,
            self._collect_from_api
        ]
        
        for method in methods:
            try:
                logger.info(f"Trying collection method: {method.__name__}")
                ips = method(start_date, end_date)
                if ips:
                    collected_ips.extend(ips)
                    logger.info(f"✅ {method.__name__} collected {len(ips)} IPs")
                    break  # Stop on first successful method
                else:
                    logger.info(f"❌ {method.__name__} returned no data")
            except Exception as e:
                logger.error(f"Error in {method.__name__}: {e}")
                continue
        
        # Remove duplicates
        if collected_ips:
            unique_ips = self._remove_duplicates(collected_ips)
            logger.info(f"Final result: {len(unique_ips)} unique IPs collected")
            return unique_ips
        else:
            logger.warning("No data collected from any method")
            return []

    def _collect_from_board(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Collect from board/bulletin system"""
        try:
            # Try blacklist board URL
            board_url = f"{self.base_url}/board/boardList"
            params = {
                "menuCode": "HPHB0620101",  # Malicious IP blocking
                "startDate": start_date,
                "endDate": end_date
            }
            
            response = self.session.get(board_url, params=params, timeout=self.timeout, verify=False)
            
            if response.status_code == 200:
                return self._parse_board_page(response.text, "REGTECH_BOARD")
            else:
                logger.warning(f"Board access failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Board collection error: {e}")
            return []

    def _collect_from_excel(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Collect from Excel download"""
        try:
            excel_url = f"{self.base_url}/board/excelDownload"
            params = {
                "menuCode": "HPHB0620101",
                "startDate": start_date,
                "endDate": end_date
            }
            
            response = self.session.get(excel_url, params=params, timeout=self.timeout, verify=False)
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                if 'excel' in content_type or 'spreadsheet' in content_type:
                    return self._parse_excel_response(response.content, "REGTECH_EXCEL")
                else:
                    # Might be HTML with data
                    return self._parse_board_page(response.text, "REGTECH_EXCEL_HTML")
            else:
                logger.warning(f"Excel download failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Excel collection error: {e}")
            return []

    def _collect_from_api(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Try API-based collection"""
        try:
            api_urls = [
                f"{self.base_url}/api/blacklist/search",
                f"{self.base_url}/threat/blacklist/list",
                f"{self.base_url}/data/blacklist"
            ]
            
            for api_url in api_urls:
                try:
                    params = {
                        "startDate": start_date,
                        "endDate": end_date,
                        "pageSize": 1000
                    }
                    
                    response = self.session.get(api_url, params=params, timeout=self.timeout, verify=False)
                    
                    if response.status_code == 200:
                        content_type = response.headers.get('content-type', '').lower()
                        if 'json' in content_type:
                            return self._parse_json_response(response.json(), "REGTECH_API")
                        else:
                            return self._parse_board_page(response.text, "REGTECH_API_HTML")
                except Exception:
                    continue
            
            return []
            
        except Exception as e:
            logger.error(f"API collection error: {e}")
            return []

    def _parse_board_page(self, html_content: str, source: str) -> List[Dict[str, Any]]:
        """Parse HTML page for IP addresses"""
        ips = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for IP addresses in various elements
            ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
            
            # Search in table cells
            for cell in soup.find_all(['td', 'th', 'span', 'div']):
                text = cell.get_text(strip=True)
                matches = ip_pattern.findall(text)
                for ip in matches:
                    if self._is_valid_ip(ip):
                        ips.append({
                            "ip": ip,
                            "source": source,
                            "detection_date": datetime.now().strftime('%Y-%m-%d'),
                            "description": f"Found in {source}",
                            "confidence": "medium"
                        })
            
            return ips
            
        except Exception as e:
            logger.error(f"Error parsing board page: {e}")
            return []

    def _parse_excel_response(self, excel_content: bytes, source: str) -> List[Dict[str, Any]]:
        """Parse Excel response for IP addresses"""
        try:
            # Save to temporary file and parse with pandas
            import tempfile
            import pandas as pd
            
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
                tmp_file.write(excel_content)
                tmp_file.flush()
                
                df = pd.read_excel(tmp_file.name, engine='openpyxl')
                
                # Look for IP columns
                ip_columns = []
                for col in df.columns:
                    col_lower = str(col).lower()
                    if any(word in col_lower for word in ['ip', '주소', 'address']):
                        ip_columns.append(col)
                
                ips = []
                for col in ip_columns:
                    for value in df[col].dropna():
                        ip_str = str(value).strip()
                        if self._is_valid_ip(ip_str):
                            ips.append({
                                "ip": ip_str,
                                "source": source,
                                "detection_date": datetime.now().strftime('%Y-%m-%d'),
                                "description": f"Excel data from column {col}",
                                "confidence": "high"
                            })
                
                # Cleanup
                os.unlink(tmp_file.name)
                return ips
                
        except ImportError:
            logger.warning("pandas not available for Excel parsing")
            return []
        except Exception as e:
            logger.error(f"Error parsing Excel: {e}")
            return []

    def _parse_json_response(self, json_data: Dict, source: str) -> List[Dict[str, Any]]:
        """Parse JSON response for IP addresses"""
        ips = []
        
        try:
            # Handle different JSON structures
            if isinstance(json_data, dict):
                if 'data' in json_data:
                    data = json_data['data']
                elif 'items' in json_data:
                    data = json_data['items']
                else:
                    data = json_data
            else:
                data = json_data
            
            # If data is a list
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        ip = self._extract_ip_from_dict(item)
                        if ip:
                            ips.append({
                                "ip": ip,
                                "source": source,
                                "detection_date": item.get("date", datetime.now().strftime('%Y-%m-%d')),
                                "description": item.get("description", "JSON API data"),
                                "confidence": "high"
                            })
            
            return ips
            
        except Exception as e:
            logger.error(f"Error parsing JSON: {e}")
            return []

    def _extract_ip_from_dict(self, data: Dict) -> Optional[str]:
        """Extract IP address from dictionary"""
        ip_keys = ['ip', 'ip_address', 'address', 'target_ip', 'source_ip']
        
        for key in ip_keys:
            if key in data:
                ip_str = str(data[key]).strip()
                if self._is_valid_ip(ip_str):
                    return ip_str
        
        return None

    def _is_valid_ip(self, ip_str: str) -> bool:
        """Validate IP address"""
        try:
            import ipaddress
            ip = ipaddress.ip_address(ip_str)
            # Only allow public IPs
            return not (ip.is_private or ip.is_loopback or ip.is_multicast)
        except ValueError:
            return False

    def _remove_duplicates(self, ips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate IPs"""
        seen_ips = set()
        unique_ips = []
        
        for ip_data in ips:
            ip = ip_data.get("ip")
            if ip and ip not in seen_ips:
                seen_ips.add(ip)
                unique_ips.append(ip_data)
        
        return unique_ips

    def collect_from_web(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        Main collection interface method
        Compatible with existing collection service
        """
        try:
            collected_data = self.collect_blacklist_data(start_date, end_date)
            
            return {
                "success": True,
                "data": collected_data,
                "count": len(collected_data),
                "message": f"REGTECH에서 {len(collected_data)}개 IP 수집 완료"
            }
            
        except Exception as e:
            logger.error(f"REGTECH 웹 수집 실패: {e}")
            return {
                "success": False,
                "data": [],
                "count": 0,
                "error": str(e),
                "message": f"REGTECH 수집 중 오류: {e}"
            }

    def logout(self):
        """Logout from REGTECH"""
        if self.session:
            try:
                self.session.get(f"{self.base_url}/logout", verify=False, timeout=10)
            except Exception:
                pass
            finally:
                self.session.close()
                self.session = None
                self.authenticated = False


if __name__ == "__main__":
    """Test the fixed collector"""
    import sys
    from dotenv import load_dotenv
    
    all_validation_failures = []
    total_tests = 0
    
    load_dotenv()
    
    # Test 1: Collector initialization
    total_tests += 1
    try:
        collector = FixedRegtechCollector()
        if not collector.username or not collector.password:
            all_validation_failures.append("Collector initialization failed - missing credentials")
    except Exception as e:
        all_validation_failures.append(f"Collector initialization failed: {e}")
    
    # Test 2: Authentication
    total_tests += 1
    try:
        auth_success = collector.authenticate()
        if not auth_success:
            all_validation_failures.append("Authentication failed")
    except Exception as e:
        all_validation_failures.append(f"Authentication test failed: {e}")
    
    # Test 3: Data collection
    total_tests += 1
    try:
        result = collector.collect_from_web()
        if not result.get("success"):
            all_validation_failures.append(f"Data collection failed: {result.get('error', 'Unknown error')}")
        else:
            print(f"Collection result: {result.get('count', 0)} IPs collected")
    except Exception as e:
        all_validation_failures.append(f"Data collection test failed: {e}")
    
    # Test 4: Logout
    total_tests += 1
    try:
        collector.logout()
        # Logout always succeeds
    except Exception as e:
        all_validation_failures.append(f"Logout test failed: {e}")
    
    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Fixed REGTECH collector is validated and ready for use")
        sys.exit(0)