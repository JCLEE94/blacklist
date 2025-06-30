#!/usr/bin/env python3
"""
SECUDIUM 수집기 - 웹 기반 수집
secudium.skinfosec.co.kr에서 실제 로그인 후 데이터 수집
"""

import os
import json
import pandas as pd
import requests
import re
import time
import warnings
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
from bs4 import BeautifulSoup
from requests.exceptions import RequestException, Timeout, ConnectionError

from src.core.models import BlacklistEntry
from src.config.settings import settings
from src.utils.error_handler import (
    CollectionError, ExternalServiceError, retry_on_error, 
    handle_api_errors, safe_execute
)
from src.utils.structured_logging import get_logger

warnings.filterwarnings('ignore', message='Unverified HTTPS request')
logger = get_logger(__name__)

class SecudiumCollector:
    """
    SECUDIUM 수집기
    - secudium.skinfosec.co.kr 사이트에서 데이터 수집
    - 로그인 후 블랙리스트 데이터 수집
    """
    
    def __init__(self, data_dir: str, cache_backend=None):
        self.data_dir = data_dir
        self.secudium_dir = os.path.join(data_dir, 'secudium')
        os.makedirs(self.secudium_dir, exist_ok=True)
        
        # SECUDIUM 웹사이트 설정 - 데이터베이스 설정 우선
        self.base_url = settings.secudium_base_url
        
        # 데이터베이스에서 인증 정보 읽기
        try:
            from ..models.settings import get_settings_manager
            settings_manager = get_settings_manager()
            self.username = settings_manager.get_setting('secudium_username', settings.secudium_username)
            self.password = settings_manager.get_setting('secudium_password', settings.secudium_password)
            
            logger.info(f"SECUDIUM 인증 정보 로드 - username: {self.username[:3] + '***' if self.username else '없음'}, password: {'***' if self.password else '없음'}")
        except Exception as e:
            logger.warning(f"데이터베이스 설정 읽기 실패, 환경변수 사용: {e}")
            self.username = settings.secudium_username
            self.password = settings.secudium_password
        
        # 세션 초기화
        self.session = None
        self.authenticated = False
        self.token = None
        
        logger.info(f"SECUDIUM 수집기 초기화 (웹 기반): {self.secudium_dir}")
    
    def collect_from_file(self, filepath: str = None) -> List[BlacklistEntry]:
        """파일에서 SECUDIUM 데이터 수집"""
        
        # 기본 파일 경로들
        if not filepath:
            possible_files = [
                os.path.join(self.data_dir, "secudium_test_data.json"),
                os.path.join(self.data_dir, "secudium_test_data.xlsx"),
                os.path.join(self.secudium_dir, "latest.json"),
                os.path.join(self.secudium_dir, "latest.xlsx"),
            ]
            
            # 존재하는 첫 번째 파일 사용
            for file in possible_files:
                if os.path.exists(file):
                    filepath = file
                    break
        
        if not filepath or not os.path.exists(filepath):
            logger.warning("SECUDIUM 데이터 파일을 찾을 수 없습니다")
            return []
        
        logger.info(f"SECUDIUM 파일 처리: {filepath}")
        
        # 파일 형식에 따라 처리
        if filepath.endswith('.json'):
            return self._process_json_file(filepath)
        elif filepath.endswith('.xlsx') or filepath.endswith('.xls'):
            return self._process_excel_file(filepath)
        else:
            logger.error(f"지원하지 않는 파일 형식: {filepath}")
            return []
    
    def _process_json_file(self, filepath: str) -> List[BlacklistEntry]:
        """JSON 파일 처리"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            entries = []
            details = data.get('details', [])
            
            for item in details:
                entry = BlacklistEntry(
                    ip_address=item.get('ip_address', item.get('ip', '')),
                    country=item.get('country', 'Unknown'),
                    reason=item.get('attack_type', 'SECUDIUM'),
                    source='SECUDIUM',
                    reg_date=self._parse_detection_date(item.get('detection_date')),
                    exp_date=None,
                    is_active=True,
                    threat_level=item.get('threat_level', 'high'),
                    source_details={
                        'type': 'SECUDIUM',
                        'attack': item.get('attack_type', 'Unknown')
                    }
                )
                entries.append(entry)
            
            logger.info(f"JSON에서 {len(entries)}개 IP 로드", file_path=filepath, count=len(entries))
            return entries
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파일 파싱 오류", 
                        exception=e, file_path=filepath, line=e.lineno, column=e.colno)
            raise CollectionError("SECUDIUM", f"잘못된 JSON 형식: {filepath}")
        except FileNotFoundError as e:
            logger.error(f"JSON 파일을 찾을 수 없음", exception=e, file_path=filepath)
            raise CollectionError("SECUDIUM", f"파일 없음: {filepath}")
        except Exception as e:
            logger.error(f"JSON 파일 처리 중 예상치 못한 오류", 
                        exception=e, file_path=filepath)
            raise CollectionError("SECUDIUM", f"파일 처리 실패: {str(e)}")
    
    def _process_excel_file(self, filepath: str) -> List[BlacklistEntry]:
        """Excel 파일 처리 - 향상된 컬럼 매핑 및 정보 추출"""
        try:
            # XLSX와 XLS 모두 지원
            if filepath.endswith('.xls'):
                df = pd.read_excel(filepath, engine='xlrd')
            else:
                df = pd.read_excel(filepath, engine='openpyxl')
            
            entries = []
            
            logger.info(f"Excel 파일 컬럼 분석 시작", file_path=filepath, columns=list(df.columns))
            
            # 컬럼 매핑 정의
            ip_columns = []
            date_columns = []
            time_columns = []
            country_columns = []
            attack_type_columns = []
            description_columns = []
            
            # 컬럼 분석 및 매핑
            for col in df.columns:
                col_str = str(col).lower()
                
                # IP 컬럼 찾기
                if any(keyword in col_str for keyword in ['ip', 'address', '주소', 'addr']):
                    ip_columns.append(col)
                
                # 날짜 컬럼 찾기
                elif any(keyword in col_str for keyword in ['date', '날짜', '일시', '시간', 'time', '탐지일시', '등록일']):
                    if any(time_keyword in col_str for time_keyword in ['time', '시간', '분', '초']):
                        time_columns.append(col)
                    else:
                        date_columns.append(col)
                
                # 국가 컬럼 찾기
                elif any(keyword in col_str for keyword in ['country', '국가', 'nation', '소재지', 'location']):
                    country_columns.append(col)
                
                # 공격유형 컬럼 찾기
                elif any(keyword in col_str for keyword in ['attack', '공격', 'type', '유형', '위험', 'threat', 'severity', '심각도']):
                    attack_type_columns.append(col)
                
                # 설명 컬럼 찾기
                elif any(keyword in col_str for keyword in ['desc', '설명', '내용', 'content', 'detail', '상세', 'info']):
                    description_columns.append(col)
            
            logger.info(f"컬럼 매핑 결과", 
                       ip_cols=ip_columns, date_cols=date_columns, time_cols=time_columns,
                       country_cols=country_columns, attack_cols=attack_type_columns, desc_cols=description_columns)
            
            if not ip_columns:
                logger.error("IP 컬럼을 찾을 수 없음", 
                           file_path=filepath, columns=list(df.columns))
                raise CollectionError("SECUDIUM", "Excel 파일에 IP 컬럼이 없습니다")
            
            # 첫 번째 IP 컬럼 사용
            ip_column = ip_columns[0]
            date_column = date_columns[0] if date_columns else None
            time_column = time_columns[0] if time_columns else None
            country_column = country_columns[0] if country_columns else None
            attack_type_column = attack_type_columns[0] if attack_type_columns else None
            description_column = description_columns[0] if description_columns else None
            
            for idx, row in df.iterrows():
                try:
                    ip = str(row[ip_column]).strip()
                    if not ip or ip == 'nan' or ip == 'None':
                        continue
                    
                    # 날짜 정보 추출
                    detection_date = None
                    detection_time = None
                    
                    if date_column and pd.notna(row[date_column]):
                        detection_date_raw = row[date_column]
                        if isinstance(detection_date_raw, pd.Timestamp):
                            detection_date = detection_date_raw.strftime('%Y-%m-%d')
                            detection_time = detection_date_raw.strftime('%H:%M:%S')
                        else:
                            detection_date = str(detection_date_raw)[:10]  # YYYY-MM-DD 형식
                    
                    if time_column and pd.notna(row[time_column]):
                        detection_time = str(row[time_column])
                    
                    # 국가 정보 추출
                    country = 'Unknown'
                    if country_column and pd.notna(row[country_column]):
                        country = str(row[country_column]).strip()
                    
                    # 공격유형 정보 추출
                    attack_type = 'SECUDIUM'
                    if attack_type_column and pd.notna(row[attack_type_column]):
                        attack_type = str(row[attack_type_column]).strip()
                    
                    # 설명 정보 추출
                    description = ''
                    if description_column and pd.notna(row[description_column]):
                        description = str(row[description_column]).strip()
                    
                    # 원본 출처 세부정보 구성
                    source_details = {
                        'type': 'SECUDIUM',
                        'attack_type': attack_type,
                        'country': country,
                        'detection_date': detection_date,
                        'detection_time': detection_time,
                        'description': description,
                        'row_index': idx + 1,
                        'excel_file': filepath.split('/')[-1]
                    }
                    
                    entry = BlacklistEntry(
                        ip_address=ip,
                        country=country,
                        reason=attack_type,  # 엑셀에서 추출한 공격유형 사용
                        source='SECUDIUM',
                        reg_date=detection_date,  # 엑셀에서 추출한 개별 날짜 사용
                        exp_date=None,
                        is_active=True,
                        threat_level='high',
                        source_details=source_details
                    )
                    entries.append(entry)
                    
                except Exception as e:
                    logger.warning(f"Excel 행 처리 스킵", 
                                 exception=e, row_index=idx, ip=ip if 'ip' in locals() else 'N/A')
                    continue
            
            logger.info(f"Excel에서 {len(entries)}개 IP 로드 (향상된 정보 포함)", 
                       file_path=filepath, count=len(entries), total_rows=len(df))
            return entries
            
        except FileNotFoundError as e:
            logger.error(f"Excel 파일을 찾을 수 없음", exception=e, file_path=filepath)
            raise CollectionError("SECUDIUM", f"파일 없음: {filepath}")
        except ValueError as e:
            logger.error(f"Excel 파일 형식 오류", exception=e, file_path=filepath)
            raise CollectionError("SECUDIUM", f"잘못된 Excel 형식: {str(e)}")
        except Exception as e:
            logger.error(f"Excel 파일 처리 중 예상치 못한 오류", 
                        exception=e, file_path=filepath)
            raise CollectionError("SECUDIUM", f"Excel 처리 실패: {str(e)}")
    
    @retry_on_error(max_attempts=3, delay=2.0, exceptions=(RequestException,))
    def login(self) -> bool:
        """SECUDIUM 웹사이트 로그인 - POST 방식"""
        try:
            logger.info("SECUDIUM 로그인 시도", base_url=self.base_url)
            
            # 세션 초기화
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest'
            })
            
            # 메인 페이지 접속하여 세션 초기화
            main_resp = self.session.get(self.base_url, verify=False, timeout=30)
            if main_resp.status_code != 200:
                logger.error(f"메인 페이지 접속 실패", 
                           status_code=main_resp.status_code, url=self.base_url)
                raise ExternalServiceError("SECUDIUM", 
                                         f"메인 페이지 접속 실패: HTTP {main_resp.status_code}")
            
            # 로그인 데이터 준비 (강제 로그인)
            login_data = {
                'lang': 'ko',
                'is_otp': 'N',
                'is_expire': 'Y',  # 기존 세션 종료
                'login_name': self.username,
                'password': self.password,
                'otp_value': ''
            }
            
            # POST 방식으로 로그인 (정확한 API 엔드포인트)
            login_resp = self.session.post(
                f"{self.base_url}/isap-api/loginProcess",
                data=login_data,
                verify=False,
                timeout=30
            )
            
            if login_resp.status_code == 200:
                try:
                    auth_data = login_resp.json()
                    if auth_data.get('response', {}).get('error') == False:
                        self.token = auth_data['response']['token']
                        
                        # 토큰을 헤더에 추가
                        self.session.headers.update({
                            'Authorization': f'Bearer {self.token}',
                            'X-AUTH-TOKEN': self.token
                        })
                        
                        logger.info("SECUDIUM 로그인 성공", 
                                  username=self.username, token_length=len(self.token))
                        self.authenticated = True
                        return True
                    else:
                        error_msg = auth_data.get('response', {}).get('message', 'Unknown error')
                        logger.error(f"SECUDIUM 로그인 인증 실패", 
                                   error_message=error_msg, username=self.username)
                        raise ExternalServiceError("SECUDIUM", f"로그인 실패: {error_msg}")
                except json.JSONDecodeError as e:
                    logger.error(f"로그인 응답 파싱 오류", 
                               exception=e, response_text=login_resp.text[:200])
                    raise ExternalServiceError("SECUDIUM", "로그인 응답 파싱 실패")
            else:
                logger.error(f"SECUDIUM 로그인 HTTP 오류", 
                           status_code=login_resp.status_code)
                raise ExternalServiceError("SECUDIUM", 
                                         f"로그인 실패: HTTP {login_resp.status_code}")
                
        except (Timeout, ConnectionError) as e:
            logger.error(f"SECUDIUM 연결 오류", exception=e)
            raise ExternalServiceError("SECUDIUM", f"서버 연결 실패: {str(e)}")
        except RequestException as e:
            logger.error(f"SECUDIUM 요청 오류", exception=e)
            raise ExternalServiceError("SECUDIUM", f"HTTP 요청 실패: {str(e)}")
        except Exception as e:
            logger.error(f"SECUDIUM 로그인 중 예상치 못한 오류", exception=e)
            raise
    
    def collect_from_web(self) -> List[BlacklistEntry]:
        """웹에서 SECUDIUM 데이터 수집 - 게시판의 엑셀 파일 다운로드"""
        try:
            if not self.authenticated and not self.login():
                logger.warning("로그인 실패로 파일 기반 수집 시도")
                return self.collect_from_file()
        except ExternalServiceError:
            logger.warning("웹 수집 실패, 파일 기반 수집으로 전환")
            return self.collect_from_file()
        
        logger.info("SECUDIUM 웹 데이터 수집 시작", 
                   timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        try:
            # 블랙리스트 게시판 조회
            list_resp = self.session.get(
                f"{self.base_url}/isap-api/secinfo/list/black_ip",
                verify=False,
                timeout=30
            )
            
            if list_resp.status_code != 200:
                logger.error(f"게시판 조회 실패: {list_resp.status_code}")
                return self.collect_from_file()
            
            data = list_resp.json()
            rows = data.get('rows', [])
            
            if not rows:
                logger.warning("게시글이 없음")
                return self.collect_from_file()
            
            logger.info(f"게시글 {len(rows)}개 발견")
            
            collected_ips = set()
            
            # 최신 3개 게시글에서 엑셀 다운로드
            for idx, row in enumerate(rows[:3]):
                try:
                    row_data = row.get('data', [])
                    if len(row_data) > 5:
                        title = row_data[2]
                        download_html = row_data[5]
                        
                        # 다운로드 정보 추출
                        match = re.search(r'download\s*\(\s*["\']([^"\']+)["\'],\s*["\']([^"\']+)["\']', download_html)
                        
                        if match:
                            server_file_name = match.group(1)  # UUID
                            file_name = match.group(2)         # 실제 파일명
                            
                            logger.info(f"[{idx+1}] {title} - {file_name} 다운로드 시도")
                            
                            # 정확한 다운로드 URL (HAR 분석 결과)
                            download_url = f"{self.base_url}/isap-api/file/SECINFO/download"
                            params = {
                                'X-Auth-Token': self.token,
                                'serverFileName': server_file_name,
                                'fileName': file_name
                            }
                            
                            dl_resp = self.session.get(download_url, params=params, verify=False, timeout=60)
                            
                            if dl_resp.status_code == 200 and len(dl_resp.content) > 1000:
                                # 임시 파일로 저장
                                temp_file = os.path.join(self.secudium_dir, f"temp_{idx}.xlsx")
                                with open(temp_file, 'wb') as f:
                                    f.write(dl_resp.content)
                                
                                # 엑셀에서 IP 추출
                                try:
                                    # 먼저 파일 내용을 확인
                                    with open(temp_file, 'rb') as f:
                                        content_sample = f.read(1000)
                                        if b'<html' in content_sample.lower() or b'<!doctype' in content_sample.lower():
                                            logger.error("다운로드된 파일이 HTML입니다. Excel 파일이 아닙니다.")
                                            continue
                                    
                                    df = pd.read_excel(temp_file, engine='openpyxl')
                                    logger.info(f"엑셀 로드 성공", 
                                              rows=df.shape[0], columns=df.shape[1], file=file_name)
                                    
                                    # 컬럼 매핑 정의
                                    ip_columns = []
                                    date_columns = []
                                    time_columns = []
                                    country_columns = []
                                    attack_type_columns = []
                                    description_columns = []
                                    
                                    # 컬럼 분석 및 매핑
                                    for col in df.columns:
                                        col_str = str(col).lower()
                                        
                                        # IP 컬럼 찾기
                                        if any(keyword in col_str for keyword in ['ip', 'address', '주소', 'addr']):
                                            ip_columns.append(col)
                                        
                                        # 날짜 컬럼 찾기
                                        elif any(keyword in col_str for keyword in ['date', '날짜', '등록', '탐지', 'reg', 'detect']):
                                            date_columns.append(col)
                                        
                                        # 시간 컬럼 찾기
                                        elif any(keyword in col_str for keyword in ['time', '시간', '시각']):
                                            time_columns.append(col)
                                        
                                        # 국가 컬럼 찾기
                                        elif any(keyword in col_str for keyword in ['country', '국가', 'nation', 'location']):
                                            country_columns.append(col)
                                        
                                        # 공격유형 컬럼 찾기
                                        elif any(keyword in col_str for keyword in ['type', '유형', '종류', 'attack', 'threat', 'category']):
                                            attack_type_columns.append(col)
                                        
                                        # 설명/상세정보 컬럼 찾기
                                        elif any(keyword in col_str for keyword in ['desc', '설명', '상세', 'detail', 'info', 'reason', '사유']):
                                            description_columns.append(col)
                                    
                                    logger.info(f"컬럼 매핑 완료: IP={len(ip_columns)}, 날짜={len(date_columns)}, 시간={len(time_columns)}, 국가={len(country_columns)}, 공격유형={len(attack_type_columns)}")
                                    
                                    # 행별로 모든 정보 추출
                                    for index, row in df.iterrows():
                                        # 기본값 설정
                                        ip_address = None
                                        detection_date = self._extract_date_from_filename(file_name)
                                        detection_time = None
                                        country = 'Unknown'
                                        attack_type = 'SECUDIUM'
                                        description = ''
                                        
                                        # IP 주소 찾기 (우선순위: 전용 컬럼 > 모든 컬럼 스캔)
                                        for col in ip_columns or df.columns:
                                            value = row.get(col)
                                            if pd.notna(value) and isinstance(value, str):
                                                str_value = value.strip()
                                                if re.match(r'^\d+\.\d+\.\d+\.\d+$', str_value):
                                                    if self._is_valid_ip(str_value):
                                                        ip_address = str_value
                                                        break
                                        
                                        if not ip_address:
                                            continue  # IP가 없으면 건너뛰기
                                        
                                        # 날짜 정보 추출
                                        for date_col in date_columns:
                                            date_value = row.get(date_col)
                                            if pd.notna(date_value):
                                                try:
                                                    if isinstance(date_value, pd.Timestamp):
                                                        detection_date = date_value.strftime('%Y-%m-%d')
                                                        if date_value.hour or date_value.minute:
                                                            detection_time = date_value.strftime('%H:%M:%S')
                                                    elif isinstance(date_value, str):
                                                        # 한국어 날짜 형식 처리: "2025. 0 6. 29. 오전 09:00"
                                                        if '오전' in date_value or '오후' in date_value:
                                                            try:
                                                                parts = date_value.split()
                                                                if len(parts) >= 5:  # 년. 월. 일. 오전/오후 시:분
                                                                    year = parts[0].replace('.', '')
                                                                    month = parts[1].replace('.', '').strip().zfill(2)
                                                                    day = parts[2].replace('.', '').strip().zfill(2)
                                                                    am_pm = parts[3]
                                                                    time_part = parts[4] if len(parts) > 4 else "00:00"
                                                                    
                                                                    if ':' in time_part:
                                                                        hour, minute = time_part.split(':')
                                                                        hour = int(hour)
                                                                        if am_pm == '오후' and hour != 12:
                                                                            hour += 12
                                                                        elif am_pm == '오전' and hour == 12:
                                                                            hour = 0
                                                                        
                                                                        detection_date = f"{year}-{month}-{day}"
                                                                        detection_time = f"{hour:02d}:{minute}:00"
                                                            except Exception as e:
                                                                logger.debug(f"한국어 날짜 파싱 실패: {e}")
                                                                # 실패시 pandas 파싱 시도
                                                                parsed = pd.to_datetime(date_value, errors='coerce')
                                                                if pd.notna(parsed):
                                                                    detection_date = parsed.strftime('%Y-%m-%d')
                                                                    if parsed.hour or parsed.minute:
                                                                        detection_time = parsed.strftime('%H:%M:%S')
                                                        else:
                                                            parsed = pd.to_datetime(date_value, errors='coerce')
                                                            if pd.notna(parsed):
                                                                detection_date = parsed.strftime('%Y-%m-%d')
                                                                if parsed.hour or parsed.minute:
                                                                    detection_time = parsed.strftime('%H:%M:%S')
                                                except:
                                                    pass
                                                break
                                        
                                        # 시간 정보 추출 (별도 시간 컬럼이 있는 경우)
                                        if not detection_time:
                                            for time_col in time_columns:
                                                time_value = row.get(time_col)
                                                if pd.notna(time_value):
                                                    try:
                                                        if isinstance(time_value, pd.Timestamp):
                                                            detection_time = time_value.strftime('%H:%M:%S')
                                                        elif isinstance(time_value, str):
                                                            # 시간 문자열 파싱
                                                            time_str = str(time_value).strip()
                                                            # 한국어 날짜 형식 처리: "2025. 0 6. 29. 오전 09:00"
                                                            if '오전' in time_str or '오후' in time_str:
                                                                try:
                                                                    # 날짜 부분과 시간 부분 분리
                                                                    parts = time_str.split()
                                                                    if len(parts) >= 6:  # 년. 월. 일. 오전/오후 시:분
                                                                        year = parts[0].replace('.', '')
                                                                        month = parts[1].replace('.', '').zfill(2)
                                                                        day = parts[2].replace('.', '').zfill(2)
                                                                        am_pm = parts[3]
                                                                        time_part = parts[4]
                                                                        
                                                                        if ':' in time_part:
                                                                            hour, minute = time_part.split(':')
                                                                            hour = int(hour)
                                                                            if am_pm == '오후' and hour != 12:
                                                                                hour += 12
                                                                            elif am_pm == '오전' and hour == 12:
                                                                                hour = 0
                                                                            
                                                                            detection_date = f"{year}-{month}-{day}"
                                                                            detection_time = f"{hour:02d}:{minute}:00"
                                                                except Exception as e:
                                                                    logger.debug(f"한국어 날짜 파싱 실패: {e}")
                                                            elif ':' in time_str:
                                                                detection_time = time_str
                                                    except:
                                                        pass
                                                    break
                                        
                                        # 국가 정보 추출
                                        for country_col in country_columns:
                                            country_value = row.get(country_col)
                                            if pd.notna(country_value) and str(country_value).strip():
                                                country = str(country_value).strip()
                                                break
                                        
                                        # 공격유형 추출
                                        for attack_col in attack_type_columns:
                                            attack_value = row.get(attack_col)
                                            if pd.notna(attack_value) and str(attack_value).strip():
                                                attack_type = str(attack_value).strip()
                                                break
                                        
                                        # 상세설명 추출
                                        desc_parts = []
                                        for desc_col in description_columns:
                                            desc_value = row.get(desc_col)
                                            if pd.notna(desc_value) and str(desc_value).strip():
                                                desc_parts.append(str(desc_value).strip())
                                        
                                        if desc_parts:
                                            description = ' | '.join(desc_parts)
                                        
                                        # 완전한 정보를 문자열로 저장 (hashable하게)
                                        full_info = f"{detection_date}|{detection_time or ''}|{country}|{attack_type}|{description}"
                                        collected_ips.add((ip_address, full_info))
                                    
                                    os.remove(temp_file)
                                    logger.info(f"IP 수집 완료", 
                                              file=file_name, ip_count=len(collected_ips))
                                    
                                except Exception as e:
                                    logger.warning(f"XLSX 파싱 실패, XLS 형식 시도: {e}")
                                    # XLS 형식으로 재시도
                                    try:
                                        df = pd.read_excel(temp_file, engine='xlrd')
                                        
                                        # 컬럼 매핑 정의 (XLS에서도 동일)
                                        ip_columns = []
                                        date_columns = []
                                        time_columns = []
                                        country_columns = []
                                        attack_type_columns = []
                                        description_columns = []
                                        
                                        # 컬럼 분석 및 매핑
                                        for col in df.columns:
                                            col_str = str(col).lower()
                                            
                                            if any(keyword in col_str for keyword in ['ip', 'address', '주소', 'addr']):
                                                ip_columns.append(col)
                                            elif any(keyword in col_str for keyword in ['date', '날짜', '등록', '탐지', 'reg', 'detect']):
                                                date_columns.append(col)
                                            elif any(keyword in col_str for keyword in ['time', '시간', '시각']):
                                                time_columns.append(col)
                                            elif any(keyword in col_str for keyword in ['country', '국가', 'nation', 'location']):
                                                country_columns.append(col)
                                            elif any(keyword in col_str for keyword in ['type', '유형', '종류', 'attack', 'threat', 'category']):
                                                attack_type_columns.append(col)
                                            elif any(keyword in col_str for keyword in ['desc', '설명', '상세', 'detail', 'info', 'reason', '사유']):
                                                description_columns.append(col)
                                        
                                        # 행별로 모든 정보 추출 (XLS)
                                        for index, row in df.iterrows():
                                            # 기본값 설정
                                            ip_address = None
                                            detection_date = self._extract_date_from_filename(file_name)
                                            detection_time = None
                                            country = 'Unknown'
                                            attack_type = 'SECUDIUM'
                                            description = ''
                                            
                                            # IP 주소 찾기
                                            for col in ip_columns or df.columns:
                                                if df[col].dtype == 'object':
                                                    value = row.get(col)
                                                    if pd.notna(value):
                                                        str_value = str(value).strip()
                                                        if re.match(r'^\d+\.\d+\.\d+\.\d+$', str_value):
                                                            if self._is_valid_ip(str_value):
                                                                ip_address = str_value
                                                                break
                                            
                                            if not ip_address:
                                                continue
                                            
                                            # 날짜/시간 정보 추출
                                            for date_col in date_columns:
                                                date_value = row.get(date_col)
                                                if pd.notna(date_value):
                                                    try:
                                                        if isinstance(date_value, pd.Timestamp):
                                                            detection_date = date_value.strftime('%Y-%m-%d')
                                                            if date_value.hour or date_value.minute:
                                                                detection_time = date_value.strftime('%H:%M:%S')
                                                        elif isinstance(date_value, str):
                                                            # 한국어 날짜 형식 처리: "2025. 0 6. 29. 오전 09:00"
                                                            if '오전' in date_value or '오후' in date_value:
                                                                try:
                                                                    parts = date_value.split()
                                                                    if len(parts) >= 5:  # 년. 월. 일. 오전/오후 시:분
                                                                        year = parts[0].replace('.', '')
                                                                        month = parts[1].replace('.', '').strip().zfill(2)
                                                                        day = parts[2].replace('.', '').strip().zfill(2)
                                                                        am_pm = parts[3]
                                                                        time_part = parts[4] if len(parts) > 4 else "00:00"
                                                                        
                                                                        if ':' in time_part:
                                                                            hour, minute = time_part.split(':')
                                                                            hour = int(hour)
                                                                            if am_pm == '오후' and hour != 12:
                                                                                hour += 12
                                                                            elif am_pm == '오전' and hour == 12:
                                                                                hour = 0
                                                                            
                                                                            detection_date = f"{year}-{month}-{day}"
                                                                            detection_time = f"{hour:02d}:{minute}:00"
                                                                except Exception as e:
                                                                    logger.debug(f"한국어 날짜 파싱 실패: {e}")
                                                                    # 실패시 pandas 파싱 시도
                                                                    parsed = pd.to_datetime(date_value, errors='coerce')
                                                                    if pd.notna(parsed):
                                                                        detection_date = parsed.strftime('%Y-%m-%d')
                                                                        if parsed.hour or parsed.minute:
                                                                            detection_time = parsed.strftime('%H:%M:%S')
                                                            else:
                                                                parsed = pd.to_datetime(date_value, errors='coerce')
                                                                if pd.notna(parsed):
                                                                    detection_date = parsed.strftime('%Y-%m-%d')
                                                                    if parsed.hour or parsed.minute:
                                                                        detection_time = parsed.strftime('%H:%M:%S')
                                                    except:
                                                        pass
                                                    break
                                            
                                            # 시간 정보 추출
                                            if not detection_time:
                                                for time_col in time_columns:
                                                    time_value = row.get(time_col)
                                                    if pd.notna(time_value):
                                                        try:
                                                            if isinstance(time_value, pd.Timestamp):
                                                                detection_time = time_value.strftime('%H:%M:%S')
                                                            elif isinstance(time_value, str):
                                                                time_str = str(time_value).strip()
                                                                if ':' in time_str:
                                                                    detection_time = time_str
                                                        except:
                                                            pass
                                                        break
                                            
                                            # 국가 정보 추출
                                            for country_col in country_columns:
                                                country_value = row.get(country_col)
                                                if pd.notna(country_value) and str(country_value).strip():
                                                    country = str(country_value).strip()
                                                    break
                                            
                                            # 공격유형 추출
                                            for attack_col in attack_type_columns:
                                                attack_value = row.get(attack_col)
                                                if pd.notna(attack_value) and str(attack_value).strip():
                                                    attack_type = str(attack_value).strip()
                                                    break
                                            
                                            # 상세설명 추출
                                            desc_parts = []
                                            for desc_col in description_columns:
                                                desc_value = row.get(desc_col)
                                                if pd.notna(desc_value) and str(desc_value).strip():
                                                    desc_parts.append(str(desc_value).strip())
                                            
                                            if desc_parts:
                                                description = ' | '.join(desc_parts)
                                            
                                            # 완전한 정보를 문자열로 저장 (hashable하게)
                                            full_info = f"{detection_date}|{detection_time or ''}|{country}|{attack_type}|{description}"
                                            collected_ips.add((ip_address, full_info))
                                        
                                        logger.info(f"XLS 형식으로 IP 수집 성공", 
                                                  file=file_name, ip_count=len(collected_ips))
                                    except Exception as xe:
                                        logger.error(f"Excel 파일 처리 실패: {xe}")
                                finally:
                                    if os.path.exists(temp_file):
                                        os.remove(temp_file)
                            else:
                                logger.warning(f"다운로드 실패: {dl_resp.status_code}")
                                
                except Exception as e:
                    logger.error(f"게시글 처리 오류: {e} (row {idx}, title: {title if 'title' in locals() else 'N/A'})")
                    continue
            
            if collected_ips:
                # BlacklistEntry 객체로 변환 - 모든 정보 포함
                entries = []
                for ip_tuple in collected_ips:
                    # collected_ips는 이제 (ip, full_info) 튜플의 집합
                    if isinstance(ip_tuple, tuple) and len(ip_tuple) == 2:
                        ip, info = ip_tuple
                        if isinstance(info, str) and '|' in info:
                            # 새로운 형식: 파이프로 구분된 정보
                            parts = info.split('|')
                            if len(parts) >= 5:
                                detection_date = parts[0]
                                detection_time = parts[1] or None
                                country = parts[2]
                                attack_type = parts[3]
                                description = '|'.join(parts[4:])  # 나머지는 description
                            else:
                                detection_date = str(info)
                                detection_time = None
                                country = 'Unknown'
                                attack_type = 'SECUDIUM'
                                description = ''
                        else:
                            # 이전 형식: 날짜만
                            detection_date = str(info)
                            detection_time = None
                            country = 'Unknown'
                            attack_type = 'SECUDIUM'
                            description = ''
                    else:
                        # 이전 형식 호환성 (단순 IP 문자열)
                        ip = ip_tuple
                        detection_date = self._extract_date_from_filename(file_name if 'file_name' in locals() else '')
                        detection_time = None
                        country = 'Unknown'
                        attack_type = 'SECUDIUM'
                        description = ''
                    
                    # 상세 정보 구성
                    source_details = {
                        'type': 'SECUDIUM_WEB',
                        'collection_method': 'excel_download',
                        'attack_type': attack_type
                    }
                    
                    if detection_time:
                        source_details['detection_time'] = detection_time
                    
                    if description:
                        source_details['description'] = description
                    
                    entry = BlacklistEntry(
                        ip_address=ip,
                        country=country,
                        reason=attack_type,  # 엑셀에서 추출한 공격유형 사용
                        source='SECUDIUM',
                        reg_date=detection_date,  # 엑셀에서 추출한 개별 날짜 사용
                        exp_date=None,
                        is_active=True,
                        threat_level='high',
                        source_details=source_details
                    )
                    entries.append(entry)
                
                # 수집 통계 로그
                logger.info(f"✅ SECUDIUM 웹 수집 완료")
                logger.info(f"📊 수집 통계:")
                logger.info(f"   - 총 수집 IP: {len(entries)}개")
                logger.info(f"   - 게시글 검색: {len(rows[:3])}개")
                logger.info(f"   - 수집 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 일일 수집인 경우 추가 통계
                today = datetime.now().strftime('%Y%m%d')
                if any(today in file_name for file_name in [row.get('data', [])[2] for row in rows[:3] if len(row.get('data', [])) > 2]):
                    logger.info(f"📅 금일({today}) 데이터 수집 포함")
                
                # 결과를 파일로도 저장
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                result_file = os.path.join(self.secudium_dir, f'collected_{timestamp}.json')
                
                with open(result_file, 'w', encoding='utf-8') as f:
                    # IP 리스트를 적절한 형식으로 변환
                    if collected_ips and isinstance(next(iter(collected_ips)), tuple):
                        # 튜플 형태인 경우: (ip, date)
                        ips_data = [{'ip': ip, 'detection_date': date} for ip, date in sorted(collected_ips)]
                        ips_list = [ip for ip, date in sorted(collected_ips)]
                    else:
                        # 이전 형식 호환성
                        ips_data = [{'ip': ip, 'detection_date': self._extract_date_from_filename(file_name if 'file_name' in locals() else '')} for ip in sorted(collected_ips)]
                        ips_list = sorted(collected_ips)
                    
                    json.dump({
                        'source': 'SECUDIUM',
                        'date': datetime.now().isoformat(),
                        'total_ips': len(collected_ips),
                        'ips': ips_list,  # 호환성을 위한 단순 IP 리스트
                        'ips_with_dates': ips_data  # 날짜가 포함된 상세 정보
                    }, f, indent=2, ensure_ascii=False)
                
                return entries
            else:
                logger.warning("SECUDIUM 웹에서 IP 데이터를 찾을 수 없음 - 파일 기반으로 폴백")
                return self.collect_from_file()  # 폴백: 파일 기반 수집
                
        except RequestException as e:
            logger.error(f"SECUDIUM 웹 수집 HTTP 오류", exception=e)
            raise ExternalServiceError("SECUDIUM", f"웹 수집 실패: {str(e)}")
        except Exception as e:
            logger.error(f"SECUDIUM 웹 수집 중 예상치 못한 오류", exception=e)
            raise CollectionError("SECUDIUM", f"웹 수집 실패: {str(e)}")
    
    def _extract_ips_from_json(self, data) -> List[str]:
        """JSON 데이터에서 IP 추출"""
        ips = []
        
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    # IP 필드 찾기
                    for key, value in item.items():
                        if 'ip' in key.lower() and isinstance(value, str):
                            if self._is_valid_ip(value):
                                ips.append(value)
        elif isinstance(data, dict):
            # 딕셔너리에서 IP 찾기
            if 'data' in data and isinstance(data['data'], list):
                ips.extend(self._extract_ips_from_json(data['data']))
            
            for key, value in data.items():
                if 'ip' in key.lower() and isinstance(value, str):
                    if self._is_valid_ip(value):
                        ips.append(value)
                elif isinstance(value, (list, dict)):
                    ips.extend(self._extract_ips_from_json(value))
        
        return ips
    
    def _extract_ips_from_html(self, html_text: str) -> List[str]:
        """HTML에서 IP 패턴 추출"""
        ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
        found_ips = ip_pattern.findall(html_text)
        
        # 유효한 IP만 필터링
        valid_ips = [ip for ip in found_ips if self._is_valid_ip(ip)]
        return valid_ips
    
    def _extract_ips_from_response(self, response) -> List[str]:
        """응답에서 IP 추출 (JSON 또는 HTML)"""
        try:
            data = response.json()
            return self._extract_ips_from_json(data)
        except ValueError:
            return self._extract_ips_from_html(response.text)
    
    def _parse_detection_date(self, date_value) -> str:
        """탐지일 파싱 - 원본 데이터 우선 사용"""
        if not date_value:
            return datetime.now().strftime('%Y-%m-%d')
        
        try:
            # pandas.Timestamp 객체인 경우
            if hasattr(date_value, 'strftime'):
                return date_value.strftime('%Y-%m-%d')
            
            # 문자열인 경우 파싱 시도
            if isinstance(date_value, str):
                # 다양한 날짜 형식 시도
                date_formats = ['%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d', '%m/%d/%Y', '%d/%m/%Y']
                for fmt in date_formats:
                    try:
                        parsed_date = datetime.strptime(date_value, fmt)
                        return parsed_date.strftime('%Y-%m-%d')
                    except ValueError:
                        continue
                
                # pandas로 파싱 시도
                try:
                    import pandas as pd
                    parsed_date = pd.to_datetime(date_value)
                    return parsed_date.strftime('%Y-%m-%d')
                except:
                    pass
            
            # 기타 타입인 경우 문자열로 변환 후 재시도
            return self._parse_detection_date(str(date_value))
            
        except Exception as e:
            logger.warning(f"날짜 파싱 실패 ({date_value}): {e}")
            return datetime.now().strftime('%Y-%m-%d')
    
    def _extract_date_from_filename(self, filename: str) -> str:
        """파일명에서 날짜 추출 시도"""
        if not filename:
            return datetime.now().strftime('%Y-%m-%d')
        
        try:
            # 파일명에서 날짜 패턴 찾기 (YYYYMMDD, YYYY-MM-DD, YYYY_MM_DD 등)
            import re
            date_patterns = [
                r'(\d{4})(\d{2})(\d{2})',  # YYYYMMDD
                r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
                r'(\d{4})_(\d{2})_(\d{2})',  # YYYY_MM_DD
                r'(\d{4})\.(\d{2})\.(\d{2})',  # YYYY.MM.DD
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, filename)
                if match:
                    year, month, day = match.groups()
                    try:
                        # 날짜 유효성 검증
                        date_obj = datetime(int(year), int(month), int(day))
                        return date_obj.strftime('%Y-%m-%d')
                    except ValueError:
                        continue
            
            # 파일명에서 날짜를 찾지 못한 경우 현재 날짜 사용
            logger.info(f"파일명 '{filename}'에서 날짜 패턴을 찾지 못함, 현재 날짜 사용")
            return datetime.now().strftime('%Y-%m-%d')
            
        except Exception as e:
            logger.warning(f"파일명 날짜 추출 실패 ({filename}): {e}")
            return datetime.now().strftime('%Y-%m-%d')

    def _is_valid_ip(self, ip: str) -> bool:
        """IP 주소 유효성 검사"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    return False
            
            # 로컬/사설 IP 제외
            if ip.startswith(('127.', '192.168.', '10.', '172.')):
                return False
            if ip == '0.0.0.0' or ip == '255.255.255.255':
                return False
                
            return True
        except (ValueError, AttributeError) as e:
            logger.debug(f"IP 유효성 검사 실패", ip=ip, exception=e)
            return False
    
    def auto_collect(self) -> Dict[str, Any]:
        """자동 수집 (웹 우선, 파일 폴백)"""
        try:
            logger.info("SECUDIUM 자동 수집 시작")
            
            # 웹에서 데이터 수집 시도
            try:
                collected_data = self.collect_from_web()
            except (CollectionError, ExternalServiceError) as e:
                logger.warning(f"웹 수집 실패, 파일 수집 시도", exception=e)
                collected_data = self.collect_from_file()
            
            if collected_data:
                # 결과 저장
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                result_file = os.path.join(self.secudium_dir, f'collected_{timestamp}.json')
                
                safe_execute(
                    lambda: self._save_collection_result(result_file, collected_data),
                    error_message="수집 결과 저장 실패"
                )
                
                return {
                    'success': True,
                    'message': f'SECUDIUM 수집 완료: {len(collected_data)}개 IP',
                    'total_collected': len(collected_data),
                    'ips': collected_data
                }
            else:
                return {
                    'success': False,
                    'message': 'SECUDIUM 데이터를 찾을 수 없습니다',
                    'total_collected': 0
                }
                
        except Exception as e:
            logger.error(f"SECUDIUM 자동 수집 중 예상치 못한 오류", exception=e)
            return {
                'success': False,
                'message': f'수집 오류: {str(e)}',
                'total_collected': 0
            }
    
    def _save_collection_result(self, filepath: str, data: List[BlacklistEntry]):
        """수집 결과 저장"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'source': 'SECUDIUM',
                'collected_at': datetime.now().isoformat(),
                'total_ips': len(data),
                'ips': [entry.ip_address for entry in data],
                'method': 'web_scraping'
            }, f, indent=2, ensure_ascii=False)
    
    def collect_blacklist_data(self, count: int = 100) -> List[Dict[str, Any]]:
        """블랙리스트 데이터 수집 (호환성 메서드)"""
        entries = self.collect_from_web()
        return [{
            'ip': entry.ip_address,
            'country': entry.country,
            'attack_type': entry.reason,
            'source': 'SECUDIUM'
        } for entry in entries[:count]]