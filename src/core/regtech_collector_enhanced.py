#!/usr/bin/env python3
"""
Enhanced REGTECH 수집기 - 안정성 및 오류 처리 강화 버전
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
import threading
from dataclasses import dataclass
import re
from bs4 import BeautifulSoup
import io
import tempfile
from urllib.parse import urljoin
import traceback
from requests.exceptions import RequestException, Timeout, ConnectionError

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from src.core.models import BlacklistEntry
from src.config.settings import settings
from src.utils.error_handler import (
    CollectionError, ExternalServiceError, retry_on_error,
    handle_api_errors, safe_execute
)
from src.utils.structured_logging import get_logger

logger = get_logger(__name__)

if not PANDAS_AVAILABLE:
    logger.warning("pandas not available - Excel download will not work")


@dataclass
class RegtechCollectionStats:
    """REGTECH 수집 통계"""
    start_time: datetime
    end_time: Optional[datetime] = None
    total_collected: int = 0
    successful_collections: int = 0
    failed_collections: int = 0
    pages_processed: int = 0
    duplicate_count: int = 0
    error_count: int = 0
    source_method: str = "unknown"
    last_error: Optional[str] = None
    auth_attempts: int = 0
    excel_attempts: int = 0
    html_attempts: int = 0


class EnhancedRegtechCollector:
    """
    Enhanced REGTECH 수집기 - 더 강력한 오류 처리 및 재시도 로직
    """
    
    def __init__(self, data_dir: str, cache_backend=None):
        self.data_dir = data_dir
        self.regtech_dir = os.path.join(data_dir, 'regtech')
        
        # 디렉토리 생성
        os.makedirs(self.regtech_dir, exist_ok=True)
        
        # REGTECH API 설정
        self.base_url = settings.regtech_base_url.rstrip('/')
        self.advisory_endpoint = "/fcti/securityAdvisory/advisoryList"
        
        # 수집 통계
        self.stats = RegtechCollectionStats(start_time=datetime.now())
        
        # 재시도 설정
        self.max_retries = 3
        self.retry_delay = 5
        
        # 세션 타임아웃 설정
        self.session_timeout = 60
        
        logger.info(f"Enhanced REGTECH 수집기 초기화 완료: {self.regtech_dir}")
    
    def collect_from_web(self, max_pages: int = 25, page_size: int = 100, 
                        parallel_workers: int = 1, start_date: str = None, 
                        end_date: str = None) -> List[BlacklistEntry]:
        """
        REGTECH 데이터 수집 - 강화된 오류 처리 및 재시도 로직
        """
        logger.info(f"🔄 Enhanced REGTECH 수집 시작")
        
        # 날짜 설정
        if not start_date or not end_date:
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=90)
            start_date = start_dt.strftime('%Y%m%d')
            end_date = end_dt.strftime('%Y%m%d')
        
        is_daily = (start_date == end_date)
        logger.info(f"📆 수집 기간: {start_date} ~ {end_date} {'(일일 수집)' if is_daily else ''}")
        
        self.stats = RegtechCollectionStats(
            start_time=datetime.now(),
            source_method="enhanced_collection"
        )
        
        collected_ips = []
        
        # 여러 수집 방법을 순차적으로 시도
        collection_methods = [
            ("Excel Download", self._try_excel_collection),
            ("HTML Parsing", self._try_html_collection),
            ("HAR-based Collection", self._try_har_based_collection)
        ]
        
        for method_name, method_func in collection_methods:
            try:
                logger.info(f"🔧 시도 중: {method_name}")
                result = method_func(start_date, end_date, max_pages, page_size)
                
                if result and len(result) > 0:
                    logger.info(f"✅ {method_name} 성공: {len(result)}개 IP 수집")
                    collected_ips = result
                    self.stats.source_method = method_name.lower().replace(' ', '_')
                    break
                else:
                    logger.warning(f"{method_name} 실패 또는 데이터 없음")
                    
            except CollectionError as e:
                logger.error(f"{method_name} 수집 오류: {e}")
                self.stats.last_error = str(e)
                self.stats.error_count += 1
                continue
            except Exception as e:
                logger.error(f"{method_name} 중 예상치 못한 오류: {e}")
                self.stats.last_error = str(e)
                self.stats.error_count += 1
                continue
        
        # 최종 결과 처리
        self.stats.end_time = datetime.now()
        self.stats.total_collected = len(collected_ips)
        
        if collected_ips:
            self.stats.successful_collections = len(collected_ips)
            logger.info(f"✅ 최종 수집 완료: {len(collected_ips)}개 IP")
            self._log_collection_summary()
        else:
            self.stats.failed_collections += 1
            logger.error(f"❌ 모든 수집 방법 실패")
            self._log_failure_details()
        
        return collected_ips
    
    def _try_excel_collection(self, start_date: str, end_date: str, 
                             max_pages: int, page_size: int) -> List[BlacklistEntry]:
        """Excel 다운로드 방식 시도"""
        if not PANDAS_AVAILABLE:
            logger.warning("pandas 미설치로 Excel 수집 불가")
            return []
        
        for attempt in range(self.max_retries):
            self.stats.excel_attempts += 1
            
            try:
                session = self._create_session()
                
                # 로그인 시도
                if not self._perform_enhanced_login(session):
                    logger.error(f"Excel 수집 로그인 실패 (시도 {attempt + 1}/{self.max_retries})")
                    time.sleep(self.retry_delay)
                    continue
                
                # Excel 다운로드
                result = self._download_excel_data_enhanced(session, start_date, end_date)
                
                if result:
                    return result
                    
            except RequestException as e:
                logger.error(f"Excel 수집 HTTP 오류", 
                           exception=e, attempt=attempt + 1, max_attempts=self.max_retries)
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
            except Exception as e:
                logger.error(f"Excel 수집 예상치 못한 오류", 
                           exception=e, attempt=attempt + 1)
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    
        return []
    
    def _try_html_collection(self, start_date: str, end_date: str,
                            max_pages: int, page_size: int) -> List[BlacklistEntry]:
        """HTML 파싱 방식 시도"""
        for attempt in range(self.max_retries):
            self.stats.html_attempts += 1
            
            try:
                session = self._create_session()
                
                # 로그인 시도
                if not self._perform_enhanced_login(session):
                    logger.error(f"HTML 수집 로그인 실패 (시도 {attempt + 1}/{self.max_retries})")
                    time.sleep(self.retry_delay)
                    continue
                
                # HTML 수집
                result = self._collect_html_enhanced(session, start_date, end_date, max_pages, page_size)
                
                if result:
                    return result
                    
            except Exception as e:
                logger.error(f"HTML 수집 오류 (시도 {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    
        return []
    
    def _try_har_based_collection(self, start_date: str, end_date: str,
                                 max_pages: int, page_size: int) -> List[BlacklistEntry]:
        """HAR 기반 수집 방식 시도"""
        try:
            # HAR 기반 수집기 임포트 시도
            from .har_based_regtech_collector import HARBasedRegtechCollector
            
            logger.info("HAR 기반 수집기 사용 시도")
            har_collector = HARBasedRegtechCollector(self.data_dir)
            
            result = har_collector.collect_from_web(
                start_date=start_date,
                end_date=end_date,
                max_pages=max_pages
            )
            
            if result:
                logger.info(f"HAR 수집 성공: {len(result)}개")
                return result
                
        except ImportError:
            logger.warning("HAR 기반 수집기 사용 불가")
        except Exception as e:
            logger.error(f"HAR 수집 오류: {e}")
            
        return []
    
    def _create_session(self) -> requests.Session:
        """강화된 세션 생성"""
        session = requests.Session()
        
        # 기본 헤더 설정
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        })
        
        # 타임아웃 설정
        session.request = lambda *args, **kwargs: requests.Session.request(
            session, 
            *args, 
            timeout=kwargs.pop('timeout', self.session_timeout),
            **kwargs
        )
        
        return session
    
    @retry_on_error(max_attempts=3, delay=2.0, exceptions=(RequestException,))
    def _perform_enhanced_login(self, session: requests.Session) -> bool:
        """강화된 로그인 처리"""
        try:
            self.stats.auth_attempts += 1
            
            # 데이터베이스에서 인증 정보 가져오기 (우선순위: DB > 환경변수)
            try:
                from ..models.settings import get_settings_manager
                settings_manager = get_settings_manager()
                username = settings_manager.get_setting('regtech_username', settings.regtech_username)
                password = settings_manager.get_setting('regtech_password', settings.regtech_password)
                
                logger.info(f"REGTECH 인증 정보 로드 - username: {username[:3] + '***' if username else '없음'}, password: {'***' if password else '없음'}")
            except Exception as e:
                logger.warning(f"데이터베이스 설정 읽기 실패, 환경변수 사용: {e}")
                username = settings.regtech_username
                password = settings.regtech_password
            
            if not username or not password:
                logger.error("REGTECH 인증 정보 없음")
                raise CollectionError("REGTECH", "인증 정보가 설정되지 않았습니다")
            
            logger.info(f"🔐 REGTECH 로그인 시작 (사용자: {username})")
            
            # 1. 세션 초기화 - 메인 페이지 방문
            main_url = f"{self.base_url}/main/main"
            logger.debug(f"메인 페이지 접속: {main_url}")
            
            main_resp = session.get(main_url)
            if main_resp.status_code != 200:
                logger.error(f"메인 페이지 접속 실패", 
                           status_code=main_resp.status_code, url=main_url)
                raise ExternalServiceError("REGTECH", 
                                         f"메인 페이지 접속 실패: HTTP {main_resp.status_code}")
            
            time.sleep(1)
            
            # 2. 로그인 폼 접속
            login_form_url = f"{self.base_url}/login/loginForm"
            logger.debug(f"로그인 폼 접속: {login_form_url}")
            
            form_resp = session.get(login_form_url)
            if form_resp.status_code != 200:
                logger.error(f"로그인 폼 접속 실패: {form_resp.status_code}")
                return False
            
            time.sleep(1)
            
            # 3. 로그인 수행
            login_url = f"{self.base_url}/login/addLogin"
            login_data = {
                'login_error': '',
                'txId': '',
                'token': '',
                'memberId': '',
                'smsTimeExcess': 'N',
                'username': username,
                'password': password
            }
            
            login_headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': self.base_url,
                'Referer': login_form_url
            }
            
            logger.debug(f"로그인 요청: {login_url}")
            login_resp = session.post(
                login_url,
                data=login_data,
                headers=login_headers,
                allow_redirects=True
            )
            
            # 로그인 응답 분석
            if login_resp.status_code != 200:
                logger.error(f"로그인 요청 실패: {login_resp.status_code}")
                return False
            
            # 로그인 성공 여부 확인
            if 'login/loginForm' in login_resp.url:
                # 로그인 페이지로 리다이렉트 = 실패
                logger.error("로그인 실패: 로그인 페이지로 리다이렉트됨")
                
                # 에러 메시지 확인
                if 'error=true' in login_resp.url:
                    logger.error("로그인 오류: 인증 실패 (잘못된 자격증명 또는 정책 변경)")
                
                return False
            
            # Bearer Token 확인
            bearer_token = None
            for cookie in session.cookies:
                if cookie.name == 'regtech-va' and cookie.value.startswith('Bearer'):
                    bearer_token = cookie.value
                    session.headers['Authorization'] = bearer_token
                    logger.info(f"✅ Bearer Token 획득 성공 (길이: {len(bearer_token)})")
                    break
            
            if not bearer_token:
                logger.warning("Bearer Token을 찾을 수 없음 - 계속 진행")
            
            # 4. 로그인 확인 - 보안 권고 페이지 접근
            verify_url = f"{self.base_url}/fcti/securityAdvisory/advisoryList"
            verify_resp = session.get(verify_url)
            
            if verify_resp.status_code == 200:
                logger.info("✅ REGTECH 로그인 성공 확인")
                return True
            else:
                logger.error(f"로그인 확인 실패: {verify_resp.status_code}")
                return False
                
        except (Timeout, ConnectionError) as e:
            logger.error(f"REGTECH 연결 오류", exception=e)
            raise ExternalServiceError("REGTECH", f"서버 연결 실패: {str(e)}")
        except RequestException as e:
            logger.error(f"REGTECH 요청 오류", exception=e)
            raise ExternalServiceError("REGTECH", f"HTTP 요청 실패: {str(e)}")
        except Exception as e:
            logger.error(f"REGTECH 로그인 중 예상치 못한 오류", exception=e)
            raise
    
    def _download_excel_data_enhanced(self, session: requests.Session, 
                                     start_date: str, end_date: str) -> List[BlacklistEntry]:
        """강화된 Excel 다운로드"""
        try:
            excel_url = f"{self.base_url}/fcti/securityAdvisory/advisoryListDownloadXlsx"
            
            # POST 데이터
            excel_data = {
                'page': '0',
                'tabSort': 'blacklist',
                'excelDownload': 'blacklist,',
                'cveId': '',
                'ipId': '',
                'estId': '',
                'startDate': start_date,
                'endDate': end_date,
                'findCondition': 'all',
                'findKeyword': '',
                'excelDown': 'blacklist',
                'size': '10'
            }
            
            # 헤더
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Origin': self.base_url,
                'Referer': f"{self.base_url}/fcti/securityAdvisory/advisoryList"
            }
            
            logger.info(f"📥 Excel 다운로드 시도... ({start_date} ~ {end_date})")
            
            response = session.post(
                excel_url,
                data=excel_data,
                headers=headers,
                stream=True
            )
            
            if response.status_code != 200:
                logger.error(f"Excel 다운로드 실패: HTTP {response.status_code}")
                return []
            
            # Content-Type 확인
            content_type = response.headers.get('Content-Type', '')
            content_length = response.headers.get('Content-Length', '0')
            
            logger.info(f"응답 Content-Type: {content_type}, Length: {content_length}")
            
            # Excel 파일 확인
            if not any(x in content_type.lower() for x in ['excel', 'spreadsheet', 'octet-stream', 'download']):
                # HTML 응답인 경우 내용 확인
                if 'text/html' in content_type:
                    html_content = response.text[:500]
                    logger.error(f"Excel 대신 HTML 응답 받음: {html_content}")
                    
                    # 로그인 페이지로 리다이렉트된 경우
                    if 'login' in html_content.lower():
                        logger.error("세션 만료 - 재로그인 필요")
                        
                return []
            
            # Excel 파일 파싱
            try:
                excel_content = io.BytesIO(response.content)
                df = pd.read_excel(excel_content)
                
                logger.info(f"✅ Excel 로드 성공: {len(df)} 행")
                logger.info(f"컬럼: {list(df.columns)}")
                
                # IP 컬럼 찾기
                ip_column = None
                for col in df.columns:
                    if 'IP' in str(col).upper():
                        ip_column = col
                        break
                
                if not ip_column:
                    logger.error("IP 컬럼을 찾을 수 없음")
                    logger.info(f"사용 가능한 컬럼: {list(df.columns)}")
                    return []
                
                # 데이터 변환
                entries = []
                for idx, row in df.iterrows():
                    try:
                        ip = str(row[ip_column]).strip()
                        
                        if not self._is_valid_ip(ip):
                            continue
                        
                        # 다른 필드 추출
                        country = str(row.get('국가', 'Unknown')).strip()
                        reason = str(row.get('등록사유', 'REGTECH')).strip()
                        
                        # 날짜 처리
                        reg_date_raw = row.get('등록일')
                        if pd.notna(reg_date_raw):
                            if isinstance(reg_date_raw, pd.Timestamp):
                                reg_date = reg_date_raw.strftime('%Y-%m-%d')
                            else:
                                try:
                                    reg_date = pd.to_datetime(str(reg_date_raw)).strftime('%Y-%m-%d')
                                except:
                                    reg_date = datetime.now().strftime('%Y-%m-%d')
                        else:
                            reg_date = datetime.now().strftime('%Y-%m-%d')
                        
                        entry = BlacklistEntry(
                            ip_address=ip,
                            country=country,
                            reason=reason,
                            source='REGTECH',
                            reg_date=reg_date,
                            is_active=True,
                            threat_level='high',
                            source_details={'type': 'REGTECH', 'attack': reason}
                        )
                        
                        entries.append(entry)
                        
                    except Exception as e:
                        logger.debug(f"행 처리 오류: {e}, row_index: {idx}, ip: {ip if 'ip' in locals() else 'N/A'}")
                        continue
                
                # 중복 제거
                unique_entries = self._remove_duplicates(entries)
                
                logger.info(f"✅ Excel에서 {len(unique_entries)}개 고유 IP 추출")
                return unique_entries
                
            except pd.errors.ParserError as e:
                logger.error(f"Excel 파싱 오류", exception=e)
                raise CollectionError("REGTECH", "Excel 파일 파싱 실패")
            except Exception as e:
                logger.error(f"Excel 처리 중 예상치 못한 오류", exception=e)
                raise CollectionError("REGTECH", f"Excel 처리 실패: {str(e)}")
                
        except RequestException as e:
            logger.error(f"Excel 다운로드 HTTP 오류", exception=e)
            raise ExternalServiceError("REGTECH", f"Excel 다운로드 실패: {str(e)}")
        except Exception as e:
            logger.error(f"Excel 다운로드 중 예상치 못한 오류", exception=e)
            raise
    
    def _collect_html_enhanced(self, session: requests.Session, start_date: str, 
                              end_date: str, max_pages: int, page_size: int) -> List[BlacklistEntry]:
        """강화된 HTML 수집"""
        collected_ips = []
        
        for page in range(max_pages):
            try:
                logger.info(f"📄 HTML 페이지 {page + 1}/{max_pages} 수집 중...")
                
                # POST 데이터
                post_data = {
                    'page': str(page),
                    'tabSort': 'blacklist',
                    'excelDownload': '',
                    'cveId': '',
                    'ipId': '',
                    'estId': '',
                    'startDate': start_date,
                    'endDate': end_date,
                    'findCondition': 'all',
                    'findKeyword': '',
                    'size': '1000'  # 페이지당 1000개 요청
                }
                
                # 헤더
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': f"{self.base_url}/fcti/securityAdvisory/advisoryList"
                }
                
                response = session.post(
                    f"{self.base_url}/fcti/securityAdvisory/advisoryList",
                    data=post_data,
                    headers=headers
                )
                
                if response.status_code != 200:
                    logger.error(f"페이지 {page + 1} 요청 실패: {response.status_code}")
                    break
                
                # HTML 파싱
                page_entries = self._parse_html_enhanced(response.text)
                
                if page_entries:
                    collected_ips.extend(page_entries)
                    logger.info(f"페이지 {page + 1}: {len(page_entries)}개 IP 수집")
                    
                    # 마지막 페이지 확인
                    if len(page_entries) < page_size:
                        logger.info("마지막 페이지 도달")
                        break
                else:
                    logger.warning(f"페이지 {page + 1}: 데이터 없음")
                    break
                    
                # 과도한 요청 방지
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"페이지 {page + 1} 수집 오류: {e}")
                self.stats.error_count += 1
                break
        
        # 중복 제거
        unique_entries = self._remove_duplicates(collected_ips)
        
        logger.info(f"HTML 수집 완료: {len(unique_entries)}개 고유 IP")
        return unique_entries
    
    def _parse_html_enhanced(self, html_content: str) -> List[BlacklistEntry]:
        """강화된 HTML 파싱"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            entries = []
            
            # 다양한 테이블 구조 시도
            tables = soup.find_all('table')
            
            for table in tables:
                # 요주의 IP 테이블 찾기
                caption = table.find('caption')
                if caption and '요주의' in caption.text:
                    logger.debug("요주의 IP 테이블 발견")
                    
                    # tbody 찾기
                    tbody = table.find('tbody')
                    rows = tbody.find_all('tr') if tbody else table.find_all('tr')[1:]
                    
                    for row in rows:
                        cells = row.find_all('td')
                        
                        if len(cells) >= 4:  # 최소 필요 컬럼 수
                            try:
                                ip = cells[0].get_text(strip=True)
                                
                                if not self._is_valid_ip(ip):
                                    continue
                                
                                country = cells[1].get_text(strip=True) if len(cells) > 1 else 'Unknown'
                                reason = cells[2].get_text(strip=True) if len(cells) > 2 else 'REGTECH'
                                reg_date = cells[3].get_text(strip=True) if len(cells) > 3 else datetime.now().strftime('%Y-%m-%d')
                                
                                entry = BlacklistEntry(
                                    ip_address=ip,
                                    country=country,
                                    reason=reason,
                                    source='REGTECH',
                                    reg_date=reg_date,
                                    is_active=True,
                                    threat_level='high'
                                )
                                
                                entries.append(entry)
                                
                            except Exception as e:
                                logger.debug(f"HTML 행 파싱 오류: {e}, row_data: {str(cells)[:100]}")
                                continue
            
            # 결과가 없으면 다른 구조 시도
            if not entries:
                # div 기반 구조 등 대체 파싱 시도
                logger.debug("테이블 구조를 찾지 못함, 대체 구조 검색")
                
                # IP 패턴으로 직접 검색
                ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
                potential_ips = ip_pattern.findall(html_content)
                
                for ip in potential_ips[:10]:  # 최대 10개만 확인
                    if self._is_valid_ip(ip):
                        logger.debug(f"패턴 매칭으로 IP 발견: {ip}")
            
            return entries
            
        except Exception as e:
            logger.error(f"HTML 파싱 중 예상치 못한 오류", exception=e)
            raise CollectionError("REGTECH", f"HTML 파싱 실패: {str(e)}")
    
    def _is_valid_ip(self, ip: str) -> bool:
        """IP 유효성 검증 (강화)"""
        try:
            if not ip or not isinstance(ip, str):
                return False
            
            # 기본 형식 검증
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            
            # 각 부분 검증
            for part in parts:
                try:
                    num = int(part)
                    if not 0 <= num <= 255:
                        return False
                except ValueError:
                    return False
            
            # 특수 IP 제외
            if parts[0] in ['0', '127', '255']:
                return False
            
            # 사설 IP 제외
            if parts[0] == '10':
                return False
            if parts[0] == '192' and parts[1] == '168':
                return False
            if parts[0] == '172' and 16 <= int(parts[1]) <= 31:
                return False
            
            return True
            
        except Exception:
            return False
    
    def _remove_duplicates(self, entries: List[BlacklistEntry]) -> List[BlacklistEntry]:
        """중복 제거"""
        unique_entries = []
        seen_ips = set()
        
        for entry in entries:
            if entry.ip_address not in seen_ips:
                unique_entries.append(entry)
                seen_ips.add(entry.ip_address)
            else:
                self.stats.duplicate_count += 1
        
        if self.stats.duplicate_count > 0:
            logger.info(f"중복 제거: {self.stats.duplicate_count}개")
        
        return unique_entries
    
    def _log_collection_summary(self):
        """수집 요약 로그"""
        duration = self.stats.end_time - self.stats.start_time
        
        logger.info("=" * 60)
        logger.info("📊 REGTECH 수집 요약")
        logger.info(f"  - 수집 방법: {self.stats.source_method}")
        logger.info(f"  - 총 수집 IP: {self.stats.total_collected}개")
        logger.info(f"  - 중복 제거: {self.stats.duplicate_count}개")
        logger.info(f"  - 소요 시간: {duration}")
        logger.info(f"  - 인증 시도: {self.stats.auth_attempts}회")
        logger.info(f"  - Excel 시도: {self.stats.excel_attempts}회")
        logger.info(f"  - HTML 시도: {self.stats.html_attempts}회")
        logger.info(f"  - 오류 횟수: {self.stats.error_count}회")
        logger.info("=" * 60)
    
    def _log_failure_details(self):
        """실패 상세 로그"""
        logger.error("=" * 60)
        logger.error("❌ REGTECH 수집 실패 상세")
        logger.error(f"  - 인증 시도: {self.stats.auth_attempts}회")
        logger.error(f"  - Excel 시도: {self.stats.excel_attempts}회")
        logger.error(f"  - HTML 시도: {self.stats.html_attempts}회")
        logger.error(f"  - 마지막 오류: {self.stats.last_error}")
        logger.error("=" * 60)


def create_enhanced_regtech_collector(data_dir: str, cache_backend=None) -> EnhancedRegtechCollector:
    """Enhanced REGTECH 수집기 팩토리 함수"""
    return EnhancedRegtechCollector(data_dir, cache_backend)