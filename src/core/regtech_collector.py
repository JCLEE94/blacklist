#!/usr/bin/env python3
"""
REGTECH 자동 수집 시스템
기존 blacklist 관리 시스템에 통합된 REGTECH 데이터 수집기
"""

import os
import sys
import json
import logging
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from dataclasses import dataclass
import zipfile
from bs4 import BeautifulSoup
import re
import uuid

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.models import BlacklistEntry
from src.utils.cache import CacheManager
from src.config.settings import settings

logger = logging.getLogger(__name__)


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


class RegtechCollector:
    """
    REGTECH 자동 수집 시스템
    - 실시간 웹 크롤링
    - ZIP 파일 분석
    - 기존 blacklist 시스템과 통합
    """
    
    def __init__(self, data_dir: str, cache_backend=None):
        self.data_dir = data_dir
        self.regtech_dir = os.path.join(data_dir, 'regtech')
        self.collection_log_dir = os.path.join(self.regtech_dir, 'logs')
        
        # 디렉토리 생성
        os.makedirs(self.regtech_dir, exist_ok=True)
        os.makedirs(self.collection_log_dir, exist_ok=True)
        
        # 캐시 및 스레드 초기화
        self.cache = CacheManager(cache_backend, default_ttl=3600)
        self._lock = threading.RLock()
        
        # REGTECH API 설정
        self.base_url = settings.regtech_base_url
        self.advisory_endpoint = "/fcti/securityAdvisory/advisoryList"
        self.blacklist_endpoint = "/fcti/securityAdvisory/blackListView"
        
        # 수집 통계
        self.stats = RegtechCollectionStats(start_time=datetime.now())
        
        logger.info(f"REGTECH 수집기 초기화 완료: {self.regtech_dir}")
    
    def collect_from_web(self, max_pages: int = 1, page_size: int = 5000, 
                        parallel_workers: int = 1, start_date: str = None, 
                        end_date: str = None) -> Dict[str, Any]:
        """
        실시간 웹 크롤링으로 전체 데이터 수집
        """
        logger.info(f"REGTECH 웹 수집 시작: {max_pages}페이지, {parallel_workers}개 동시 작업")
        
        # 기본 날짜 설정 (파라미터로 제공되지 않은 경우)
        if not start_date or not end_date:
            from datetime import datetime, timedelta
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=180)  # 6개월로 확장 (더 많은 데이터)
            start_date = start_dt.strftime('%Y%m%d')
            end_date = end_dt.strftime('%Y%m%d')
        
        logger.info(f"REGTECH 수집 날짜 범위: {start_date} ~ {end_date}")
        
        self.stats = RegtechCollectionStats(
            start_time=datetime.now(),
            source_method="web_crawling"
        )
        
        collected_data = []
        
        try:
            # 세션 준비
            session = self._prepare_session()
            
            # 단일 세션으로 순차 수집 (세션 유지 보장)
            collected_data = []
            
            for page in range(0, max_pages):
                try:
                    page_data = self._collect_page(session, page, start_date, end_date)
                    if page_data:
                        collected_data.extend(page_data)
                        self.stats.pages_processed += 1
                        self.stats.successful_collections += len(page_data)
                        
                        logger.info(f"페이지 {page} 수집 완료: {len(page_data)}개 IP")
                        
                        # 페이지 간 짧은 대기 (서버 부하 방지)
                        time.sleep(0.5)
                    else:
                        # 연속으로 빈 페이지가 나오면 종료
                        if page > 5:  # 처음 5페이지는 확인
                            logger.info(f"페이지 {page}에서 데이터 없음 - 수집 종료")
                            break
                        
                except Exception as e:
                    self.stats.failed_collections += 1
                    self.stats.error_count += 1
                    logger.error(f"페이지 {page} 수집 실패: {e}")
                    
                    # 세션 오류가 많으면 중단
                    if self.stats.error_count > 10:
                        logger.error("너무 많은 오류 발생 - 수집 중단")
                        break
            
            # 중복 제거
            unique_data = self._deduplicate_data(collected_data)
            self.stats.duplicate_count = len(collected_data) - len(unique_data)
            self.stats.total_collected = len(unique_data)
            
            # 결과 저장
            result = self._save_collection_results(unique_data, "web")
            
            self.stats.end_time = datetime.now()
            logger.info(f"REGTECH 웹 수집 완료: {self.stats.total_collected}개 수집")
            
            return result
            
        except Exception as e:
            logger.error(f"REGTECH 웹 수집 실패: {e}")
            self.stats.end_time = datetime.now()
            return {"success": False, "error": str(e), "stats": self.stats}
    
    def collect_from_zip(self, zip_path: str) -> Dict[str, Any]:
        """
        ZIP 파일에서 데이터 수집 (오프라인 방식)
        """
        logger.info(f"REGTECH ZIP 수집 시작: {zip_path}")
        
        self.stats = RegtechCollectionStats(
            start_time=datetime.now(),
            source_method="zip_file"
        )
        
        try:
            # ZIP 파일 추출 및 분석
            extracted_data = self._extract_from_zip(zip_path)
            
            if not extracted_data:
                raise DataProcessingError("ZIP 파일에서 데이터 추출 실패")
            
            # 중복 제거
            unique_data = self._deduplicate_data(extracted_data)
            self.stats.duplicate_count = len(extracted_data) - len(unique_data)
            self.stats.total_collected = len(unique_data)
            self.stats.successful_collections = len(unique_data)
            
            # 결과 저장
            result = self._save_collection_results(unique_data, "zip")
            
            self.stats.end_time = datetime.now()
            logger.info(f"REGTECH ZIP 수집 완료: {self.stats.total_collected}개 수집")
            
            return result
            
        except Exception as e:
            logger.error(f"REGTECH ZIP 수집 실패: {e}")
            self.stats.end_time = datetime.now()
            return {"success": False, "error": str(e), "stats": self.stats}
    
    def collect_with_session(self, auth_token: Optional[str] = None, 
                            start_date: str = "20250501", 
                            end_date: str = "20250531") -> Dict[str, Any]:
        """
        세션 기반 REGTECH 데이터 수집 (PowerShell 스크립트 방식)
        
        Args:
            auth_token: Bearer 토큰 (regtech-va 쿠키값)
            start_date: 시작 날짜 (YYYYMMDD)
            end_date: 종료 날짜 (YYYYMMDD)
        """
        logger.info("REGTECH 세션 기반 수집 시작")
        
        self.stats = RegtechCollectionStats(
            start_time=datetime.now(),
            source_method="session_post"
        )
        
        try:
            session = requests.Session()
            
            # 쿠키 설정 (PowerShell 스크립트에서 추출)
            cookies = {
                '_ga': 'GA1.1.215465125.1748404470',
                'regtech-front': '1F18F21595469EFB208BBBBB637ECD53',
                '_ga_7WRDYHF66J': 'GS2.1.s1750114865$o8$g1$t1750115626$j53$l0$h0'
            }
            
            # 인증 토큰이 제공된 경우 사용
            if auth_token:
                cookies['regtech-va'] = f"Bearer{auth_token}"
            else:
                # 환경변수에서 토큰 찾기
                env_token = os.getenv('REGTECH_AUTH_TOKEN')
                if env_token:
                    cookies['regtech-va'] = f"Bearer{env_token}"
            
            session.cookies.update(cookies)
            
            # 헤더 설정
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'Cache-Control': 'no-cache',
                'Origin': self.base_url,
                'Pragma': 'no-cache',
                'Referer': f'{self.base_url}/fcti/securityAdvisory/advisoryList',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"'
            }
            
            session.headers.update(headers)
            
            collected_data = []
            page = 0
            max_pages = 200  # 안전장치
            
            while page < max_pages:
                # POST 요청 데이터 (PowerShell 스크립트에서 추출)
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
                    'excelDown': ['security', 'blacklist', 'weakpoint'],
                    'size': '5000'  # 대량 수집을 위한 큰 사이즈 (테스트로 확인됨)
                }
                
                try:
                    response = session.post(
                        f'{self.base_url}/fcti/securityAdvisory/advisoryList',
                        data=post_data,
                        timeout=30
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"HTTP {response.status_code}: {response.text[:200]}")
                        break
                    
                    # HTML 파싱하여 IP 데이터 추출
                    page_data = self._parse_advisory_page(response.text)
                    
                    if not page_data:
                        logger.info(f"페이지 {page}에서 더 이상 데이터가 없음")
                        break
                    
                    collected_data.extend(page_data)
                    self.stats.pages_processed += 1
                    self.stats.successful_collections += len(page_data)
                    
                    logger.info(f"페이지 {page} 수집 완료: {len(page_data)}개 항목")
                    
                    page += 1
                    time.sleep(1)  # 요청 간격
                    
                except Exception as e:
                    logger.error(f"페이지 {page} 수집 실패: {e}")
                    self.stats.failed_collections += 1
                    self.stats.error_count += 1
                    page += 1
            
            # 중복 제거 및 저장
            unique_data = self._deduplicate_data(collected_data)
            self.stats.duplicate_count = len(collected_data) - len(unique_data)
            self.stats.total_collected = len(unique_data)
            
            result = self._save_collection_results(unique_data, "session_post")
            
            self.stats.end_time = datetime.now()
            logger.info(f"REGTECH 세션 수집 완료: {self.stats.total_collected}개 수집")
            
            return result
            
        except Exception as e:
            logger.error(f"REGTECH 세션 수집 실패: {e}")
            self.stats.end_time = datetime.now()
            return {"success": False, "error": str(e), "stats": self.stats}
    
    def _parse_advisory_page(self, html_content: str) -> List[Dict[str, Any]]:
        """보안 권고 페이지에서 IP 데이터 파싱"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            data = []
            
            # 테이블에서 데이터 추출 (구체적인 선택자는 실제 HTML 구조에 따라 조정)
            rows = soup.find_all('tr')
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 3:  # 최소 3개 컬럼 필요
                    
                    # IP 주소 찾기
                    ip_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                    ip_matches = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', ip_text)
                    
                    if ip_matches:
                        for ip in ip_matches:
                            data.append({
                                'ip': ip,
                                'detection_date': datetime.now().strftime('%Y-%m-%d'),
                                'source': 'regtech_advisory',
                                'attack_type': 'various',
                                'country': 'unknown',
                                'confidence': 'high',
                                'raw_data': ip_text[:200]  # 원본 데이터 일부 저장
                            })
            
            return data
            
        except Exception as e:
            logger.error(f"HTML 파싱 오류: {e}")
            return []

    def auto_collect(self, prefer_web: bool = True, 
                    fallback_zip_path: Optional[str] = None,
                    auth_token: Optional[str] = None,
                    enhanced_mode: bool = True) -> Dict[str, Any]:
        """
        자동 수집 - 향상된 다단계 수집 전략
        """
        logger.info("REGTECH 고도화된 자동 수집 시작")
        
        collection_methods = []
        
        # 1. 세션 기반 수집 시도 (가장 정확한 방법)
        if auth_token or os.getenv('REGTECH_AUTH_TOKEN'):
            collection_methods.append(('session', self.collect_with_session, [auth_token]))
        
        # 2. 향상된 웹 수집
        if prefer_web:
            if enhanced_mode:
                collection_methods.append(('enhanced_web', self._collect_enhanced_web, []))
            collection_methods.append(('standard_web', self.collect_from_web, []))
        
        # 3. ZIP 파일 수집
        zip_paths = []
        if fallback_zip_path and os.path.exists(fallback_zip_path):
            zip_paths.append(fallback_zip_path)
        
        # 기본 ZIP 파일들 찾기
        default_zips = [
            os.path.join(self.data_dir, "regtech.fsec.or.kr.zip"),
            os.path.join("archives", "regtech.fsec.or.kr.zip"),
            os.path.join("document", "regtech.fsec.or.kr.zip")
        ]
        
        for zip_path in default_zips:
            if os.path.exists(zip_path):
                zip_paths.append(zip_path)
        
        for zip_path in zip_paths:
            collection_methods.append(('zip', self.collect_from_zip, [zip_path]))
        
        # 수집 방법들을 순차적으로 시도
        last_error = None
        for method_name, method_func, args in collection_methods:
            try:
                logger.info(f"수집 방법 시도: {method_name}")
                result = method_func(*args)
                
                if result.get("success", False) and result.get("stats", {}).get("total_collected", 0) > 0:
                    logger.info(f"수집 성공: {method_name}, {result['stats']['total_collected']}개 IP")
                    result['collection_method'] = method_name
                    return result
                else:
                    logger.warning(f"수집 방법 {method_name} 실패 또는 빈 결과")
                    
            except Exception as e:
                last_error = str(e)
                logger.error(f"수집 방법 {method_name} 예외: {e}")
                continue
        
        return {
            "success": False, 
            "error": f"모든 수집 방법 실패. 마지막 오류: {last_error}", 
            "stats": self.stats,
            "attempted_methods": [method[0] for method in collection_methods]
        }
    
    def _collect_enhanced_web(self) -> Dict[str, Any]:
        """향상된 웹 수집 - 여러 엔드포인트 시도"""
        logger.info("향상된 웹 수집 실행")
        
        # 다양한 REGTECH 엔드포인트 시도
        endpoints = [
            "/fcti/securityAdvisory/advisoryList",
            "/fcti/securityAdvisory/blackListView", 
            "/fcti/securityAdvisory/advisoryListDownloadXlsx"
        ]
        
        all_data = []
        successful_endpoints = []
        
        for endpoint in endpoints:
            try:
                logger.info(f"엔드포인트 시도: {endpoint}")
                
                # 각 엔드포인트별 맞춤 파라미터
                if "blackListView" in endpoint:
                    result = self._collect_blacklist_view()
                elif "advisoryList" in endpoint:
                    result = self.collect_from_web(max_pages=10, parallel_workers=1)
                else:
                    continue
                
                if result.get("success", False):
                    endpoint_data = result.get("data", [])
                    all_data.extend(endpoint_data)
                    successful_endpoints.append(endpoint)
                    logger.info(f"엔드포인트 {endpoint} 성공: {len(endpoint_data)}개 수집")
                
            except Exception as e:
                logger.error(f"엔드포인트 {endpoint} 실패: {e}")
                continue
        
        if all_data:
            # 중복 제거
            unique_data = self._deduplicate_data(all_data)
            self.stats.total_collected = len(unique_data)
            self.stats.successful_collections = len(unique_data)
            
            # 저장
            result = self._save_collection_results(unique_data, "enhanced_web")
            result['successful_endpoints'] = successful_endpoints
            
            return result
        
        return {"success": False, "error": "모든 엔드포인트 실패"}
    
    def _collect_blacklist_view(self) -> Dict[str, Any]:
        """BlackListView 전용 수집"""
        try:
            session = self._prepare_session()
            
            # BlackListView 페이지 접근
            response = session.get(f"{self.base_url}/fcti/securityAdvisory/blackListView")
            response.raise_for_status()
            
            # 특별한 파싱 로직 (blackListView는 다른 구조)
            data = self._parse_blacklist_view_page(response.text)
            
            return {
                "success": True,
                "data": data,
                "stats": {"total_collected": len(data)}
            }
            
        except Exception as e:
            logger.error(f"BlackListView 수집 실패: {e}")
            return {"success": False, "error": str(e)}
    
    def _parse_blacklist_view_page(self, html_content: str) -> List[Dict[str, Any]]:
        """BlackListView 페이지 전용 파싱"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            data = []
            
            # BlackListView는 다른 DOM 구조를 가질 수 있음
            # JavaScript로 동적 로딩되는 경우 대비
            
            # 1. 일반 테이블 구조 시도
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows[1:]:  # 헤더 스킵
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 1:
                        # IP 주소 찾기
                        for cell in cells:
                            text = cell.get_text(strip=True)
                            ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', text)
                            if ip_match:
                                ip = ip_match.group()
                                try:
                                    import ipaddress
                                    ipaddress.ip_address(ip)
                                    data.append({
                                        'ip': ip,
                                        'source': 'regtech_blacklistview',
                                        'collected_at': datetime.now().isoformat(),
                                        'raw_data': text[:200]
                                    })
                                except:
                                    continue
            
            # 2. JSON 데이터 찾기 (스크립트 태그 내)
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # JSON 패턴 찾기
                    json_matches = re.findall(r'\{[^{}]*"ip"[^{}]*\}', script.string)
                    for match in json_matches:
                        try:
                            json_data = json.loads(match)
                            if 'ip' in json_data:
                                data.append({
                                    'ip': json_data['ip'],
                                    'source': 'regtech_blacklistview_json',
                                    'collected_at': datetime.now().isoformat(),
                                    **json_data
                                })
                        except:
                            continue
            
            return data
            
        except Exception as e:
            logger.error(f"BlackListView 파싱 오류: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """수집 통계 반환"""
        duration = None
        if self.stats.end_time:
            duration = (self.stats.end_time - self.stats.start_time).total_seconds()
        
        return {
            "start_time": self.stats.start_time.isoformat(),
            "end_time": self.stats.end_time.isoformat() if self.stats.end_time else None,
            "duration_seconds": duration,
            "total_collected": self.stats.total_collected,
            "successful_collections": self.stats.successful_collections,
            "failed_collections": self.stats.failed_collections,
            "pages_processed": self.stats.pages_processed,
            "duplicate_count": self.stats.duplicate_count,
            "error_count": self.stats.error_count,
            "source_method": self.stats.source_method,
            "success_rate": (
                self.stats.successful_collections / max(1, self.stats.total_collected) * 100
            )
        }
    
    def _prepare_session(self) -> requests.Session:
        """HTTP 세션 준비 및 로그인"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        session.timeout = 30
        
        # 로그인 수행
        if self._perform_login(session):
            logger.info("REGTECH 로그인 성공")
        else:
            logger.warning("REGTECH 로그인 실패 - 게스트 모드로 진행")
        
        return session
    
    def _perform_login(self, session: requests.Session) -> bool:
        """REGTECH 로그인 수행 - 향상된 세션 관리"""
        try:
            # 설정에서 자격증명 가져오기
            username = settings.regtech_username
            password = settings.regtech_password
            
            if not username or not password:
                logger.warning("REGTECH 자격증명이 없습니다")
                return False
            
            logger.info(f"REGTECH 로그인 시도: {username}")
            
            # 1. 메인 페이지 접속 (세션 초기화)
            main_resp = session.get(f"{self.base_url}/main/main", timeout=30)
            if main_resp.status_code != 200:
                logger.error(f"메인 페이지 접속 실패: {main_resp.status_code}")
                return False
            
            logger.debug(f"메인 페이지 접속 성공: {main_resp.status_code}")
            
            # 2. 로그인 폼에서 hidden 필드들 가져오기
            from bs4 import BeautifulSoup
            form_resp = session.get(f"{self.base_url}/login/loginForm", timeout=30)
            soup = BeautifulSoup(form_resp.text, 'html.parser')
            
            logger.debug(f"로그인 폼 응답 상태: {form_resp.status_code}")
            
            # loginForm에서 hidden 필드들 추출
            hidden_fields = {}
            login_form = soup.find('form', {'id': 'loginForm'})
            if login_form:
                for inp in login_form.find_all('input', {'type': 'hidden'}):
                    name = inp.get('name')
                    value = inp.get('value', '')
                    if name:
                        hidden_fields[name] = value
                logger.debug(f"발견된 hidden 필드들: {hidden_fields}")
            else:
                logger.warning("loginForm을 찾을 수 없음")
            
            # 3. 실제 로그인: addLogin 엔드포인트 사용 (document 분석 결과)
            login_data = {
                'memberId': username,   # document 분석: 로그인에 사용
                'memberPw': password,   # document 분석: 패스워드
                'userType': '1',        # document 분석: 사용자 타입
                **hidden_fields        # 폼에서 추출한 hidden 필드들
            }
            
            # 헤더를 폼 제출에 맞게 변경
            session.headers.update({
                'Content-Type': 'application/x-www-form-urlencoded',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            })
            
            login_resp = session.post(
                f"{self.base_url}/login/addLogin",
                data=login_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'Referer': f"{self.base_url}/login/loginForm"
                },
                timeout=30
            )
            
            logger.debug(f"로그인 응답: {login_resp.status_code}")
            logger.debug(f"로그인 응답 내용: {login_resp.text[:500]}")
            
            # 로그인 성공 여부 판단 (문서 분석 기반)
            # 1. 응답 상태 확인
            if login_resp.status_code != 200:
                logger.error(f"로그인 요청 실패: {login_resp.status_code}")
                return False
            
            # 2. 응답 내용으로 성공/실패 판단
            response_text = login_resp.text
            final_url = login_resp.url
            
            # 로그인 실패 시 다시 로그인 페이지로 리다이렉트됨 (로그 분석 결과)
            if 'login' in final_url.lower() or '로그인' in response_text:
                logger.error(f"로그인 후 다시 로그인 페이지로 리다이렉트됨: {final_url}")
                return False
            
            # 3. JSON 응답 처리 (API 응답인 경우)
            try:
                login_result = login_resp.json()
                logger.debug(f"로그인 JSON 결과: {login_result}")
                
                # 오류 응답 체크
                if login_result.get('error') or 'error' in login_result:
                    logger.error(f"로그인 API 오류: {login_result}")
                    return False
                    
                # 성공 토큰 추출
                tx_id = login_result.get('txId')
                if tx_id:
                    logger.debug(f"트랜잭션 ID 추출: {tx_id}")
                    
            except Exception as json_err:
                logger.debug(f"JSON 파싱 실패 (HTML 응답일 수 있음): {json_err}")
                # HTML 응답도 성공일 수 있으므로 계속 진행
            
            # 인증 성공으로 간주하고 세션 상태 확인
            logger.info(f"REGTECH 1단계 인증 성공: {username}")
            return True
            
        except Exception as e:
            logger.error(f"로그인 중 오류 발생: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _collect_page(self, session: requests.Session, page: int, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """단일 페이지 수집 (블랙리스트 전용) - 향상된 세션 관리"""
        try:
            # 페이지 번호 조정 (1부터 시작)
            page_index = page + 1
            
            # 1. 먼저 advisoryList 페이지 접근 (세션 검증)
            advisory_resp = session.get(
                f"{self.base_url}/fcti/securityAdvisory/advisoryList",
                timeout=30
            )
            
            if advisory_resp.status_code != 200:
                logger.warning(f"페이지 {page}: advisory 페이지 접근 실패 ({advisory_resp.status_code})")
                return []
            
            # 로그인 페이지로 리다이렉트되었는지 확인
            if 'login' in advisory_resp.url.lower() or 'loginForm' in advisory_resp.text:
                logger.error(f"페이지 {page}: 세션 만료 - 로그인 페이지로 리다이렉트됨")
                return []
            
            # 2. 블랙리스트 데이터 POST 요청 (날짜 파라미터 추가)
            from datetime import datetime, timedelta
            
            # 기본 날짜 범위: 최근 3개월
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
            
            # 최적화된 대량 수집 방식 (테스트로 2,000개 IP 확인됨)
            post_data = {
                'page': '0',  # 첫 페이지만 사용
                'tabSort': 'blacklist',
                'startDate': start_date.strftime('%Y%m%d'),
                'endDate': end_date.strftime('%Y%m%d'),
                'findKeyword': '',
                'size': '5000'  # 대량 수집을 위한 큰 사이즈
            }
            
            # Document 분석 결과: advisoryList 엔드포인트를 사용 (실제 데이터 소스)
            response = session.post(
                f"{self.base_url}/fcti/securityAdvisory/advisoryList",
                data=post_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': f"{self.base_url}/fcti/securityAdvisory/advisoryList"
                },
                timeout=30
            )
            
            if response.status_code != 200:
                logger.warning(f"페이지 {page}: blackListView 응답 실패 ({response.status_code})")
                return []
            
            # 응답 내용 검증
            response_text = response.text
            if len(response_text) < 100:
                logger.warning(f"페이지 {page}: 응답이 너무 짧음 ({len(response_text)} bytes)")
                return []
            
            # 로그인 페이지 HTML이 반환되지 않았는지 확인
            if 'loginForm' in response_text or 'login/addLogin' in response_text:
                logger.error(f"페이지 {page}: 로그인 페이지 반환됨 - 세션 문제")
                return []
            
            logger.debug(f"페이지 {page} 수집 완료 (응답 크기: {len(response_text)} bytes)")
            
            # HTML 파싱하여 데이터 추출
            parsed_data = self._parse_blacklist_page(response_text, page)
            
            if parsed_data:
                logger.info(f"페이지 {page}: {len(parsed_data)}개 IP 추출 성공")
            else:
                logger.warning(f"페이지 {page}: 데이터 추출 실패")
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"페이지 {page} 수집 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _parse_blacklist_page(self, html_content: str, page_num: int) -> List[Dict[str, Any]]:
        """블랙리스트 페이지 전용 파싱"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            blacklist_data = []
            
            # IP 패턴 정규식
            ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
            
            # 전체 텍스트에서 IP 추출
            page_text = soup.get_text()
            ips_found = ip_pattern.findall(page_text)
            
            logger.info(f"페이지 {page_num}에서 발견된 원시 IP: {len(ips_found)}개")
            
            # 유효한 IP만 필터링
            valid_ips = []
            for ip in ips_found:
                parts = ip.split('.')
                if all(0 <= int(part) <= 255 for part in parts):
                    # 사설 IP 제외
                    if not (parts[0] == '192' and parts[1] == '168') and \
                       not (parts[0] == '10') and \
                       not (parts[0] == '172' and 16 <= int(parts[1]) <= 31):
                        valid_ips.append(ip)
            
            # 중복 제거
            unique_ips = list(set(valid_ips))
            logger.info(f"페이지 {page_num}에서 유효한 고유 IP: {len(unique_ips)}개")
            
            # BlacklistEntry 형태로 변환
            for ip in unique_ips:
                blacklist_data.append({
                    'ip': ip,
                    'country': 'Unknown',
                    'attack_type': 'REGTECH',
                    'source': 'REGTECH',
                    'detection_date': datetime.now().strftime('%Y-%m-%d'),
                    'page': page_num
                })
            
            return blacklist_data
            
        except Exception as e:
            logger.error(f"페이지 {page_num} 파싱 오류: {e}")
            return []
    
    def _parse_advisory_page(self, html_content: str) -> List[Dict[str, Any]]:
        """HTML 페이지에서 blacklist 데이터 추출 (고도화된 파싱)"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            blacklist_data = []
            
            # 다양한 테이블 구조 지원
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                
                # 헤더 행 식별 및 스킵
                data_rows = []
                for i, row in enumerate(rows):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:  # 최소 3개 컬럼 필요
                        # 헤더가 아닌 데이터 행인지 확인
                        cell_texts = [cell.get_text(strip=True) for cell in cells]
                        if not any(text.lower() in ['번호', 'no', 'ip', '국가', 'country'] for text in cell_texts[:2]):
                            data_rows.append((i, row, cells))
                
                # 데이터 행 처리
                for row_idx, row, cells in data_rows:
                    try:
                        # IP 주소 추출 (다양한 패턴 지원)
                        all_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                        ip_patterns = [
                            r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',  # 기본 IP 패턴
                            r'(?:^|\s)([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})(?:\s|$)',  # 공백으로 구분
                        ]
                        
                        found_ips = set()
                        for pattern in ip_patterns:
                            matches = re.findall(pattern, all_text)
                            found_ips.update(matches)
                        
                        if not found_ips:
                            continue
                        
                        # UUID 추출 (향상된 패턴)
                        uuid_patterns = [
                            r"goView\('([a-f0-9\-]{36})'",
                            r"'([a-f0-9\-]{36})'",
                            r"([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})"
                        ]
                        
                        uuid_value = None
                        for pattern in uuid_patterns:
                            uuid_match = re.search(pattern, str(row))
                            if uuid_match:
                                uuid_value = uuid_match.group(1)
                                break
                        
                        if not uuid_value:
                            uuid_value = str(uuid.uuid4())
                        
                        # 각 IP에 대해 데이터 생성
                        for ip in found_ips:
                            # IP 주소 유효성 검사
                            try:
                                import ipaddress
                                ipaddress.ip_address(ip)
                                
                                # 메타데이터 추출 (셀 순서에 따라 유연하게)
                                data = {
                                    'ip': ip,
                                    'uuid': uuid_value,
                                    'source': 'regtech_enhanced',
                                    'collected_at': datetime.now().isoformat(),
                                    'raw_data': all_text[:500]  # 원본 데이터 보존
                                }
                                
                                # 추가 메타데이터 추출 시도
                                if len(cells) >= 2:
                                    data['country'] = cells[1].get_text(strip=True) if len(cells) > 1 else 'unknown'
                                if len(cells) >= 3:
                                    data['reason'] = cells[2].get_text(strip=True) if len(cells) > 2 else 'unknown'
                                if len(cells) >= 4:
                                    data['reg_date'] = cells[3].get_text(strip=True) if len(cells) > 3 else ''
                                if len(cells) >= 5:
                                    data['exp_date'] = cells[4].get_text(strip=True) if len(cells) > 4 else ''
                                if len(cells) >= 6:
                                    try:
                                        data['view_count'] = int(cells[5].get_text(strip=True) or 0)
                                    except:
                                        data['view_count'] = 0
                                
                                # 위험도 평가 (고도화)
                                risk_score = self._calculate_risk_score(data)
                                data['risk_score'] = risk_score
                                data['risk_level'] = self._get_risk_level(risk_score)
                                
                                blacklist_data.append(data)
                                
                            except (ValueError, ipaddress.AddressValueError):
                                logger.warning(f"유효하지 않은 IP 주소: {ip}")
                                continue
                    
                    except Exception as e:
                        logger.error(f"행 {row_idx} 파싱 오류: {e}")
                        continue
            
            logger.info(f"HTML 파싱 완료: {len(blacklist_data)}개 IP 추출")
            return blacklist_data
            
        except Exception as e:
            logger.error(f"HTML 파싱 전체 오류: {e}")
            return []
    
    def _calculate_risk_score(self, data: Dict[str, Any]) -> int:
        """위험도 점수 계산 (0-100)"""
        score = 50  # 기본 점수
        
        # 국가별 위험도
        high_risk_countries = ['CN', 'RU', 'KP', 'IR', 'PK']
        country = data.get('country', '').upper()
        if any(risk_country in country for risk_country in high_risk_countries):
            score += 20
        
        # 이유/유형별 위험도
        reason = data.get('reason', '').lower()
        if any(keyword in reason for keyword in ['malware', 'botnet', 'c&c', 'command']):
            score += 25
        elif any(keyword in reason for keyword in ['scan', 'brute', 'attack']):
            score += 15
        
        # 조회수 기반 (인기도)
        view_count = data.get('view_count', 0)
        if view_count > 100:
            score += 10
        elif view_count > 50:
            score += 5
        
        return min(100, max(0, score))
    
    def _get_risk_level(self, score: int) -> str:
        """위험도 레벨 반환"""
        if score >= 80:
            return 'critical'
        elif score >= 60:
            return 'high'
        elif score >= 40:
            return 'medium'
        else:
            return 'low'
    
    def _extract_from_zip(self, zip_path: str) -> List[Dict[str, Any]]:
        """ZIP 파일에서 데이터 추출"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                # advisoryList.html 찾기
                advisory_file = None
                for filename in zip_file.namelist():
                    if 'advisoryList.html' in filename:
                        advisory_file = filename
                        break
                
                if not advisory_file:
                    raise FileNotFoundError("ZIP 파일에서 advisoryList.html을 찾을 수 없음")
                
                # HTML 내용 읽기
                html_content = zip_file.read(advisory_file).decode('utf-8')
                
                # 데이터 추출
                return self._parse_advisory_page(html_content)
                
        except Exception as e:
            logger.error(f"ZIP 파일 추출 오류: {e}")
            raise
    
    def _deduplicate_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """중복 데이터 제거"""
        seen_ips = set()
        unique_data = []
        
        for item in data:
            ip = item.get('ip')
            if ip and ip not in seen_ips:
                seen_ips.add(ip)
                unique_data.append(item)
        
        return unique_data
    
    def _save_collection_results(self, data: List[Dict[str, Any]], 
                               source_type: str) -> Dict[str, Any]:
        """수집 결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 파일 경로
        csv_path = os.path.join(self.regtech_dir, f"regtech_{source_type}_blacklist_{timestamp}.csv")
        json_path = os.path.join(self.regtech_dir, f"regtech_{source_type}_blacklist_{timestamp}.json")
        stats_path = os.path.join(self.collection_log_dir, f"regtech_{source_type}_stats_{timestamp}.json")
        
        try:
            # CSV 저장
            import pandas as pd
            df = pd.DataFrame(data)
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            
            # JSON 저장
            collection_result = {
                "collection_info": {
                    "timestamp": timestamp,
                    "source_type": source_type,
                    "total_count": len(data),
                    "collection_stats": self.get_collection_stats()
                },
                "blacklist_data": data
            }
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(collection_result, f, ensure_ascii=False, indent=2)
            
            # 통계 저장
            with open(stats_path, 'w', encoding='utf-8') as f:
                json.dump(self.get_collection_stats(), f, ensure_ascii=False, indent=2)
            
            logger.info(f"REGTECH 수집 결과 저장 완료: {len(data)}개")
            
            return {
                "success": True,
                "csv_path": csv_path,
                "json_path": json_path,
                "stats_path": stats_path,
                "total_count": len(data),
                "stats": self.get_collection_stats()
            }
            
        except Exception as e:
            logger.error(f"수집 결과 저장 실패: {e}")
            return {"success": False, "error": str(e)}


def create_regtech_collector(data_dir: str, cache_backend=None) -> RegtechCollector:
    """REGTECH 수집기 팩토리 함수"""
    return RegtechCollector(data_dir, cache_backend)


if __name__ == "__main__":
    # 직접 실행시 테스트
    import argparse
    
    parser = argparse.ArgumentParser(description="REGTECH 자동 수집기")
    parser.add_argument("--data-dir", default="data", help="데이터 디렉토리")
    parser.add_argument("--web", action="store_true", help="웹 수집 실행")
    parser.add_argument("--zip", help="ZIP 파일 경로")
    parser.add_argument("--max-pages", type=int, default=183, help="최대 페이지 수")
    parser.add_argument("--parallel", type=int, default=5, help="병렬 작업 수")
    
    args = parser.parse_args()
    
    # 로깅 설정
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 수집기 생성
    collector = RegtechCollector(args.data_dir)
    
    if args.web:
        result = collector.collect_from_web(args.max_pages, parallel_workers=args.parallel)
    elif args.zip:
        result = collector.collect_from_zip(args.zip)
    else:
        result = collector.auto_collect()
    
    print(json.dumps(result, indent=2, ensure_ascii=False))