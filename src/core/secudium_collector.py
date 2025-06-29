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
        
        # SECUDIUM 웹사이트 설정
        self.base_url = settings.secudium_base_url
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
        """Excel 파일 처리"""
        try:
            df = pd.read_excel(filepath)
            entries = []
            
            # IP 컬럼 찾기
            ip_columns = [col for col in df.columns if 'ip' in str(col).lower()]
            if not ip_columns:
                logger.error("IP 컬럼을 찾을 수 없음", 
                           file_path=filepath, columns=list(df.columns))
                raise CollectionError("SECUDIUM", "Excel 파일에 IP 컬럼이 없습니다")
            
            ip_column = ip_columns[0]
            
            for idx, row in df.iterrows():
                try:
                    ip = str(row[ip_column]).strip()
                    if not ip or ip == 'nan':
                        continue
                    
                    entry = BlacklistEntry(
                        ip_address=ip,
                        country=row.get('country', 'Unknown'),
                        reason=row.get('attack_type', 'SECUDIUM'),
                        source='SECUDIUM',
                        reg_date=self._parse_detection_date(row.get('detection_date')),
                        exp_date=None,
                        is_active=True,
                        threat_level=row.get('threat_level', 'high'),
                        source_details={
                            'type': 'SECUDIUM',
                            'attack': row.get('attack_type', 'Unknown')
                        }
                    )
                    entries.append(entry)
                except Exception as e:
                    logger.warning(f"Excel 행 처리 스킵", 
                                 exception=e, row_index=idx, ip=ip if 'ip' in locals() else 'N/A')
                    continue
            
            logger.info(f"Excel에서 {len(entries)}개 IP 로드", 
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
                                    df = pd.read_excel(temp_file, engine='openpyxl')
                                    logger.info(f"엑셀 로드 성공", 
                                              rows=df.shape[0], columns=df.shape[1], file=file_name)
                                    
                                    # 모든 컬럼에서 IP 찾기
                                    for col in df.columns:
                                        if df[col].dtype == 'object':
                                            for value in df[col].dropna():
                                                str_value = str(value).strip()
                                                # IP 패턴 확인
                                                if re.match(r'^\d+\.\d+\.\d+\.\d+$', str_value):
                                                    if self._is_valid_ip(str_value):
                                                        collected_ips.add(str_value)
                                    
                                    os.remove(temp_file)
                                    logger.info(f"IP 수집 완료", 
                                              file=file_name, ip_count=len(collected_ips))
                                    
                                except Exception as e:
                                    logger.warning(f"XLSX 파싱 실패, XLS 형식 시도", 
                                                 exception=e, file=file_name)
                                    # XLS 형식으로 재시도
                                    try:
                                        df = pd.read_excel(temp_file, engine='xlrd')
                                        for col in df.columns:
                                            if df[col].dtype == 'object':
                                                for value in df[col].dropna():
                                                    str_value = str(value).strip()
                                                    if re.match(r'^\d+\.\d+\.\d+\.\d+$', str_value):
                                                        if self._is_valid_ip(str_value):
                                                            collected_ips.add(str_value)
                                        logger.info(f"XLS 형식으로 IP 수집 성공", 
                                                  file=file_name, ip_count=len(collected_ips))
                                    except Exception as xe:
                                        logger.error(f"Excel 파일 처리 실패", 
                                                   exception=xe, file=file_name)
                                finally:
                                    if os.path.exists(temp_file):
                                        os.remove(temp_file)
                            else:
                                logger.warning(f"다운로드 실패: {dl_resp.status_code}")
                                
                except Exception as e:
                    logger.error(f"게시글 처리 오류", 
                              exception=e, row_index=idx, title=title if 'title' in locals() else 'N/A')
                    continue
            
            if collected_ips:
                # BlacklistEntry 객체로 변환
                entries = []
                for ip in collected_ips:
                    entry = BlacklistEntry(
                        ip_address=ip,
                        country='Unknown',
                        reason='SECUDIUM',
                        source='SECUDIUM',
                        reg_date=self._extract_date_from_filename(file_name),
                        exp_date=None,
                        is_active=True,
                        threat_level='high',
                        source_details={
                            'type': 'SECUDIUM_WEB',
                            'collection_method': 'excel_download'
                        }
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
                    json.dump({
                        'source': 'SECUDIUM',
                        'date': datetime.now().isoformat(),
                        'total_ips': len(collected_ips),
                        'ips': sorted(collected_ips)
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