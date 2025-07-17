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
import io
import tempfile

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logging.warning("pandas not available - Excel download will not work")

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
        
        # REGTECH API 설정 (쿠키 기반 인증)
        self.base_url = "https://regtech.fsec.or.kr"
        self.advisory_endpoint = "/fcti/securityAdvisory/advisoryList"
        
        # 쿠키 설정 (e.ps1에서 추출한 값들)
        self.cookies = {
            '_ga': 'GA1.1.1689204774.1752555033',
            'regtech-front': '2F3B7CE1B26084FCD546BDB56CE9ABAC',
            'regtech-va': 'BearereyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJuZXh0cmFkZSIsIm9yZ2FubmFtZSI6IuuEpeyKpO2KuOugiOydtOuTnCIsImlkIjoibmV4dHJhZGUiLCJleHAiOjE3NTI4Mjk2NDUsInVzZXJuYW1lIjoi7J6l7ZmN7KSAIn0.ha36VHXTf1AnziAChasI68mh9nrDawyrKRXyXKV6liPCOA1MFnoR5kTg3pSw3RNM_zkDD2NnfX5PcbdzwPET1w',
            '_ga_7WRDYHF66J': 'GS2.1.s1752743223$o3$g1$t1752746099$j38$l0$h0'
        }
        
        # 수집 통계
        self.stats = RegtechCollectionStats(start_time=datetime.now())
        
        logger.info(f"REGTECH 수집기 초기화 완료 (쿠키 기반 인증): {self.regtech_dir}")
    
    def collect_from_web(self, max_pages: int = 5, page_size: int = 100, 
                        parallel_workers: int = 1, start_date: str = None, 
                        end_date: str = None) -> List[BlacklistEntry]:
        """
        REGTECH Excel 다운로드 방식으로 데이터 수집
        """
        logger.info(f"🔄 REGTECH Excel 다운로드 수집 시작")
        logger.info(f"📝 수집 진행 상황을 상세히 로깅합니다")
        
        # 일일 수집 여부 확인
        is_daily_collection = False
        
        # 기본 날짜 설정 (파라미터로 제공되지 않은 경우)
        if not start_date or not end_date:
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=90)  # 90일로 확대
            start_date = start_dt.strftime('%Y%m%d')
            end_date = end_dt.strftime('%Y%m%d')
        else:
            # 시작일과 종료일이 같으면 일일 수집
            if start_date == end_date:
                is_daily_collection = True
                logger.info(f"📅 일일 자동 수집 모드: {start_date} 하루 데이터만 수집")
        
        logger.info(f"📆 REGTECH 수집 날짜 범위: {start_date} ~ {end_date}")
        
        if is_daily_collection:
            logger.info(f"🔔 일일 수집 실행 중 - 금일({start_date}) 신규 탐지 IP만 수집합니다")
        
        self.stats = RegtechCollectionStats(
            start_time=datetime.now(),
            source_method="excel_download"
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
            logger.info("🔐 REGTECH 로그인 시도 중...")
            if not self._perform_login(session):
                logger.error("❌ REGTECH 로그인 실패")
                return []
            logger.info("✅ REGTECH 로그인 성공")
            
            # Excel 다운로드 방식으로 데이터 수집
            logger.info("📊 Excel 데이터 다운로드 시작...")
            collected_ips = self._download_excel_data(session, start_date, end_date)
            logger.info(f"📋 Excel 데이터 다운로드 완료: {len(collected_ips)}개 IP 수집")
            
            if collected_ips:
                self.stats.total_collected = len(collected_ips)
                self.stats.successful_collections = len(collected_ips)
                self.stats.end_time = datetime.now()
                
                # 일일 수집 여부 확인
                if start_date == end_date:
                    logger.info(f"✅ REGTECH 일일 수집 완료 ({start_date}): {len(collected_ips)}개 신규 IP 추가")
                    logger.info(f"📊 금일 탐지 통계:")
                    logger.info(f"   - 신규 탐지 IP: {len(collected_ips)}개")
                    logger.info(f"   - 수집 시간: {self.stats.end_time - self.stats.start_time}")
                else:
                    logger.info(f"✅ REGTECH Excel 수집 완료: {len(collected_ips)}개 IP")
                return collected_ips
            else:
                # Excel 다운로드 실패시 기존 HTML 파싱 방식 시도
                logger.warning("Excel 다운로드 실패, HTML 파싱 방식으로 재시도")
                return self._collect_html_fallback(session, start_date, end_date, max_pages, page_size)
            
        except Exception as e:
            logger.error(f"REGTECH 수집 중 오류: {e}")
            self.stats.error_count += 1
            return []
    
    def _parse_html_response(self, html_content: str) -> List[BlacklistEntry]:
        """
        HAR 분석 기반 HTML 응답 파싱 - 실제 REGTECH 테이블 구조 기반
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            ip_entries = []
            
            # REGTECH 요주의 IP 테이블 찾기
            tables = soup.find_all('table')
            
            for table in tables:
                # caption이 "요주의 IP 목록"인 테이블 찾기
                caption = table.find('caption')
                if caption and '요주의 IP' in caption.text:
                    logger.info("📋 요주의 IP 테이블 발견")
                    
                    # tbody의 모든 tr 찾기
                    tbody = table.find('tbody')
                    if tbody:
                        rows = tbody.find_all('tr')
                        logger.info(f"📊 테이블에서 {len(rows)}개의 행 발견")
                        
                        for row in rows:
                            cells = row.find_all('td')
                            
                            # REGTECH 테이블 구조: IP, 국가, 등록사유, 등록일, 해제일, 조회수
                            if len(cells) >= 6:
                                try:
                                    ip_text = cells[0].get_text(strip=True)
                                    country = cells[1].get_text(strip=True)
                                    
                                    # 등록사유에서 attack_type 추출
                                    reason_cell = cells[2]
                                    attack_type = reason_cell.get_text(strip=True)
                                    
                                    # 날짜 정보
                                    detection_date = cells[3].get_text(strip=True)
                                    release_date = cells[4].get_text(strip=True) if len(cells) > 4 else ''
                                    views = cells[5].get_text(strip=True) if len(cells) > 5 else '0'
                                    
                                    # IP 주소 유효성 검증
                                    if self._is_valid_ip(ip_text):
                                        # extra_data에 추가 정보 저장
                                        extra_data = {
                                            'release_date': release_date,
                                            'views': views
                                        }
                                        
                                        ip_entry = BlacklistEntry(
                                            ip_address=ip_text,
                                            country=country,
                                            reason=attack_type,
                                            source='REGTECH',
                                            reg_date=detection_date,
                                            exp_date=release_date,
                                            is_active=True,
                                            threat_level='high',
                                            source_details={'type': 'REGTECH', 'attack': attack_type}
                                        )
                                        ip_entries.append(ip_entry)
                                        logger.debug(f"IP 수집: {ip_text} ({country}) - {attack_type}")
                                
                                except Exception as e:
                                    logger.debug(f"행 파싱 중 오류 (무시): {e}")
                                    continue
                    else:
                        # tbody가 없는 경우 모든 tr 검색
                        rows = table.find_all('tr')
                        for row in rows[1:]:  # 헤더 제외
                            cells = row.find_all('td')
                            if len(cells) >= 4:
                                try:
                                    ip_text = cells[0].get_text(strip=True)
                                    if self._is_valid_ip(ip_text):
                                        country = cells[1].get_text(strip=True) if len(cells) > 1 else 'Unknown'
                                        attack_type = cells[2].get_text(strip=True) if len(cells) > 2 else 'REGTECH'
                                        detection_date = cells[3].get_text(strip=True) if len(cells) > 3 else datetime.now().strftime('%Y-%m-%d')
                                        
                                        ip_entry = BlacklistEntry(
                                            ip_address=ip_text,
                                            country=country,
                                            reason=attack_type,
                                            source='REGTECH',
                                            reg_date=detection_date,
                                            is_active=True,
                                            threat_level='high'
                                        )
                                        ip_entries.append(ip_entry)
                                except Exception as e:
                                    logger.debug(f"행 파싱 중 오류 (무시): {e}")
                                    continue
            
            # 테이블을 찾지 못한 경우 경고
            if not ip_entries:
                logger.warning("요주의 IP 테이블을 찾지 못했거나 데이터가 없음")
                
                # 디버깅을 위해 총 건수 확인
                total_elem = soup.find('em')
                if total_elem:
                    total_text = total_elem.get_text(strip=True)
                    logger.info(f"페이지에 표시된 총 건수: {total_text}")
            
            return ip_entries
            
        except Exception as e:
            logger.error(f"HTML 파싱 중 오류: {e}")
            return []
    
    def _perform_login(self, session: requests.Session) -> bool:
        """REGTECH 쿠키 기반 인증 설정 (e.ps1 방식)"""
        try:
            logger.info("REGTECH 쿠키 기반 인증 설정 시작")
            
            # 기존 쿠키 설정
            for name, value in self.cookies.items():
                session.cookies.set(name, value, domain='.regtech.fsec.or.kr')
            
            # 추가 헤더 설정
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin'
            })
            
            # 쿠키 유효성 간단 테스트
            test_resp = session.get(f"{self.base_url}/fcti/securityAdvisory/advisoryList", timeout=30)
            if test_resp.status_code == 200:
                logger.info("REGTECH 쿠키 기반 인증 성공")
                return True
            else:
                logger.error(f"REGTECH 쿠키 인증 실패: {test_resp.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"REGTECH 쿠키 인증 중 오류: {e}")
            return False
            
            logger.info(f"REGTECH 로그인 시작: {username}")
            
            # 1. 메인 페이지 접속 (세션 초기화)
            main_resp = session.get(f"{self.base_url}/main/main", timeout=30)
            if main_resp.status_code != 200:
                logger.error(f"메인 페이지 접속 실패: {main_resp.status_code}")
                return False
            time.sleep(1)
            
            # 2. 로그인 폼 접속
            form_resp = session.get(f"{self.base_url}/login/loginForm", timeout=30)
            if form_resp.status_code != 200:
                logger.error(f"로그인 폼 접속 실패: {form_resp.status_code}")
                return False
            time.sleep(1)
            
            # 3. 실제 로그인 수행
            login_data = {
                'login_error': '',
                'txId': '',
                'token': '',
                'memberId': '',
                'smsTimeExcess': 'N',
                'username': username,
                'password': password
            }
            
            login_resp = session.post(
                f"{self.base_url}/login/addLogin",
                data=login_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Origin': self.base_url,
                    'Referer': f"{self.base_url}/login/loginForm"
                },
                allow_redirects=True,
                timeout=30
            )
            
            if login_resp.status_code != 200:
                logger.error(f"로그인 요청 실패: {login_resp.status_code}")
                return False
            
            # Bearer Token 확인 및 Authorization 헤더 설정
            bearer_token = None
            for cookie in session.cookies:
                if cookie.name == 'regtech-va' and cookie.value.startswith('Bearer'):
                    bearer_token = cookie.value
                    session.headers['Authorization'] = bearer_token
                    logger.info("Bearer Token 획득 및 헤더 설정 완료")
                    break
            
            if not bearer_token:
                logger.error("Bearer Token을 찾을 수 없음")
                return False
            
            # 자동 인증 모듈에 토큰 저장
            try:
                from .regtech_auto_login import get_regtech_auth
                auth = get_regtech_auth()
                auth._current_token = bearer_token
                auth._save_token_to_file(bearer_token)
            except:
                pass
            
            logger.info("REGTECH 로그인 성공")
            return True
                
        except Exception as e:
            logger.error(f"REGTECH 로그인 중 오류: {e}")
            return False
    
    def _download_excel_data(self, session: requests.Session, start_date: str, end_date: str) -> List[BlacklistEntry]:
        """Excel 파일 다운로드 방식으로 데이터 수집"""
        if not PANDAS_AVAILABLE:
            logger.error("pandas가 설치되지 않아 Excel 다운로드를 사용할 수 없습니다")
            return []
        
        try:
            # Excel 다운로드 엔드포인트
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
            
            # 추가 헤더
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Origin': self.base_url,
                'Referer': f"{self.base_url}/fcti/securityAdvisory/advisoryList",
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin'
            }
            
            # 일일 수집 여부 확인
            is_daily = (start_date == end_date)
            if is_daily:
                logger.info(f"📅 일일 수집 모드 - {start_date} 하루 데이터만 다운로드")
            
            logger.info(f"📥 Excel 파일 다운로드 중... (기간: {start_date} ~ {end_date})")
            response = session.post(
                excel_url,
                data=excel_data,
                headers=headers,
                timeout=60,
                stream=True
            )
            
            if response.status_code == 200:
                # Excel 파일인지 확인
                content_type = response.headers.get('Content-Type', '')
                if 'excel' in content_type or 'spreadsheet' in content_type or 'octet-stream' in content_type or not content_type:
                    # 메모리에서 Excel 파일 읽기
                    excel_content = io.BytesIO(response.content)
                    
                    try:
                        df = pd.read_excel(excel_content)
                        logger.info(f"✅ Excel 데이터 로드 성공: {len(df)} 행")
                        
                        if is_daily:
                            logger.info(f"📊 일일 수집 결과: {start_date}에 탐지된 {len(df)}개 IP 발견")
                        
                        # IP 컬럼 찾기
                        ip_column = None
                        logger.info(f"Excel 컬럼 목록: {list(df.columns)}")
                        for col in df.columns:
                            if 'IP' in col.upper() or 'ip' in col:
                                ip_column = col
                                logger.info(f"IP 컬럼 발견: '{col}'")
                                break
                        
                        if not ip_column:
                            logger.error("Excel 파일에서 IP 컬럼을 찾을 수 없습니다")
                            return []
                        
                        # BlacklistEntry 객체로 변환
                        ip_entries = []
                        invalid_count = 0
                        logger.info(f"IP 처리 시작 (총 {len(df)}개)")
                        
                        for idx, row in df.iterrows():
                            try:
                                ip = str(row[ip_column]).strip()
                                
                                # IP 유효성 검증
                                if not self._is_valid_ip(ip):
                                    invalid_count += 1
                                    if invalid_count <= 5:
                                        logger.debug(f"무효한 IP: '{ip}' (행 {idx})")
                                    continue
                                
                                # 다른 컬럼 데이터 추출
                                country = str(row.get('국가', 'Unknown')).strip()
                                attack_type = str(row.get('등록사유', 'REGTECH')).strip()
                                
                                # 원본 등록일 파싱 (Excel에서 실제 날짜 컬럼 사용)
                                detection_date_raw = row.get('등록일')
                                if pd.notna(detection_date_raw):
                                    if isinstance(detection_date_raw, pd.Timestamp):
                                        detection_date = detection_date_raw.strftime('%Y-%m-%d')
                                    else:
                                        # 문자열인 경우 파싱 시도
                                        try:
                                            parsed_date = pd.to_datetime(str(detection_date_raw))
                                            detection_date = parsed_date.strftime('%Y-%m-%d')
                                        except:
                                            detection_date = datetime.now().strftime('%Y-%m-%d')
                                else:
                                    detection_date = datetime.now().strftime('%Y-%m-%d')
                                
                                release_date_raw = row.get('해제일')
                                if pd.notna(release_date_raw):
                                    if isinstance(release_date_raw, pd.Timestamp):
                                        release_date = release_date_raw.strftime('%Y-%m-%d')
                                    else:
                                        release_date = str(release_date_raw).strip()
                                else:
                                    release_date = ''
                                
                                # extra_data
                                extra_data = {
                                    'release_date': release_date,
                                    'excel_row': idx + 1
                                }
                                
                                entry = BlacklistEntry(
                                    ip_address=ip,
                                    country=country,
                                    reason=attack_type,
                                    source='REGTECH',
                                    reg_date=detection_date,
                                    exp_date=release_date,
                                    is_active=True,
                                    threat_level='high',
                                    source_details={'type': 'REGTECH', 'attack': attack_type}
                                )
                                
                                ip_entries.append(entry)
                                if len(ip_entries) <= 5:
                                    logger.info(f"IP 추가됨: {ip} ({country}) - {attack_type}")
                                
                            except Exception as e:
                                logger.warning(f"행 {idx} 처리 중 오류: {e}")
                                if idx < 5:  # 처음 5개만 자세히 기록
                                    import traceback
                                    logger.warning(f"상세 오류: {traceback.format_exc()}")
                                continue
                        
                        # 중복 제거
                        unique_ips = []
                        seen_ips = set()
                        
                        for entry in ip_entries:
                            if entry.ip_address not in seen_ips:
                                unique_ips.append(entry)
                                seen_ips.add(entry.ip_address)
                            else:
                                self.stats.duplicate_count += 1
                        
                        # 일일 수집 통계 로그
                        if is_daily:
                            logger.info(f"📊 {start_date} 일일 수집 상세 통계:")
                            logger.info(f"   - 전체 행 수: {len(df)}개")
                            logger.info(f"   - 유효한 IP: {len(unique_ips)}개")
                            logger.info(f"   - 중복 제거: {self.stats.duplicate_count}개")
                            logger.info(f"   - 무효한 IP: {invalid_count}개")
                            
                            # 국가별 통계
                            if unique_ips:
                                country_stats = {}
                                for entry in unique_ips:
                                    country = entry.country or 'Unknown'
                                    country_stats[country] = country_stats.get(country, 0) + 1
                                
                                logger.info(f"   - 국가별 분포:")
                                for country, count in sorted(country_stats.items(), key=lambda x: x[1], reverse=True)[:5]:
                                    logger.info(f"     • {country}: {count}개")
                        else:
                            logger.info(f"Excel에서 {len(unique_ips)}개 고유 IP 추출 (중복 {self.stats.duplicate_count}개 제거)")
                            logger.info(f"무효한 IP 수: {invalid_count}")
                        
                        if len(unique_ips) == 0:
                            logger.warning(f"⚠️ IP가 하나도 추출되지 않음. 전체 {len(df)}행 중 무효 {invalid_count}개")
                        return unique_ips
                        
                    except Exception as e:
                        logger.error(f"Excel 파일 파싱 오류: {e}")
                        return []
                else:
                    logger.error(f"Excel이 아닌 응답 타입: {content_type}")
                    return []
            else:
                logger.error(f"Excel 다운로드 실패: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Excel 다운로드 중 오류: {e}")
            return []
    
    def _collect_html_fallback(self, session: requests.Session, start_date: str, end_date: str, 
                               max_pages: int, page_size: int) -> List[BlacklistEntry]:
        """HTML 파싱 방식 폴백"""
        logger.info("HTML 파싱 방식으로 수집 시도")
        collected_ips = []
        
        for page in range(max_pages):
            logger.info(f"REGTECH 페이지 {page + 1}/{max_pages} 수집 중...")
            
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
                'size': str(page_size)
            }
            
            response = session.post(
                f"{self.base_url}{self.advisory_endpoint}",
                data=collection_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': f"{self.base_url}{self.advisory_endpoint}"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                page_ips = self._parse_html_response(response.text)
                
                if page_ips:
                    collected_ips.extend(page_ips)
                    self.stats.pages_processed += 1
                    logger.info(f"페이지 {page + 1}: {len(page_ips)}개 IP 수집")
                else:
                    logger.warning(f"페이지 {page + 1}: IP 데이터 없음")
                    break
            else:
                logger.error(f"페이지 {page + 1} 요청 실패: {response.status_code}")
                break
        
        # 중복 제거
        unique_ips = []
        seen_ips = set()
        
        for ip_entry in collected_ips:
            if ip_entry.ip_address not in seen_ips:
                unique_ips.append(ip_entry)
                seen_ips.add(ip_entry.ip_address)
            else:
                self.stats.duplicate_count += 1
        
        return unique_ips
    
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