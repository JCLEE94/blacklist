#!/usr/bin/env python3
"""
REGTECH 개선된 수집기 - PowerShell 스크립트 로직 기반
쿠키 기반 인증으로 안정적인 데이터 수집
"""

import os
import json
import logging
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import re
from bs4 import BeautifulSoup

from src.core.models import BlacklistEntry

logger = logging.getLogger(__name__)

@dataclass
class RegtechCollectionStats:
    """REGTECH 수집 통계"""
    start_time: datetime
    end_time: Optional[datetime] = None
    total_collected: int = 0
    pages_processed: int = 0
    error_count: int = 0
    duplicate_count: int = 0

class RegtechEnhancedCollector:
    """
    REGTECH 개선된 수집기
    - 쿠키 기반 인증
    - 페이지 자동 순회
    - 환경변수 기반 설정
    """
    
    def __init__(self):
        self.base_url = "https://regtech.fsec.or.kr"
        self.api_url = f"{self.base_url}/fcti/securityAdvisory/advisoryList"
        
        # 환경변수에서 쿠키 설정 로드
        self.cookies = self._load_cookies_from_env()
        
        # 요청 헤더 설정
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Referer': f'{self.base_url}/fcti/securityAdvisory/advisoryList',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
        }
        
        # 세션 생성
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.cookies.update(self.cookies)
        
        logger.info("✅ REGTECH 개선된 수집기 초기화 완료")
    
    def _load_cookies_from_env(self) -> Dict[str, str]:
        """데이터베이스 우선, 환경변수 대체로 쿠키 설정 로드"""
        cookies = {}
        
        # 데이터베이스에서 쿠키 설정 로드 시도
        try:
            from src.models.settings import get_settings_manager
            settings_manager = get_settings_manager()
            
            # DB에서 REGTECH 쿠키 설정들 조회
            db_cookie_mapping = {
                'regtech_cookie_ga': '_ga',
                'regtech_cookie_front': 'regtech-front',
                'regtech_cookie_va': 'regtech-va', 
                'regtech_cookie_ga_analytics': '_ga_7WRDYHF66J'
            }
            
            db_cookies_found = 0
            for db_key, cookie_name in db_cookie_mapping.items():
                cookie_value = settings_manager.get_setting(db_key)
                if cookie_value and cookie_value.strip():
                    cookies[cookie_name] = cookie_value.strip()
                    logger.info(f"✅ DB에서 쿠키 로드됨: {cookie_name}")
                    db_cookies_found += 1
            
            if db_cookies_found > 0:
                logger.info(f"✅ 데이터베이스에서 {db_cookies_found}개 쿠키 설정 로드 완료")
                return cookies
            else:
                logger.info("ℹ️ 데이터베이스에 저장된 쿠키 설정이 없음, 환경변수 확인")
                
        except Exception as e:
            logger.warning(f"⚠️ 데이터베이스 쿠키 로드 실패: {e}, 환경변수 사용")
        
        # 환경변수에서 쿠키 설정 로드 (DB 대체)
        env_cookie_mapping = {
            'REGTECH_COOKIE_GA': '_ga',
            'REGTECH_COOKIE_FRONT': 'regtech-front', 
            'REGTECH_COOKIE_VA': 'regtech-va',
            'REGTECH_COOKIE_GA_ANALYTICS': '_ga_7WRDYHF66J'
        }
        
        env_cookies_found = 0
        for env_key, cookie_name in env_cookie_mapping.items():
            cookie_value = os.getenv(env_key)
            if cookie_value and cookie_value.strip():
                cookies[cookie_name] = cookie_value.strip()
                logger.info(f"✅ 환경변수에서 쿠키 로드됨: {cookie_name}")
                env_cookies_found += 1
        
        # 쿠키가 하나도 없으면 기본값 사용 (테스트용)
        if not cookies:
            logger.warning("⚠️ DB와 환경변수에서 쿠키를 찾을 수 없습니다. 기본값을 사용합니다.")
            cookies = {
                '_ga': 'GA1.1.1689204774.1752555033',
                'regtech-front': '2F3B7CE1B26084FCD546BDB56CE9ABAC',
                'regtech-va': 'Bearer...',  # 실제 토큰으로 교체 필요
                '_ga_7WRDYHF66J': 'GS2.1.s1752743223$o3$g1$t1752746099$j38$l0$h0'
            }
        else:
            if env_cookies_found > 0:
                logger.info(f"✅ 환경변수에서 {env_cookies_found}개 쿠키 설정 로드 완료")
        
        return cookies
    
    def collect_from_web(self, start_date: str = None, end_date: str = None) -> List[BlacklistEntry]:
        """
        웹에서 데이터 수집 - 모든 페이지 자동 순회
        
        Args:
            start_date: 시작일 (YYYYMMDD) - 기본값: 3개월 전
            end_date: 종료일 (YYYYMMDD) - 기본값: 오늘
            
        Returns:
            수집된 BlacklistEntry 리스트
        """
        stats = RegtechCollectionStats(start_time=datetime.now())
        
        try:
            # 날짜 설정
            if not start_date:
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            
            logger.info(f"🚀 REGTECH 수집 시작 - 기간: {start_date} ~ {end_date}")
            
            all_entries = []
            page = 0
            
            while True:
                logger.info(f"📄 페이지 {page} 요청 중...")
                
                # POST 요청 데이터
                post_data = {
                    'page': str(page),
                    'tabSort': 'blacklist',
                    'startDate': start_date,
                    'endDate': end_date,
                    'findCondition': 'all',
                    'findKeyword': '',
                    'size': '50'
                }
                
                try:
                    # 요청 실행
                    response = self.session.post(
                        self.api_url,
                        data=post_data,
                        timeout=30,
                        verify=False  # SSL 검증 비활성화 (필요시)
                    )
                    
                    response.raise_for_status()
                    stats.pages_processed += 1
                    
                    # HTML 파싱
                    page_entries = self._parse_html_response(response.text)
                    
                    if not page_entries:
                        logger.info(f"✅ 페이지 {page}에서 더 이상 데이터가 없어 수집 종료")
                        break
                    
                    all_entries.extend(page_entries)
                    logger.info(f"   -> {len(page_entries)}개 항목 발견 (누적: {len(all_entries)}개)")
                    
                    page += 1
                    
                    # 요청 간격 (서버 부하 방지)
                    time.sleep(1)
                    
                except requests.exceptions.RequestException as e:
                    logger.error(f"❌ 페이지 {page} 요청 실패: {e}")
                    stats.error_count += 1
                    break
                except Exception as e:
                    logger.error(f"❌ 페이지 {page} 처리 중 오류: {e}")
                    stats.error_count += 1
                    continue
            
            # 통계 업데이트
            stats.end_time = datetime.now()
            stats.total_collected = len(all_entries)
            
            # 결과 로깅
            duration = (stats.end_time - stats.start_time).total_seconds()
            logger.info(f"🎯 REGTECH 수집 완료:")
            logger.info(f"   - 수집 기간: {start_date} ~ {end_date}")
            logger.info(f"   - 처리된 페이지: {stats.pages_processed}")
            logger.info(f"   - 총 수집 IP: {stats.total_collected}")
            logger.info(f"   - 소요 시간: {duration:.1f}초")
            logger.info(f"   - 오류 횟수: {stats.error_count}")
            
            return all_entries
            
        except Exception as e:
            logger.error(f"❌ REGTECH 수집 실패: {e}")
            return []
    
    def _parse_html_response(self, html_content: str) -> List[BlacklistEntry]:
        """HTML 응답에서 IP 데이터 추출"""
        entries = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # "요주의 IP 목록" 테이블 찾기
            table = None
            for caption in soup.find_all('caption'):
                if '요주의 IP 목록' in caption.get_text():
                    table = caption.find_parent('table')
                    break
            
            if not table:
                logger.warning("⚠️ 요주의 IP 목록 테이블을 찾을 수 없습니다")
                return entries
            
            # 데이터가 없는 경우 체크
            if '총 <em>0</em>' in html_content:
                logger.info("ℹ️ 해당 페이지에 데이터가 없습니다")
                return entries
            
            # tbody에서 행 추출
            tbody = table.find('tbody')
            if not tbody:
                logger.warning("⚠️ tbody를 찾을 수 없습니다")
                return entries
            
            rows = tbody.find_all('tr')
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 6:
                    try:
                        ip_address = cells[0].get_text().strip()
                        country = cells[1].get_text().strip()
                        reason = cells[2].get_text().strip()
                        registration_date = cells[3].get_text().strip()
                        release_date = cells[4].get_text().strip()
                        
                        # IP 주소 유효성 검증
                        if self._is_valid_ip(ip_address):
                            # 등록일 파싱
                            detection_date = self._parse_date(registration_date)
                            
                            entry = BlacklistEntry(
                                ip_address=ip_address,
                                source='REGTECH',
                                detection_date=detection_date,
                                reason=f"{reason} ({country})",
                                threat_level='medium',
                                is_active=True
                            )
                            
                            entries.append(entry)
                        else:
                            logger.warning(f"⚠️ 유효하지 않은 IP 주소: {ip_address}")
                            
                    except Exception as e:
                        logger.warning(f"⚠️ 행 파싱 실패: {e}")
                        continue
            
        except Exception as e:
            logger.error(f"❌ HTML 파싱 실패: {e}")
        
        return entries
    
    def _is_valid_ip(self, ip_address: str) -> bool:
        """IP 주소 유효성 검증"""
        import ipaddress
        try:
            ipaddress.ip_address(ip_address)
            return True
        except ValueError:
            return False
    
    def _parse_date(self, date_str: str) -> datetime:
        """날짜 문자열 파싱"""
        try:
            # 다양한 날짜 형식 처리
            date_formats = [
                '%Y-%m-%d',
                '%Y.%m.%d',
                '%Y/%m/%d',
                '%Y-%m-%d %H:%M:%S',
                '%Y.%m.%d %H:%M:%S'
            ]
            
            for date_format in date_formats:
                try:
                    return datetime.strptime(date_str.strip(), date_format)
                except ValueError:
                    continue
            
            # 파싱 실패 시 현재 시간 반환
            logger.warning(f"⚠️ 날짜 파싱 실패: {date_str}, 현재 시간 사용")
            return datetime.now()
            
        except Exception as e:
            logger.warning(f"⚠️ 날짜 파싱 오류: {e}, 현재 시간 사용")
            return datetime.now()
    
    def test_connection(self) -> bool:
        """연결 테스트"""
        try:
            logger.info("🔍 REGTECH 연결 테스트 중...")
            
            response = self.session.get(
                f"{self.base_url}/fcti/securityAdvisory/advisoryList",
                timeout=10
            )
            
            success = response.status_code == 200
            
            if success:
                logger.info("✅ REGTECH 연결 테스트 성공")
                
                # 로그인 상태 확인
                if 'regtech-va' in self.session.cookies:
                    logger.info("✅ 인증 상태 확인됨")
                else:
                    logger.warning("⚠️ 인증 쿠키가 없습니다")
                    
            else:
                logger.error(f"❌ REGTECH 연결 테스트 실패: HTTP {response.status_code}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ REGTECH 연결 테스트 오류: {e}")
            return False


def create_regtech_collector():
    """REGTECH 수집기 팩토리 함수"""
    return RegtechEnhancedCollector()


if __name__ == "__main__":
    # 테스트 실행
    collector = RegtechEnhancedCollector()
    
    if collector.test_connection():
        entries = collector.collect_from_web()
        print(f"수집된 IP 개수: {len(entries)}")
        
        if entries:
            print("첫 번째 IP 예시:")
            print(f"  IP: {entries[0].ip_address}")
            print(f"  출처: {entries[0].source}")
            print(f"  탐지일: {entries[0].detection_date}")
            print(f"  이유: {entries[0].reason}")
    else:
        print("연결 테스트 실패")