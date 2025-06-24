#!/usr/bin/env python3
"""
실제 API 분석 기반 수집기
HAR 파일 분석을 통해 파악한 실제 API 엔드포인트 사용
"""
import requests
import json
import os
from datetime import datetime, timedelta
import sqlite3
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImprovedRegtechCollector:
    """개선된 REGTECH 수집기 - 실제 API 사용"""
    
    def __init__(self):
        self.base_url = "https://regtech.fsec.or.kr"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        })
        self.username = os.getenv('REGTECH_USERNAME', 'nextrade')
        self.password = os.getenv('REGTECH_PASSWORD', 'Sprtmxm1@3')
    
    def login(self) -> bool:
        """REGTECH 로그인"""
        try:
            # 1. 로그인 페이지 접속
            login_page = self.session.get(f"{self.base_url}/login/loginForm")
            logger.info(f"Login page status: {login_page.status_code}")
            
            # 2. 로그인 요청
            login_data = {
                'memberId': self.username,
                'password': self.password
            }
            
            login_resp = self.session.post(
                f"{self.base_url}/login/addLogin",
                data=login_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': f"{self.base_url}/login/loginForm"
                }
            )
            
            # 로그인 성공 여부 확인
            if login_resp.status_code == 200:
                # 메인 페이지로 이동해서 확인
                main_page = self.session.get(f"{self.base_url}/main/main")
                if '로그아웃' in main_page.text:
                    logger.info("REGTECH login successful")
                    return True
            
            logger.error(f"REGTECH login failed: {login_resp.status_code}")
            return False
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
    
    def collect_blacklist_data(self, start_date: str = None, end_date: str = None) -> List[Dict]:
        """블랙리스트 데이터 수집"""
        if not self.login():
            logger.error("Login required for data collection")
            return []
        
        # 날짜 설정
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")
        
        try:
            # HAR 파일에서 확인한 실제 엔드포인트
            # 1. 리스트 페이지 접속
            list_url = f"{self.base_url}/fcti/securityAdvisory/advisoryList"
            list_page = self.session.get(list_url)
            logger.info(f"Advisory list page status: {list_page.status_code}")
            
            # 2. 블랙리스트 탭 데이터 요청
            blacklist_data = {
                'page': '0',
                'tabSort': 'blacklist',
                'startDate': start_date,
                'endDate': end_date,
                'findCondition': 'all',
                'findKeyword': '',
                'size': '1000'  # 더 많은 데이터 요청
            }
            
            # AJAX 요청으로 데이터 가져오기
            ajax_headers = self.session.headers.copy()
            ajax_headers.update({
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': list_url
            })
            
            # 블랙리스트 데이터 요청
            response = self.session.post(
                f"{self.base_url}/fcti/securityAdvisory/blacklistListJson",
                data=blacklist_data,
                headers=ajax_headers
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    blacklist_items = []
                    
                    # JSON 응답에서 IP 추출
                    if 'list' in data:
                        for item in data['list']:
                            ip_info = {
                                'ip': item.get('ip', ''),
                                'country': item.get('country', ''),
                                'reason': item.get('reason', ''),
                                'registration_date': item.get('regDate', ''),
                                'source': 'REGTECH'
                            }
                            if ip_info['ip']:
                                blacklist_items.append(ip_info)
                                logger.info(f"Found IP: {ip_info['ip']}")
                    
                    logger.info(f"Collected {len(blacklist_items)} IPs from REGTECH")
                    return blacklist_items
                    
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON response")
                    # HTML 응답인 경우 파싱 시도
                    return self._parse_html_response(response.text)
            
            logger.error(f"Failed to get blacklist data: {response.status_code}")
            return []
            
        except Exception as e:
            logger.error(f"Collection error: {e}")
            return []
    
    def _parse_html_response(self, html: str) -> List[Dict]:
        """HTML 응답에서 IP 추출"""
        blacklist_items = []
        try:
            import re
            # IP 패턴 찾기
            ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
            ips = re.findall(ip_pattern, html)
            
            for ip in set(ips):
                # 유효한 공인 IP만
                if not any(ip.startswith(p) for p in ['192.168.', '10.', '127.', '172.']):
                    blacklist_items.append({
                        'ip': ip,
                        'country': 'Unknown',
                        'reason': 'REGTECH Blacklist',
                        'registration_date': datetime.now().strftime('%Y-%m-%d'),
                        'source': 'REGTECH'
                    })
            
            logger.info(f"Extracted {len(blacklist_items)} IPs from HTML")
        except Exception as e:
            logger.error(f"HTML parsing error: {e}")
        
        return blacklist_items


class ImprovedSecudiumCollector:
    """개선된 SECUDIUM 수집기 - 실제 API 사용"""
    
    def __init__(self):
        self.base_url = "https://secudium.skinfosec.co.kr"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        })
        self.username = os.getenv('SECUDIUM_USERNAME', 'nextrade')
        self.password = os.getenv('SECUDIUM_PASSWORD', 'Sprtmxm1@3')
        self.auth_token = None
    
    def login(self) -> bool:
        """SECUDIUM 로그인"""
        try:
            # HAR 파일에서 확인한 로그인 API
            login_data = {
                'lang': 'ko',
                'is_otp': 'N',
                'is_expire': 'N',
                'login_name': self.username,
                'password': self.password,
                'otp_value': ''
            }
            
            response = self.session.post(
                f"{self.base_url}/isap-api/loginProcess",
                data=login_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': f"{self.base_url}/login"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    # 토큰 저장
                    self.auth_token = result.get('token', '')
                    if 'X-Auth-Token' in response.headers:
                        self.session.headers['X-Auth-Token'] = response.headers['X-Auth-Token']
                    logger.info("SECUDIUM login successful")
                    return True
                else:
                    logger.error(f"Login failed: {result.get('message', 'Unknown error')}")
            
            return False
            
        except Exception as e:
            logger.error(f"SECUDIUM login error: {e}")
            return False
    
    def collect_blacklist_data(self) -> List[Dict]:
        """블랙리스트 데이터 수집"""
        if not self.login():
            logger.error("Login required for data collection")
            return []
        
        try:
            # 블랙리스트 페이지 접속
            list_url = f"{self.base_url}/secinfo/black_ip"
            
            # 리스트 데이터 요청
            list_params = {
                'page': '1',
                'rows': '100',
                '_search': 'false'
            }
            
            response = self.session.get(
                f"{self.base_url}/isap-api/secinfo/list/black_ip",
                params=list_params,
                headers={
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': list_url
                }
            )
            
            blacklist_items = []
            
            if response.status_code == 200:
                data = response.json()
                
                # 각 항목의 상세 정보 가져오기
                if 'rows' in data:
                    for row in data['rows']:
                        item_id = row.get('id')
                        if item_id:
                            # 상세 정보 요청
                            detail = self._get_blacklist_detail(item_id)
                            if detail:
                                blacklist_items.append(detail)
                
                logger.info(f"Collected {len(blacklist_items)} items from SECUDIUM")
            
            return blacklist_items
            
        except Exception as e:
            logger.error(f"SECUDIUM collection error: {e}")
            return []
    
    def _get_blacklist_detail(self, item_id: int) -> Optional[Dict]:
        """블랙리스트 상세 정보 가져오기"""
        try:
            response = self.session.get(
                f"{self.base_url}/isap-api/secinfo/view/black_ip/{item_id}",
                headers={
                    'X-Requested-With': 'XMLHttpRequest'
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # 실제 블랙리스트 IP는 첨부 파일에 있을 수 있음
                # 일단 메타데이터 수집
                return {
                    'title': data.get('title', ''),
                    'content': data.get('content', ''),
                    'file_name': data.get('fileString255', ''),
                    'file_id': data.get('sefileString255', ''),
                    'registration_date': datetime.fromtimestamp(
                        data.get('regDate', 0) / 1000
                    ).strftime('%Y-%m-%d') if data.get('regDate') else '',
                    'source': 'SECUDIUM'
                }
                
        except Exception as e:
            logger.error(f"Failed to get detail for item {item_id}: {e}")
        
        return None


def update_database_with_collected_data(blacklist_items: List[Dict]):
    """수집한 데이터로 데이터베이스 업데이트"""
    db_path = 'instance/blacklist.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    inserted = 0
    for item in blacklist_items:
        if 'ip' in item and item['ip']:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO blacklist_ip 
                    (ip, source, detection_date, threat_type, metadata, is_active)
                    VALUES (?, ?, ?, ?, ?, 1)
                ''', (
                    item['ip'],
                    item.get('source', 'Unknown'),
                    item.get('registration_date', datetime.now().strftime('%Y-%m-%d')),
                    item.get('reason', 'malicious'),
                    json.dumps({
                        'country': item.get('country', 'Unknown'),
                        'reason': item.get('reason', ''),
                        'original_data': item
                    }),
                ))
                inserted += 1
            except Exception as e:
                logger.error(f"Failed to insert IP {item['ip']}: {e}")
    
    conn.commit()
    conn.close()
    
    logger.info(f"Inserted/Updated {inserted} IPs in database")
    return inserted


def main():
    """메인 실행 함수"""
    logger.info("=== Starting Improved Collectors ===")
    
    all_items = []
    
    # REGTECH 수집
    logger.info("\n--- REGTECH Collection ---")
    regtech_collector = ImprovedRegtechCollector()
    regtech_items = regtech_collector.collect_blacklist_data()
    all_items.extend(regtech_items)
    
    # SECUDIUM 수집
    logger.info("\n--- SECUDIUM Collection ---")
    secudium_collector = ImprovedSecudiumCollector()
    secudium_items = secudium_collector.collect_blacklist_data()
    all_items.extend(secudium_items)
    
    # 데이터베이스 업데이트
    if all_items:
        logger.info(f"\n--- Updating Database ---")
        count = update_database_with_collected_data(all_items)
        logger.info(f"Collection complete. Total items processed: {count}")
    else:
        logger.warning("No data collected")
    
    return len(all_items)


if __name__ == "__main__":
    main()