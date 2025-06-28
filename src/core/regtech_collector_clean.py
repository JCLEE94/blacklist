#!/usr/bin/env python3
"""
REGTECH 자동 수집 시스템 - HAR 분석 기반 정리된 버전
"""

import os
import json
import logging
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path
import threading
from dataclasses import dataclass
import re
from bs4 import BeautifulSoup

from src.core.models import BlacklistEntry
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
    REGTECH 자동 수집 시스템 - HAR 분석 기반 구현
    """
    
    def __init__(self, data_dir: str, cache_backend=None):
        self.data_dir = data_dir
        self.regtech_dir = os.path.join(data_dir, 'regtech')
        
        # 디렉토리 생성
        os.makedirs(self.regtech_dir, exist_ok=True)
        
        # REGTECH API 설정
        self.base_url = settings.regtech_base_url
        self.advisory_endpoint = "/fcti/securityAdvisory/advisoryList"
        
        # 수집 통계
        self.stats = RegtechCollectionStats(start_time=datetime.now())
        
        logger.info(f"REGTECH 수집기 초기화 완료: {self.regtech_dir}")
    
    def collect_from_web(self, max_pages: int = 5, page_size: int = 100, 
                        parallel_workers: int = 1, start_date: str = None, 
                        end_date: str = None) -> List[BlacklistEntry]:
        """
        실시간 웹 크롤링으로 REGTECH 데이터 수집 - HAR 분석 기반 구현
        """
        logger.info(f"REGTECH 웹 수집 시작 (HAR 분석 기반)")
        
        # 기본 날짜 설정 (파라미터로 제공되지 않은 경우)
        if not start_date or not end_date:
            from datetime import datetime, timedelta
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=30)  # 30일로 설정
            start_date = start_dt.strftime('%Y%m%d')
            end_date = end_dt.strftime('%Y%m%d')
        
        logger.info(f"REGTECH 수집 날짜 범위: {start_date} ~ {end_date}")
        
        self.stats = RegtechCollectionStats(
            start_time=datetime.now(),
            source_method="web_crawling"
        )
        
        try:
            # 세션 생성 및 로그인
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            })
            
            # 로그인 수행
            if not self._perform_login(session):
                logger.error("REGTECH 로그인 실패")
                return []
            
            # HAR 분석 기반 데이터 수집
            collected_ips = []
            
            for page in range(max_pages):
                logger.info(f"REGTECH 페이지 {page + 1}/{max_pages} 수집 중...")
                
                # HAR에서 확인된 정확한 POST 파라미터
                collection_data = {
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
                    'excelDown': 'security',
                    'size': str(page_size)
                }
                
                # POST 요청
                response = session.post(
                    f"{self.base_url}{self.advisory_endpoint}",
                    data=collection_data,
                    headers={
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Referer': f"{self.base_url}{self.advisory_endpoint}"
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    # BeautifulSoup으로 HTML 파싱
                    page_ips = self._parse_html_response(response.text)
                    
                    if page_ips:
                        collected_ips.extend(page_ips)
                        self.stats.pages_processed += 1
                        logger.info(f"페이지 {page + 1}: {len(page_ips)}개 IP 수집")
                    else:
                        logger.warning(f"페이지 {page + 1}: IP 데이터 없음")
                        break  # 더 이상 데이터가 없으면 중단
                else:
                    logger.error(f"페이지 {page + 1} 요청 실패: {response.status_code}")
                    break
            
            # 중복 제거
            unique_ips = []
            seen_ips = set()
            
            for ip_entry in collected_ips:
                if ip_entry.ip not in seen_ips:
                    unique_ips.append(ip_entry)
                    seen_ips.add(ip_entry.ip)
                else:
                    self.stats.duplicate_count += 1
            
            self.stats.total_collected = len(unique_ips)
            self.stats.successful_collections = len(unique_ips)
            self.stats.end_time = datetime.now()
            
            logger.info(f"REGTECH 수집 완료: {len(unique_ips)}개 고유 IP (중복 {self.stats.duplicate_count}개 제거)")
            
            return unique_ips
            
        except Exception as e:
            logger.error(f"REGTECH 웹 수집 중 오류: {e}")
            self.stats.error_count += 1
            return []
    
    def _parse_html_response(self, html_content: str) -> List[BlacklistEntry]:
        """
        HAR 분석 기반 HTML 응답 파싱
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            ip_entries = []
            
            # 테이블에서 IP 데이터 추출
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                
                for row in rows:
                    cells = row.find_all('td')
                    
                    if len(cells) >= 4:  # IP, Country, Attack Type, Date 등이 있는 행
                        try:
                            ip_text = cells[0].get_text(strip=True)
                            country = cells[1].get_text(strip=True) if len(cells) > 1 else 'Unknown'
                            attack_type = cells[2].get_text(strip=True) if len(cells) > 2 else 'REGTECH'
                            detection_date = cells[3].get_text(strip=True) if len(cells) > 3 else datetime.now().strftime('%Y-%m-%d')
                            
                            # IP 주소 유효성 검증
                            if self._is_valid_ip(ip_text):
                                ip_entry = BlacklistEntry(
                                    ip=ip_text,
                                    country=country,
                                    attack_type=attack_type,
                                    source='REGTECH',
                                    detection_date=detection_date,
                                    description=f"REGTECH 위협정보: {attack_type}"
                                )
                                ip_entries.append(ip_entry)
                        
                        except Exception as e:
                            logger.debug(f"행 파싱 중 오류 (무시): {e}")
                            continue
            
            # 테이블 외부에서 IP 패턴 검색 (fallback)
            if not ip_entries:
                import re
                ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
                found_ips = re.findall(ip_pattern, html_content)
                
                for ip in found_ips:
                    if self._is_valid_ip(ip):
                        ip_entry = BlacklistEntry(
                            ip=ip,
                            country='Unknown',
                            attack_type='REGTECH',
                            source='REGTECH',
                            detection_date=datetime.now().strftime('%Y-%m-%d'),
                            description="REGTECH 위협정보"
                        )
                        ip_entries.append(ip_entry)
            
            return ip_entries
            
        except Exception as e:
            logger.error(f"HTML 파싱 중 오류: {e}")
            return []
    
    def _perform_login(self, session: requests.Session) -> bool:
        """REGTECH 로그인 수행 - HAR 분석 기반 수정"""
        try:
            username = settings.regtech_username
            password = settings.regtech_password
            
            if not username or not password:
                logger.error("REGTECH 자격증명이 설정되지 않았습니다")
                return False
            
            # 1. 메인 페이지 접속
            main_resp = session.get(f"{self.base_url}/main/main", timeout=30)
            if main_resp.status_code != 200:
                logger.error(f"메인 페이지 접속 실패: {main_resp.status_code}")
                return False
            
            # 2. 로그인 폼 접속
            form_resp = session.get(f"{self.base_url}/login/loginForm", timeout=30)
            if form_resp.status_code != 200:
                logger.error(f"로그인 폼 접속 실패: {form_resp.status_code}")
                return False
            
            # 3. 실제 로그인 수행 (HAR 분석 결과 기반)
            login_data = {
                'memberId': username,
                'memberPw': password
            }
            
            login_resp = session.post(
                f"{self.base_url}/login/addLogin",
                data=login_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': f"{self.base_url}/login/loginForm"
                },
                timeout=30
            )
            
            if login_resp.status_code == 200:
                logger.info("REGTECH 로그인 성공")
                return True
            else:
                logger.error(f"REGTECH 로그인 실패: {login_resp.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"REGTECH 로그인 중 오류: {e}")
            return False
    
    def _is_valid_ip(self, ip: str) -> bool:
        """IP 주소 유효성 검증"""
        try:
            if not ip or not isinstance(ip, str):
                return False
            
            # IP 패턴 검증
            import re
            ip_pattern = re.compile(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$')
            if not ip_pattern.match(ip):
                return False
            
            # 각 옥텟 범위 검증
            parts = ip.split('.')
            for part in parts:
                if not 0 <= int(part) <= 255:
                    return False
            
            # 사설 IP 및 특수 IP 제외
            if parts[0] == '192' and parts[1] == '168':
                return False
            if parts[0] == '10':
                return False
            if parts[0] == '172' and 16 <= int(parts[1]) <= 31:
                return False
            if parts[0] in ['0', '127', '255']:
                return False
            
            return True
            
        except:
            return False


def create_regtech_collector(data_dir: str, cache_backend=None) -> RegtechCollector:
    """REGTECH 수집기 팩토리 함수"""
    return RegtechCollector(data_dir, cache_backend)