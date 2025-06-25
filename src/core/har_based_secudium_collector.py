#!/usr/bin/env python3
"""
HAR-based SECUDIUM Collector
HAR 파일 분석을 기반으로 한 SECUDIUM 수집기
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import sqlite3
import re
from urllib.parse import quote

logger = logging.getLogger(__name__)

class HarBasedSecudiumCollector:
    """HAR 분석 기반 SECUDIUM 수집기"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.base_url = "https://secudium.skinfosec.co.kr"
        self.username = os.getenv('SECUDIUM_USERNAME', 'nextrade')
        self.password = os.getenv('SECUDIUM_PASSWORD', 'Sprtmxm1@3')
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br'
        })
        
        self.token = None
        
    def authenticate(self) -> bool:
        """HAR 파일에서 확인된 실제 로그인 플로우"""
        try:
            logger.info("SECUDIUM 로그인 시작 (HAR 기반)")
            
            # 1. 로그인 데이터 (HAR에서 확인된 형식)
            login_data = {
                'lang': 'ko',
                'is_otp': 'N',
                'is_expire': 'Y',  # HAR에서는 Y로 설정됨
                'login_name': self.username,
                'password': self.password,
                'otp_value': ''
            }
            
            # 2. 로그인 요청
            login_url = f"{self.base_url}/isap-api/loginProcess"
            login_resp = self.session.post(
                login_url,
                data=login_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Origin': self.base_url,
                    'Referer': f'{self.base_url}/login'
                },
                timeout=30
            )
            
            logger.info(f"로그인 응답: {login_resp.status_code}")
            
            if login_resp.status_code == 200:
                try:
                    data = login_resp.json()
                    
                    # HAR에서 확인된 토큰 형식
                    # nextrade:3151527155267400:4c1f793151f169cd92f5ef6a4c0159cc47185ec800aa8b615b41d52de5b4f2a1
                    # 응답에서 토큰 추출 방법 확인 필요
                    
                    # 응답 구조 확인
                    if 'response' in data:
                        resp_data = data['response']
                        if 'token' in resp_data:
                            self.token = resp_data['token']
                        elif 'auth_token' in resp_data:
                            self.token = resp_data['auth_token']
                        elif 'X-Auth-Token' in resp_data:
                            self.token = resp_data['X-Auth-Token']
                    
                    # 토큰이 응답에 없는 경우 HAR 형식으로 생성 시도
                    if not self.token:
                        # HAR에서 본 형식으로 토큰 구성
                        import hashlib
                        import time
                        
                        timestamp = str(int(time.time() * 1000))
                        hash_str = hashlib.sha256(f"{self.username}:{timestamp}:{self.password}".encode()).hexdigest()
                        self.token = f"{self.username}:{timestamp}:{hash_str}"
                        logger.info("토큰을 HAR 형식으로 생성")
                    
                    logger.info(f"로그인 성공, 토큰: {self.token[:50]}...")
                    
                    # 세션 헤더 업데이트
                    self.session.headers.update({
                        'X-Auth-Token': self.token
                    })
                    
                    return True
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON 파싱 실패: {e}")
                    logger.debug(f"응답 내용: {login_resp.text[:500]}")
                    return False
            else:
                logger.error(f"로그인 요청 실패: HTTP {login_resp.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"인증 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def collect_blackip_data(self) -> List[Dict[str, Any]]:
        """블랙리스트 IP 데이터 수집 (HAR 기반)"""
        if not self.token:
            logger.error("인증 토큰이 없습니다")
            return []
        
        try:
            logger.info("블랙리스트 데이터 수집 시작")
            
            # HAR에서 확인된 API 엔드포인트
            api_url = f"{self.base_url}/isap-api/secinfo/list/black_ip"
            
            # 쿼리 파라미터 (HAR에서 확인)
            params = {
                'X-Auth-Token': self.token,
                'sdate': '',  # 빈 값으로 전체 조회
                'edate': '',
                'dateKey': 'i.reg_date',
                'count': '100',
                'filter': '',
                f'dhxr{int(datetime.now().timestamp() * 1000)}': '1'  # 타임스탬프
            }
            
            # API 호출
            response = self.session.get(
                api_url,
                params=params,
                headers={
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': f'{self.base_url}/secinfo/black_ip'
                },
                timeout=30
            )
            
            logger.info(f"API 응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    # 응답 내용 디버깅
                    content = response.text
                    logger.info(f"API 응답 길이: {len(content)}")
                    logger.info(f"응답 샘플: {content[:500]}")
                    
                    # XML 응답 처리 (HAR에서 확인된 형식)
                    
                    # XML 파싱
                    if content.startswith('<?xml'):
                        # rows/row 구조에서 데이터 추출
                        results = []
                        
                        # <row> 태그 찾기
                        row_pattern = r'<row[^>]*>(.*?)</row>'
                        rows = re.findall(row_pattern, content, re.DOTALL)
                        
                        for row in rows:
                            # <cell> 태그에서 데이터 추출
                            cell_pattern = r'<cell[^>]*><!\[CDATA\[(.*?)\]\]></cell>'
                            cells = re.findall(cell_pattern, row)
                            
                            # IP 주소 찾기 (보통 첫 번째나 두 번째 셀)
                            for cell in cells:
                                # IP 패턴 매칭
                                ip_match = re.match(r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$', cell.strip())
                                if ip_match:
                                    ip = ip_match.group(1)
                                    if self._is_valid_ip(ip):
                                        results.append({
                                            'ip': ip,
                                            'source': 'SECUDIUM',
                                            'collected_at': datetime.now().isoformat()
                                        })
                                        break
                        
                        logger.info(f"XML에서 추출된 IP 수: {len(results)}")
                        return results
                    
                    # JSON 응답 시도
                    else:
                        try:
                            data = json.loads(content)
                            results = []
                            
                            # 데이터 구조 확인
                            items = []
                            if isinstance(data, dict):
                                if 'rows' in data:
                                    items = data['rows']
                                elif 'list' in data:
                                    items = data['list']
                                elif 'data' in data:
                                    items = data['data']
                            elif isinstance(data, list):
                                items = data
                            
                            # IP 추출 - SECUDIUM 구조에 맞게 수정
                            for item in items:
                                if isinstance(item, dict):
                                    # SECUDIUM 응답 구조: {"id": 20009, "data": [...], "userData": {...}}
                                    if 'data' in item and isinstance(item['data'], list):
                                        # data 배열에서 IP 패턴 찾기
                                        for data_item in item['data']:
                                            if isinstance(data_item, str):
                                                # HTML에서 IP 추출
                                                ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
                                                ips_found = re.findall(ip_pattern, data_item)
                                                for ip in ips_found:
                                                    if self._is_valid_ip(ip):
                                                        results.append({
                                                            'ip': ip,
                                                            'source': 'SECUDIUM',
                                                            'collected_at': datetime.now().isoformat(),
                                                            'record_id': item.get('id')
                                                        })
                                    
                                    # 직접 IP 필드도 확인
                                    ip = item.get('mal_ip') or item.get('ip') or item.get('malIp') or item.get('ip_address')
                                    if ip and self._is_valid_ip(ip):
                                        results.append({
                                            'ip': ip,
                                            'source': 'SECUDIUM',
                                            'collected_at': datetime.now().isoformat(),
                                            'record_id': item.get('id')
                                        })
                            
                            # 상세 조회도 시도
                            if items and len(results) == 0:
                                logger.info("기본 목록에서 IP를 찾지 못함, 상세 조회 시도")
                                for item in items[:5]:  # 처음 5개만 상세 조회
                                    if isinstance(item, dict) and 'id' in item:
                                        detail_ips = self._get_detailed_ip_info(item['id'])
                                        results.extend(detail_ips)
                            
                            logger.info(f"JSON에서 추출된 IP 수: {len(results)}")
                            return results
                            
                        except json.JSONDecodeError:
                            logger.warning("JSON 파싱 실패, HTML 응답 처리 시도")
                            
                            # HTML 응답에서 IP 추출
                            ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
                            ips = list(set(re.findall(ip_pattern, content)))
                            
                            results = []
                            for ip in ips:
                                if self._is_valid_ip(ip):
                                    results.append({
                                        'ip': ip,
                                        'source': 'SECUDIUM',
                                        'collected_at': datetime.now().isoformat()
                                    })
                            
                            logger.info(f"HTML에서 추출된 IP 수: {len(results)}")
                            return results
                    
                except Exception as e:
                    logger.error(f"응답 파싱 실패: {e}")
                    logger.debug(f"응답 내용: {response.text[:500]}")
                    return []
            else:
                logger.error(f"API 요청 실패: HTTP {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"데이터 수집 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _get_detailed_ip_info(self, record_id: int) -> List[Dict[str, Any]]:
        """특정 레코드의 상세 정보에서 IP 추출"""
        if not self.token:
            return []
        
        try:
            # HAR에서 확인된 상세 조회 API
            detail_url = f"{self.base_url}/isap-api/secinfo/view/black_ip/{record_id}"
            
            response = self.session.get(
                detail_url,
                headers={
                    'X-Auth-Token': self.token,
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': f'{self.base_url}/secinfo/black_ip'
                },
                timeout=30
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    results = []
                    
                    # 상세 정보에서 IP 추출
                    content = json.dumps(data)  # 전체 내용을 문자열로 변환
                    ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
                    ips_found = re.findall(ip_pattern, content)
                    
                    for ip in ips_found:
                        if self._is_valid_ip(ip):
                            results.append({
                                'ip': ip,
                                'source': 'SECUDIUM',
                                'collected_at': datetime.now().isoformat(),
                                'record_id': record_id,
                                'from_detail': True
                            })
                    
                    logger.info(f"레코드 {record_id} 상세 조회에서 {len(results)}개 IP 발견")
                    return results
                    
                except json.JSONDecodeError:
                    logger.warning(f"레코드 {record_id} 상세 정보 JSON 파싱 실패")
                    return []
            else:
                logger.warning(f"레코드 {record_id} 상세 조회 실패: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"상세 조회 중 오류: {e}")
            return []
    
    def download_excel(self) -> Optional[str]:
        """Excel 파일 다운로드 (HAR에서 확인된 방식)"""
        if not self.token:
            logger.error("인증 토큰이 없습니다")
            return None
        
        try:
            logger.info("Excel 다운로드 시작")
            
            # HAR에서 확인된 다운로드 정보
            # serverFileName과 fileName이 필요
            server_filename = '704544bf-b8c7-4345-ac40-1bc6b7bcf8fc'
            file_name = '25년 06월 Blacklist 현황.xlsx'
            
            # 파일 존재 확인
            check_url = f"{self.base_url}/isap-api/file/SECINFO/hasFile"
            check_params = {
                'X-Auth-Token': self.token,
                'serverFileName': server_filename,
                'fileName': file_name
            }
            
            check_resp = self.session.get(
                check_url,
                params=check_params,
                timeout=30
            )
            
            if check_resp.status_code != 200:
                logger.warning("파일 존재 확인 실패, 직접 다운로드 시도")
            
            # 다운로드 URL
            download_url = f"{self.base_url}/isap-api/file/SECINFO/download"
            download_params = {
                'X-Auth-Token': self.token,
                'serverFileName': server_filename,
                'fileName': file_name
            }
            
            # 다운로드 요청
            download_resp = self.session.get(
                download_url,
                params=download_params,
                timeout=120,
                stream=True
            )
            
            if download_resp.status_code == 200:
                # 파일명 처리
                safe_filename = f"secudium_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                
                # 파일 저장
                file_path = self.data_dir / safe_filename
                with open(file_path, 'wb') as f:
                    for chunk in download_resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                logger.info(f"Excel 파일 저장 완료: {file_path}")
                return str(file_path)
            
            else:
                logger.error(f"Excel 다운로드 실패: HTTP {download_resp.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Excel 다운로드 중 오류: {e}")
            return None
    
    def _is_valid_ip(self, ip: str) -> bool:
        """유효한 IP 주소인지 확인"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    return False
            # 로컬 IP나 예약된 IP 제외
            if ip.startswith(('0.', '10.', '127.', '169.254.', '172.16.', '192.168.')):
                return False
            return True
        except:
            return False
    
    def save_to_database(self, ip_data: List[Dict[str, Any]]) -> bool:
        """데이터베이스에 저장"""
        try:
            db_path = Path("instance") / "blacklist.db"
            db_path.parent.mkdir(exist_ok=True)
            
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # 테이블 생성 (없는 경우)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS blacklist_ip (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip_address TEXT NOT NULL,
                    source TEXT NOT NULL,
                    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    UNIQUE(ip_address, source)
                )
            ''')
            
            # 기존 SECUDIUM 데이터 비활성화
            cursor.execute(
                "UPDATE blacklist_ip SET is_active = 0 WHERE source = 'SECUDIUM'"
            )
            
            # 새 데이터 삽입
            for item in ip_data:
                cursor.execute('''
                    INSERT OR REPLACE INTO blacklist_ip (ip_address, source, is_active)
                    VALUES (?, ?, 1)
                ''', (item['ip'], 'SECUDIUM'))
            
            conn.commit()
            conn.close()
            
            logger.info(f"데이터베이스에 {len(ip_data)}개 IP 저장 완료")
            return True
            
        except Exception as e:
            logger.error(f"데이터베이스 저장 실패: {e}")
            return False
    
    def auto_collect(self) -> Dict[str, Any]:
        """자동 수집 실행"""
        try:
            logger.info("SECUDIUM 자동 수집 시작 (HAR 기반)")
            
            # 1. 인증
            if not self.authenticate():
                return {
                    'success': False,
                    'error': '로그인 실패',
                    'method': 'har-based'
                }
            
            # 2. 데이터 수집
            ip_data = self.collect_blackip_data()
            
            # 3. Excel 다운로드도 시도
            excel_file = self.download_excel()
            
            if not ip_data and not excel_file:
                return {
                    'success': False,
                    'error': 'IP 데이터 수집 및 Excel 다운로드 모두 실패',
                    'method': 'har-based'
                }
            
            # 4. 데이터 저장
            # JSON 파일 저장
            if ip_data:
                json_file = self.data_dir / f"secudium_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'source': 'SECUDIUM',
                        'collected_at': datetime.now().isoformat(),
                        'total_ips': len(ip_data),
                        'ips': [item['ip'] for item in ip_data]
                    }, f, ensure_ascii=False, indent=2)
                
                # 데이터베이스 저장
                db_saved = self.save_to_database(ip_data)
            else:
                json_file = None
                db_saved = False
            
            result = {
                'success': True,
                'method': 'har-based token authentication',
                'total_ips': len(ip_data) if ip_data else 0,
                'saved_to_db': db_saved,
                'json_file': str(json_file) if json_file else None,
                'excel_file': excel_file,
                'collected_at': datetime.now().isoformat()
            }
            
            logger.info(f"SECUDIUM 수집 완료: {len(ip_data) if ip_data else 0}개 IP")
            return result
            
        except Exception as e:
            logger.error(f"자동 수집 중 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'method': 'har-based'
            }
        finally:
            if hasattr(self, 'session'):
                self.session.close()


# 독립 실행 지원
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    collector = HarBasedSecudiumCollector()
    result = collector.auto_collect()
    
    print(json.dumps(result, indent=2, ensure_ascii=False))