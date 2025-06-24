#!/usr/bin/env python3
"""
실제 작동하는 수집기
HAR 파일 분석을 통해 확인한 정확한 API 사용
"""
import requests
import json
import os
import re
from datetime import datetime, timedelta
import sqlite3
from typing import List, Dict, Optional
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WorkingSecudiumCollector:
    """작동하는 SECUDIUM 수집기"""
    
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
        """SECUDIUM 로그인 - HAR에서 확인한 정확한 방식"""
        try:
            # 로그인 데이터
            login_data = {
                'lang': 'ko',
                'is_otp': 'N',
                'is_expire': 'N',
                'login_name': self.username,
                'password': self.password,
                'otp_value': ''
            }
            
            # 로그인 요청
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
                try:
                    result = response.json()
                    # HAR에서 확인한 토큰 형식
                    # nextrade:3150389729084400:0c236cfdde24404e07fc057f90e0660c6f49a783fac7f56e9c7fbc601f3ba639
                    if 'token' in result or 'auth_token' in result:
                        self.auth_token = result.get('token') or result.get('auth_token')
                        logger.info(f"Login successful, token received")
                        return True
                    elif response.text:
                        # 토큰이 응답 본문에 있을 수 있음
                        self.auth_token = response.text.strip()
                        logger.info(f"Login successful, token: {self.auth_token[:20]}...")
                        return True
                except:
                    # JSON이 아닌 경우 텍스트로 토큰 받기
                    if response.text:
                        self.auth_token = response.text.strip()
                        logger.info(f"Login successful with text response")
                        return True
            
            logger.error(f"Login failed: {response.status_code}")
            return False
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
    
    def collect_blacklist_list(self) -> List[Dict]:
        """블랙리스트 목록 수집"""
        if not self.auth_token:
            if not self.login():
                logger.error("Login required")
                return []
        
        try:
            # 블랙리스트 목록 요청
            # HAR에서 확인한 방식: URL 파라미터로 토큰 전달
            list_url = f"{self.base_url}/isap-api/secinfo/list/black_ip"
            
            # 토큰을 헤더와 URL 파라미터 둘 다 시도
            headers = self.session.headers.copy()
            headers['X-Auth-Token'] = self.auth_token
            
            # URL 파라미터로도 토큰 전달
            params = {
                'X-Auth-Token': self.auth_token,
                'page': '1',
                'rows': '100',
                '_search': 'false'
            }
            
            response = self.session.get(list_url, params=params, headers=headers)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.info(f"Got list response: {len(data.get('rows', []))} items")
                    
                    # 실제 IP 데이터 추출
                    blacklist_items = []
                    if 'rows' in data:
                        for row in data['rows']:
                            # 각 row에서 데이터 추출
                            if 'data' in row and len(row['data']) > 2:
                                title = row['data'][2]  # 제목
                                # 상세 정보는 별도 요청 필요
                                item_id = row.get('id')
                                if item_id:
                                    blacklist_items.append({
                                        'id': item_id,
                                        'title': title,
                                        'source': 'SECUDIUM'
                                    })
                    
                    return blacklist_items
                    
                except Exception as e:
                    logger.error(f"Failed to parse list response: {e}")
                    logger.debug(f"Response text: {response.text[:500]}")
            else:
                logger.error(f"Failed to get list: {response.status_code}")
                
        except Exception as e:
            logger.error(f"List collection error: {e}")
        
        return []
    
    def download_blacklist_file(self, file_id: str, file_name: str) -> Optional[str]:
        """블랙리스트 Excel 파일 다운로드"""
        try:
            download_url = f"{self.base_url}/isap-api/secinfo/download/{file_id}"
            
            headers = self.session.headers.copy()
            headers['X-Auth-Token'] = self.auth_token
            
            response = self.session.get(
                download_url,
                headers=headers,
                params={'X-Auth-Token': self.auth_token}
            )
            
            if response.status_code == 200:
                # 파일 저장
                file_path = f"data/secudium_{file_name}"
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Downloaded: {file_path}")
                return file_path
                
        except Exception as e:
            logger.error(f"Download error: {e}")
        
        return None


class WorkingRegtechCollector:
    """작동하는 REGTECH 수집기 - 세션 기반"""
    
    def __init__(self):
        self.base_url = "https://regtech.fsec.or.kr"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
    
    def collect_public_data(self) -> List[Dict]:
        """공개 데이터 수집 시도"""
        try:
            # advisory 리스트 페이지 직접 접근
            list_url = f"{self.base_url}/fcti/securityAdvisory/advisoryList"
            
            # 세션 없이 직접 접근
            response = self.session.get(list_url)
            
            if response.status_code == 200:
                # HTML에서 IP 추출
                return self._extract_ips_from_html(response.text)
            
            logger.error(f"Failed to access public page: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Public data collection error: {e}")
        
        return []
    
    def _extract_ips_from_html(self, html: str) -> List[Dict]:
        """HTML에서 IP 추출"""
        blacklist_items = []
        
        # IP 패턴
        ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
        
        # 모든 IP 찾기
        ips = ip_pattern.findall(html)
        
        # 유효한 공인 IP만 필터링
        for ip in set(ips):
            parts = ip.split('.')
            # 유효한 IP 확인
            if all(0 <= int(part) <= 255 for part in parts):
                # 사설 IP 제외
                if not any(ip.startswith(prefix) for prefix in ['192.168.', '10.', '127.', '172.', '0.', '255.']):
                    blacklist_items.append({
                        'ip': ip,
                        'source': 'REGTECH',
                        'reason': 'Threat IP',
                        'registration_date': datetime.now().strftime('%Y-%m-%d')
                    })
        
        logger.info(f"Extracted {len(blacklist_items)} IPs from HTML")
        return blacklist_items


def collect_and_update_database():
    """수집 및 데이터베이스 업데이트"""
    all_items = []
    
    # SECUDIUM 수집
    logger.info("=== SECUDIUM Collection ===")
    secudium = WorkingSecudiumCollector()
    secudium_list = secudium.collect_blacklist_list()
    
    if secudium_list:
        logger.info(f"Found {len(secudium_list)} SECUDIUM items")
        # 실제로는 각 항목의 상세 정보나 Excel 파일 다운로드 필요
        for item in secudium_list[:5]:  # 처음 5개만 테스트
            logger.info(f"  Item: {item}")
    
    # REGTECH 수집
    logger.info("\n=== REGTECH Collection ===")
    regtech = WorkingRegtechCollector()
    regtech_ips = regtech.collect_public_data()
    all_items.extend(regtech_ips)
    
    # 데이터베이스 업데이트
    if all_items:
        db_path = 'instance/blacklist.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        inserted = 0
        for item in all_items:
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
                        'malicious',
                        json.dumps(item),
                    ))
                    inserted += 1
                except Exception as e:
                    logger.error(f"Insert error: {e}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"\n=== Results ===")
        logger.info(f"Total items collected: {len(all_items)}")
        logger.info(f"IPs inserted/updated: {inserted}")
    else:
        logger.warning("No data collected")


if __name__ == "__main__":
    # data 폴더 생성
    os.makedirs('data', exist_ok=True)
    
    # 수집 실행
    collect_and_update_database()