#!/usr/bin/env python3
"""
HAR-based REGTECH Collector
HAR 파일 분석을 기반으로 한 REGTECH 수집기
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
import time
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class HarBasedRegtechCollector:
    """HAR 분석 기반 REGTECH 수집기"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.base_url = "https://regtech.fsec.or.kr"
        self.username = os.getenv('REGTECH_USERNAME', 'nextrade')
        self.password = os.getenv('REGTECH_PASSWORD', 'Sprtmxm1@3')
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'max-age=0',
            'Upgrade-Insecure-Requests': '1'
        })
        
    def authenticate(self) -> bool:
        """HAR 파일에서 확인된 실제 로그인 플로우"""
        try:
            logger.info("REGTECH 로그인 시작 (HAR 기반)")
            
            # 1. 로그인 폼 페이지 방문 (쿠키 획득)
            login_form_url = f"{self.base_url}/login/loginForm"
            resp = self.session.get(login_form_url, timeout=30)
            logger.info(f"로그인 폼 접근: {resp.status_code}")
            
            # 2. 로그인 데이터 준비 (HAR에서 확인된 형식)
            login_data = {
                'login_error': '',
                'txId': '',
                'token': '',
                'memberId': '',
                'smsTimeExcess': 'N',
                'username': self.username,
                'password': self.password
            }
            
            # 3. 로그인 요청
            login_url = f"{self.base_url}/login/addLogin"
            login_resp = self.session.post(
                login_url,
                data=login_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Origin': self.base_url,
                    'Referer': login_form_url
                },
                allow_redirects=False,
                timeout=30
            )
            
            logger.info(f"로그인 응답: {login_resp.status_code}")
            logger.info(f"응답 헤더: {dict(login_resp.headers)}")
            
            # 4. 리다이렉트 처리
            if login_resp.status_code == 302:
                redirect_url = login_resp.headers.get('Location', '')
                logger.info(f"리다이렉트 URL: {redirect_url}")
                
                # 에러 체크
                if 'error=true' in redirect_url:
                    logger.error("로그인 실패: error=true in redirect")
                    return False
                
                # 리다이렉트 따라가기
                if redirect_url:
                    full_url = redirect_url if redirect_url.startswith('http') else f"{self.base_url}{redirect_url}"
                    follow_resp = self.session.get(full_url, timeout=30)
                    logger.info(f"리다이렉트 페이지 접근: {follow_resp.status_code}")
                
                return True
            
            # 200 OK인 경우도 성공으로 간주
            elif login_resp.status_code == 200:
                # 응답 내용 확인
                if 'error' in login_resp.text.lower() or 'fail' in login_resp.text.lower():
                    logger.error("로그인 실패: 응답에 에러 메시지 포함")
                    return False
                logger.info("로그인 성공 (200 OK)")
                return True
            
            logger.error(f"예상치 못한 로그인 응답: {login_resp.status_code}")
            return False
            
        except Exception as e:
            logger.error(f"인증 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def collect_blacklist_data(self, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """블랙리스트 데이터 수집 (HAR 기반)"""
        try:
            logger.info("블랙리스트 데이터 수집 시작")
            
            # 날짜 설정
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
            
            # 1. advisoryList 페이지 접근 (필수)
            list_url = f"{self.base_url}/fcti/securityAdvisory/advisoryList"
            page_resp = self.session.get(list_url, timeout=30)
            logger.info(f"목록 페이지 접근: {page_resp.status_code}")
            
            # 2. POST 요청으로 데이터 가져오기 (HAR에서 확인된 형식)
            post_data = {
                'page': '0',
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
                'size': '1000'  # 더 많은 데이터 요청
            }
            
            # POST 요청
            data_resp = self.session.post(
                list_url,
                data=post_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': list_url
                },
                timeout=60
            )
            
            logger.info(f"데이터 요청 응답: {data_resp.status_code}")
            
            if data_resp.status_code == 200:
                # HTML 응답에서 데이터 추출
                content = data_resp.text
                
                # IP 패턴 찾기
                ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
                ips = list(set(re.findall(ip_pattern, content)))
                
                # JavaScript 변수에서 데이터 추출 시도
                results = []
                
                # 테이블 데이터 파싱
                if 'blackListView' in content:
                    # blackListView 링크에서 ipId 추출
                    view_pattern = r'blackListView\?[^"]*ipId=([a-f0-9\-]+)'
                    view_matches = re.findall(view_pattern, content)
                    
                    for ip_id in view_matches[:10]:  # 처음 10개만 상세 조회
                        time.sleep(0.5)  # 과도한 요청 방지
                        detail_url = f"{self.base_url}/fcti/securityAdvisory/blackListView"
                        detail_data = post_data.copy()
                        detail_data['ipId'] = ip_id
                        
                        detail_resp = self.session.post(
                            detail_url,
                            data=detail_data,
                            headers={
                                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                'X-Requested-With': 'XMLHttpRequest',
                                'Referer': list_url
                            },
                            timeout=30
                        )
                        
                        if detail_resp.status_code == 200:
                            # 상세 페이지에서 IP 추출
                            detail_ips = re.findall(ip_pattern, detail_resp.text)
                            for ip in detail_ips:
                                if self._is_valid_ip(ip):
                                    results.append({
                                        'ip': ip,
                                        'source': 'REGTECH',
                                        'collected_at': datetime.now().isoformat(),
                                        'ip_id': ip_id
                                    })
                
                # 목록에서 직접 찾은 IP들도 추가
                for ip in ips:
                    if self._is_valid_ip(ip) and not any(r['ip'] == ip for r in results):
                        results.append({
                            'ip': ip,
                            'source': 'REGTECH',
                            'collected_at': datetime.now().isoformat()
                        })
                
                logger.info(f"수집된 IP 수: {len(results)}")
                return results
            
            else:
                logger.error(f"데이터 요청 실패: HTTP {data_resp.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"데이터 수집 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def download_excel(self, start_date: str = None, end_date: str = None) -> Optional[str]:
        """Excel 파일 다운로드 (HAR에서 확인된 방식)"""
        try:
            logger.info("Excel 다운로드 시작")
            
            # 날짜 설정
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
            
            # 다운로드 URL (HAR에서 확인)
            download_url = f"{self.base_url}/fcti/securityAdvisory/advisoryListDownloadXlsx"
            
            # POST 데이터 (HAR에서 확인된 형식)
            download_data = {
                'page': '0',
                'tabSort': 'blacklist',
                'excelDownload': 'security,blacklist,weakpoint,',
                'cveId': '',
                'ipId': '',
                'estId': '',
                'startDate': start_date,
                'endDate': end_date,
                'findCondition': 'all',
                'findKeyword': '',
                'excelDown': ['security', 'blacklist', 'weakpoint'],
                'size': '10'
            }
            
            # 다운로드 요청
            download_resp = self.session.post(
                download_url,
                data=download_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': f"{self.base_url}/fcti/securityAdvisory/advisoryList"
                },
                timeout=120,
                stream=True
            )
            
            if download_resp.status_code == 200:
                # 파일명 추출
                content_disp = download_resp.headers.get('Content-Disposition', '')
                if 'filename=' in content_disp:
                    filename = content_disp.split('filename=')[-1].strip('"')
                else:
                    filename = f"regtech_blacklist_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                
                # 파일 저장
                file_path = self.data_dir / filename
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
            
            # 기존 REGTECH 데이터 비활성화
            cursor.execute(
                "UPDATE blacklist_ip SET is_active = 0 WHERE source = 'REGTECH'"
            )
            
            # 새 데이터 삽입
            for item in ip_data:
                cursor.execute('''
                    INSERT OR REPLACE INTO blacklist_ip (ip_address, source, is_active)
                    VALUES (?, ?, 1)
                ''', (item['ip'], 'REGTECH'))
            
            conn.commit()
            conn.close()
            
            logger.info(f"데이터베이스에 {len(ip_data)}개 IP 저장 완료")
            return True
            
        except Exception as e:
            logger.error(f"데이터베이스 저장 실패: {e}")
            return False
    
    def auto_collect(self, prefer_web: bool = True) -> Dict[str, Any]:
        """자동 수집 실행"""
        try:
            logger.info("REGTECH 자동 수집 시작 (HAR 기반)")
            
            # 1. 인증
            if not self.authenticate():
                return {
                    'success': False,
                    'error': '로그인 실패',
                    'method': 'har-based'
                }
            
            # 2. 데이터 수집
            ip_data = self.collect_blacklist_data()
            
            # 3. Excel 다운로드도 시도
            excel_file = None
            if prefer_web:
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
                json_file = self.data_dir / f"regtech_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'source': 'REGTECH',
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
                'method': 'har-based web collection',
                'total_ips': len(ip_data) if ip_data else 0,
                'saved_to_db': db_saved,
                'json_file': str(json_file) if json_file else None,
                'excel_file': excel_file,
                'collected_at': datetime.now().isoformat()
            }
            
            logger.info(f"REGTECH 수집 완료: {len(ip_data) if ip_data else 0}개 IP")
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
    
    collector = HarBasedRegtechCollector()
    result = collector.auto_collect()
    
    print(json.dumps(result, indent=2, ensure_ascii=False))