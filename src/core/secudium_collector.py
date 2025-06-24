#!/usr/bin/env python3
"""
SECUDIUM 자동 수집 시스템
토큰 기반 인증을 사용하여 블랙리스트 데이터 수집
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path
import re
import time

from src.config.settings import settings

logger = logging.getLogger(__name__)

class SecudiumCollector:
    """
    SECUDIUM 자동 수집 시스템
    - 토큰 기반 인증
    - 블랙리스트 IP 수집
    - API 기반 데이터 접근
    """
    
    def __init__(self, data_dir: str, cache_backend=None):
        self.data_dir = data_dir
        self.secudium_dir = os.path.join(data_dir, 'secudium')
        
        # 디렉토리 생성
        os.makedirs(self.secudium_dir, exist_ok=True)
        
        # SECUDIUM API 설정
        self.base_url = settings.secudium_base_url
        self.login_endpoint = "/isap-api/loginProcess"
        self.blacklist_endpoint = "/isap-api/secinfo/list/ictiboard"  # Document 분석 결과로 수정
        self.myinfo_endpoint = "/isap-api/myinfo"
        
        # 인증 토큰
        self.auth_token = None
        
        logger.info(f"SECUDIUM 수집기 초기화 완료: {self.secudium_dir}")
    
    def login(self) -> bool:
        """
        SECUDIUM 로그인 및 토큰 획득
        """
        try:
            username = settings.secudium_username
            password = settings.secudium_password
            
            if not username or not password:
                logger.warning("SECUDIUM 자격증명이 없습니다")
                return False
            
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': f"{self.base_url}/"
            })
            
            # 세션 저장
            self.last_session = session
            
            # 1. 메인 페이지 접속 (세션 초기화)
            main_resp = session.get(f"{self.base_url}/")
            if main_resp.status_code != 200:
                logger.error(f"메인 페이지 접속 실패: {main_resp.status_code}")
                return False
            
            # 2. 로그인 요청 (Document 분석 결과 - 정확한 필드명 사용)
            login_data = {
                'lang': 'ko',           # Document에서 확인된 순서대로
                'is_otp': 'N',          # OTP 사용 안함
                'login_name': username, # Document 분석: login_name 필드
                'password': password,   # Document 분석: password 필드
                'otp_value': ''         # OTP 값 비어있음 (is_otp가 N이므로)
            }
            
            login_resp = session.post(
                f"{self.base_url}{self.login_endpoint}",
                data=login_data
            )
            
            if login_resp.status_code == 200:
                # 응답에서 토큰 추출 (JavaScript 코드 분석 결과)
                try:
                    response_data = login_resp.json() if login_resp.text else {}
                    logger.debug(f"로그인 응답 데이터: {response_data}")
                    
                    # JavaScript에서 확인한 응답 구조: data.response.error 체크
                    if 'response' in response_data:
                        inner_response = response_data['response']
                        
                        # JavaScript 로직: error 필드로 성공/실패 판단
                        error = inner_response.get('error')
                        
                        if error:
                            # 에러가 있는 경우
                            error_message = inner_response.get('message', 'Unknown error')
                            logger.error(f"SECUDIUM 로그인 에러: {error_message}")
                            
                            # already.login 에러 처리 (JavaScript에서 확인된 패턴)
                            if 'already' in error_message.lower() or inner_response.get('code') == 'already.login':
                                logger.warning(f"SECUDIUM 중복 로그인 감지: {username}")
                                # 중복 로그인이어도 세션은 유효할 수 있음
                                self.auth_token = session.cookies.get('JSESSIONID', 'session_token')
                                return True
                            
                            return False
                        else:
                            # 에러가 없으면 성공 - 토큰 추출
                            if 'token' in inner_response:
                                self.auth_token = inner_response['token']
                                logger.info(f"SECUDIUM 로그인 성공: {username}")
                                return True
                            else:
                                logger.warning("토큰이 응답에 없음, 세션 쿠키 사용")
                                self.auth_token = session.cookies.get('JSESSIONID', 'session_token')
                                return True
                    
                    # 기존 구조 호환성 (response 필드가 없는 경우)
                    elif 'token' in response_data:
                        self.auth_token = response_data['token']
                        logger.info(f"SECUDIUM 로그인 성공 (직접 토큰): {username}")
                        return True
                    elif 'error' in response_data and not response_data['error']:
                        # error가 false인 경우 성공
                        self.auth_token = response_data.get('token', 'session_token')
                        logger.info(f"SECUDIUM 로그인 성공 (에러 없음): {username}")
                        return True
                    
                except Exception as e:
                    logger.error(f"JSON 응답 파싱 실패: {e}")
                
                # 헤더에서 토큰 확인
                if 'X-Auth-Token' in login_resp.headers:
                    self.auth_token = login_resp.headers['X-Auth-Token']
                    logger.info(f"SECUDIUM 로그인 성공 (헤더): {username}")
                    return True
                    
                # 쿠키에서 토큰 확인
                for cookie in session.cookies:
                    if 'token' in cookie.name.lower():
                        self.auth_token = cookie.value
                        logger.info(f"SECUDIUM 로그인 성공 (쿠키): {username}")
                        return True
            
            logger.error(f"SECUDIUM 로그인 실패: {login_resp.status_code}")
            return False
            
        except Exception as e:
            logger.error(f"SECUDIUM 로그인 중 오류: {e}")
            return False
    
    def collect_blacklist_data(self, count: int = 100) -> List[Dict[str, Any]]:
        """
        블랙리스트 IP 데이터 수집
        """
        if not self.auth_token:
            logger.error("인증 토큰이 없습니다. 먼저 로그인하세요.")
            return []
        
        try:
            # 로그인 시 사용한 세션 유지
            session = self.last_session if hasattr(self, 'last_session') else requests.Session()
            
            # Document 분석 결과에 따른 파라미터
            params = {
                'sdate': '',                    # Document 분석: 시작 날짜 (빈 값은 전체)
                'edate': '',                    # Document 분석: 종료 날짜 (빈 값은 전체)
                'dateKey': 'i.reg_date',        # Document 분석: 날짜 필드
                'count': str(count),            # Document 분석: 최대 100개
                'filter': ''                    # Document 분석: 필터 (빈 값은 전체)
            }
            
            # 세션 쿠키 확인
            logger.debug(f"세션 쿠키: {dict(session.cookies)}")
            
            # 기본 헤더만 사용 (세션 쿠키로 인증)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Referer': f"{self.base_url}/",
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            # X-Auth-Token은 쿠키에 있으면 사용
            if self.auth_token and self.auth_token != 'session_token':
                headers['X-Auth-Token'] = self.auth_token
            
            response = session.get(
                f"{self.base_url}{self.blacklist_endpoint}",
                params=params,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, dict) and 'data' in data:
                    raw_data = data['data']
                    logger.info(f"SECUDIUM에서 {len(raw_data)}개 레코드 수집")
                    
                    # 데이터 변환
                    blacklist_data = []
                    for item in raw_data:
                        if 'ip' in item or 'IP' in item:
                            ip = item.get('ip') or item.get('IP', '')
                            if self._is_valid_ip(ip):
                                blacklist_data.append({
                                    'ip': ip,
                                    'country': item.get('country', 'Unknown'),
                                    'attack_type': item.get('attack_type', 'SECUDIUM'),
                                    'source': 'SECUDIUM',
                                    'detection_date': item.get('reg_date', datetime.now().strftime('%Y-%m-%d')),
                                    'description': item.get('description', '')
                                })
                    
                    logger.info(f"유효한 IP {len(blacklist_data)}개 추출")
                    return blacklist_data
                
            logger.error(f"SECUDIUM 데이터 수집 실패: {response.status_code}")
            return []
            
        except Exception as e:
            logger.error(f"SECUDIUM 데이터 수집 중 오류: {e}")
            return []
    
    def _is_valid_ip(self, ip: str) -> bool:
        """
        IP 주소 유효성 검증
        """
        try:
            if not ip or not isinstance(ip, str):
                return False
            
            # IP 패턴 검증
            ip_pattern = re.compile(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$')
            if not ip_pattern.match(ip):
                return False
            
            # 각 옥텟 범위 검증
            parts = ip.split('.')
            for part in parts:
                if not 0 <= int(part) <= 255:
                    return False
            
            # 사설 IP 제외
            if parts[0] == '192' and parts[1] == '168':
                return False
            if parts[0] == '10':
                return False
            if parts[0] == '172' and 16 <= int(parts[1]) <= 31:
                return False
            
            return True
            
        except:
            return False
    
    def auto_collect(self) -> Dict[str, Any]:
        """
        자동 수집 수행
        """
        try:
            logger.info("SECUDIUM 자동 수집 시작")
            
            # 1. 로그인
            if not self.login():
                return {
                    'success': False,
                    'message': 'SECUDIUM 로그인 실패',
                    'total_collected': 0
                }
            
            # 2. 데이터 수집
            collected_data = self.collect_blacklist_data(count=1000)
            
            if collected_data:
                # 3. 데이터 저장
                save_result = self._save_collected_data(collected_data)
                
                return {
                    'success': True,
                    'message': f'SECUDIUM 수집 완료: {len(collected_data)}개 IP',
                    'total_collected': len(collected_data),
                    'save_result': save_result
                }
            else:
                return {
                    'success': False,
                    'message': 'SECUDIUM 데이터 수집 실패: 데이터 없음',
                    'total_collected': 0
                }
                
        except Exception as e:
            logger.error(f"SECUDIUM 자동 수집 오류: {e}")
            return {
                'success': False,
                'message': f'SECUDIUM 수집 오류: {e}',
                'total_collected': 0
            }
    
    def _save_collected_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        수집된 데이터 저장
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # JSON 파일로 저장
            json_file = os.path.join(self.secudium_dir, f'secudium_blacklist_{timestamp}.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # CSV 파일로도 저장
            csv_file = os.path.join(self.secudium_dir, f'secudium_blacklist_{timestamp}.csv')
            with open(csv_file, 'w', encoding='utf-8') as f:
                f.write('ip,country,attack_type,source,detection_date,description\n')
                for item in data:
                    f.write(f"{item['ip']},{item.get('country', '')},{item.get('attack_type', '')},{item['source']},{item.get('detection_date', '')},{item.get('description', '')}\n")
            
            logger.info(f"SECUDIUM 데이터 저장 완료: {json_file}")
            
            return {
                'success': True,
                'json_file': json_file,
                'csv_file': csv_file,
                'count': len(data)
            }
            
        except Exception as e:
            logger.error(f"SECUDIUM 데이터 저장 오류: {e}")
            return {
                'success': False,
                'error': str(e)
            }

def create_secudium_collector(data_dir: str, cache_backend=None) -> SecudiumCollector:
    """SECUDIUM 수집기 팩토리 함수"""
    return SecudiumCollector(data_dir=data_dir, cache_backend=cache_backend)
