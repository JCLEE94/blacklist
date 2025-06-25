#!/usr/bin/env python3
"""
Working SECUDIUM Collector
작동하는 SECUDIUM 수집기 - 토큰 기반 인증 사용
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import sqlite3

logger = logging.getLogger(__name__)

class WorkingSecudiumCollector:
    """토큰 기반 SECUDIUM 수집기"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.base_url = os.getenv('SECUDIUM_BASE_URL', 'https://secudium.skinfosec.co.kr')
        self.username = os.getenv('SECUDIUM_USERNAME', 'nextrade')
        self.password = os.getenv('SECUDIUM_PASSWORD', 'Sprtmxm1@3')
        
        self.session = requests.Session()
        self.token = None
        
    def authenticate(self) -> bool:
        """토큰 기반 인증"""
        try:
            logger.info("SECUDIUM 로그인 시작")
            
            # 로그인 데이터
            login_data = {
                'lang': 'ko',
                'is_otp': 'N',
                'is_expire': 'Y',
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
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'Referer': f'{self.base_url}/login'
                },
                timeout=30
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    resp_data = data.get('response', {})
                    
                    if not resp_data.get('error', True):
                        # 토큰 추출
                        self.token = resp_data.get('token')
                        if self.token:
                            logger.info(f"로그인 성공, 토큰 획득: {self.token[:20]}...")
                            
                            # 세션에 토큰 헤더 추가
                            self.session.headers.update({
                                'Authorization': f'Bearer {self.token}',
                                'X-Auth-Token': self.token
                            })
                            return True
                        else:
                            logger.error("토큰을 찾을 수 없습니다")
                            return False
                    else:
                        logger.error(f"로그인 실패: {resp_data.get('message', 'Unknown error')}")
                        return False
                        
                except json.JSONDecodeError as e:
                    logger.error(f"JSON 파싱 실패: {e}")
                    return False
            else:
                logger.error(f"로그인 요청 실패: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"인증 중 오류: {e}")
            return False
    
    def collect_blackip_data(self) -> List[Dict[str, Any]]:
        """블랙리스트 IP 데이터 수집"""
        if not self.token:
            logger.error("인증 토큰이 없습니다")
            return []
        
        try:
            logger.info("블랙리스트 데이터 수집 시작")
            
            # API 엔드포인트로 직접 요청
            api_url = f"{self.base_url}/isap-api/secinfo/blackIpList"
            
            # 날짜 범위 설정
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
            
            # API 파라미터
            params = {
                'page': 1,
                'size': 10000,  # 최대한 많이 가져오기
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'sortKey': 'REG_DT',
                'sortType': 'DESC'
            }
            
            # 헤더 설정
            headers = {
                'Authorization': f'Bearer {self.token}',
                'X-Auth-Token': self.token,
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Referer': f'{self.base_url}/secinfo/black_ip'
            }
            
            # API 호출
            response = self.session.get(
                api_url,
                params=params,
                headers=headers,
                timeout=30
            )
            
            logger.info(f"API 응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # 응답 구조 확인
                    if isinstance(data, dict):
                        # 'response' 키 확인
                        if 'response' in data:
                            response_data = data['response']
                            if 'list' in response_data:
                                items = response_data['list']
                            else:
                                items = response_data
                        # 'list' 키 직접 확인
                        elif 'list' in data:
                            items = data['list']
                        # 'content' 키 확인 (페이징 응답)
                        elif 'content' in data:
                            items = data['content']
                        else:
                            logger.warning(f"예상치 못한 응답 구조: {list(data.keys())}")
                            items = []
                    elif isinstance(data, list):
                        items = data
                    else:
                        logger.warning(f"예상치 못한 응답 타입: {type(data)}")
                        items = []
                    
                    logger.info(f"수집된 항목 수: {len(items)}")
                    
                    # IP 데이터 추출
                    results = []
                    for item in items:
                        if isinstance(item, dict):
                            ip = item.get('mal_ip') or item.get('ip') or item.get('malIp')
                            if ip:
                                results.append({
                                    'ip': ip,
                                    'source': 'SECUDIUM',
                                    'collected_at': datetime.now().isoformat(),
                                    'raw_data': item
                                })
                    
                    logger.info(f"추출된 IP 수: {len(results)}")
                    return results
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON 파싱 실패: {e}")
                    logger.debug(f"응답 내용: {response.text[:500]}")
                    return []
            else:
                logger.error(f"API 요청 실패: HTTP {response.status_code}")
                logger.debug(f"응답 내용: {response.text[:500]}")
                return []
                
        except Exception as e:
            logger.error(f"데이터 수집 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
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
            logger.info("SECUDIUM 자동 수집 시작")
            
            # 1. 인증
            if not self.authenticate():
                return {
                    'success': False,
                    'error': '로그인 실패',
                    'method': 'token-based'
                }
            
            # 2. 데이터 수집
            ip_data = self.collect_blackip_data()
            
            if not ip_data:
                return {
                    'success': False,
                    'error': 'IP 데이터 수집 실패',
                    'method': 'token-based'
                }
            
            # 3. 데이터 저장
            # JSON 파일 저장
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
            
            result = {
                'success': True,
                'method': 'token-based authentication',
                'total_ips': len(ip_data),
                'saved_to_db': db_saved,
                'json_file': str(json_file),
                'collected_at': datetime.now().isoformat()
            }
            
            logger.info(f"SECUDIUM 수집 완료: {len(ip_data)}개 IP")
            return result
            
        except Exception as e:
            logger.error(f"자동 수집 중 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'method': 'token-based'
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
    
    collector = WorkingSecudiumCollector()
    result = collector.auto_collect()
    
    print(json.dumps(result, indent=2, ensure_ascii=False))