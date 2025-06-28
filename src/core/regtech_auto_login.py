#!/usr/bin/env python3
"""
REGTECH 자동 로그인 및 토큰 관리
"""
import os
import json
import logging
import requests
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from pathlib import Path

from src.config.settings import settings

logger = logging.getLogger(__name__)


class RegtechAuth:
    """REGTECH 인증 관리자"""
    
    def __init__(self):
        self.base_url = "https://regtech.fsec.or.kr"
        self.token_file = Path(settings.data_dir) / ".regtech_token.json"
        self.creds_file = Path(settings.data_dir) / ".regtech_credentials.json"
        self.session = None
        self._current_token = None
        self._saved_username = None
        self._saved_password = None
        
        # 저장된 인증 정보 로드
        self._load_saved_credentials()
        
    def _load_saved_credentials(self):
        """저장된 인증 정보 로드"""
        try:
            if self.creds_file.exists():
                with open(self.creds_file, 'r') as f:
                    data = json.load(f)
                    # 환경변수 대신 인스턴스 변수로 저장
                    self._saved_username = data.get('username')
                    self._saved_password = data.get('password')
                    logger.info("저장된 REGTECH 인증 정보 로드됨")
        except Exception as e:
            logger.error(f"인증 정보 로드 오류: {e}")
        
    def get_valid_token(self) -> Optional[str]:
        """유효한 Bearer Token 반환 (필요시 자동 갱신)"""
        # 1. 메모리에 토큰이 있으면 확인
        if self._current_token and self._is_token_valid(self._current_token):
            return self._current_token
            
        # 2. 파일에서 토큰 로드
        token = self._load_token_from_file()
        if token and self._is_token_valid(token):
            self._current_token = token
            return token
            
        # 3. 새로 로그인해서 토큰 획득
        logger.info("토큰이 만료되어 새로 로그인합니다")
        token = self._perform_login()
        if token:
            self._current_token = token
            self._save_token_to_file(token)
            return token
            
        return None
        
    def _is_token_valid(self, token: str) -> bool:
        """토큰 유효성 검증"""
        try:
            # Bearer 제거
            jwt_token = token.replace("Bearer", "").strip()
            
            # JWT 디코드 (검증 없이)
            payload = jwt.decode(jwt_token, options={"verify_signature": False})
            
            # 만료 시간 확인
            exp = payload.get('exp', 0)
            now = datetime.now().timestamp()
            
            # 5분 여유를 두고 확인
            if exp > now + 300:
                return True
                
            logger.info(f"토큰 만료됨: {datetime.fromtimestamp(exp)}")
            return False
            
        except Exception as e:
            logger.error(f"토큰 검증 오류: {e}")
            return False
            
    def _load_token_from_file(self) -> Optional[str]:
        """파일에서 토큰 로드"""
        try:
            if self.token_file.exists():
                with open(self.token_file, 'r') as f:
                    data = json.load(f)
                    return data.get('token')
        except Exception as e:
            logger.error(f"토큰 파일 읽기 오류: {e}")
        return None
        
    def _save_token_to_file(self, token: str):
        """토큰을 파일에 저장"""
        try:
            # JWT에서 만료 시간 추출
            jwt_token = token.replace("Bearer", "").strip()
            payload = jwt.decode(jwt_token, options={"verify_signature": False})
            exp = payload.get('exp', 0)
            
            data = {
                'token': token,
                'expires_at': exp,
                'created_at': datetime.now().isoformat(),
                'username': payload.get('username', 'unknown')
            }
            
            # 디렉토리 생성
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.token_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            # 파일 권한 설정 (읽기 전용)
            os.chmod(self.token_file, 0o600)
            
            logger.info(f"토큰 저장 완료: {self.token_file}")
            
        except Exception as e:
            logger.error(f"토큰 저장 오류: {e}")
            
    def _perform_login(self) -> Optional[str]:
        """로그인 수행 및 Bearer Token 획득"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
        })
        
        try:
            # 1. 메인 페이지 접속 (세션 초기화)
            logger.info("REGTECH 메인 페이지 접속...")
            main_resp = session.get(f'{self.base_url}/main/main', timeout=30)
            if main_resp.status_code != 200:
                logger.error(f"메인 페이지 접속 실패: {main_resp.status_code}")
                return None
            time.sleep(1)
            
            # 2. 로그인 페이지 접속
            logger.info("로그인 페이지 접속...")
            login_page = session.get(f'{self.base_url}/login/loginForm', timeout=30)
            if login_page.status_code != 200:
                logger.error(f"로그인 페이지 접속 실패: {login_page.status_code}")
                return None
            time.sleep(1)
            
            # 3. 로그인 수행
            # 저장된 인증정보 우선, 없으면 환경변수
            username = self._saved_username or settings.regtech_username
            password = self._saved_password or settings.regtech_password
            
            if not username or not password:
                logger.error("REGTECH 인증 정보가 설정되지 않았습니다")
                return None
                
            logger.info(f"로그인 시도: {username}")
            
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
                f'{self.base_url}/login/addLogin',
                data=login_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Origin': self.base_url,
                    'Referer': f'{self.base_url}/login/loginForm',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'same-origin',
                    'Sec-Fetch-User': '?1',
                    'Upgrade-Insecure-Requests': '1'
                },
                allow_redirects=True,
                timeout=30
            )
            
            # Bearer Token 확인
            for cookie in session.cookies:
                if cookie.name == 'regtech-va' and cookie.value.startswith('Bearer'):
                    logger.info("Bearer Token 획득 성공")
                    return cookie.value
                    
            # 리다이렉트 URL 확인
            if 'error=true' in login_resp.url:
                logger.error("로그인 실패: error=true")
                return None
                
            logger.error("Bearer Token을 찾을 수 없음")
            return None
            
        except Exception as e:
            logger.error(f"로그인 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return None
            
    def update_credentials(self, username: str, password: str) -> bool:
        """인증 정보 업데이트 및 테스트"""
        # 임시로 설정
        old_username = self._saved_username
        old_password = self._saved_password
        
        try:
            # 인스턴스 변수에 저장
            self._saved_username = username
            self._saved_password = password
            
            # 로그인 테스트
            token = self._perform_login()
            if token:
                logger.info("새 인증 정보로 로그인 성공")
                self._current_token = token
                self._save_token_to_file(token)
                
                # 설정 파일에 저장
                self._save_credentials(username, password)
                return True
            else:
                # 실패시 롤백
                self._saved_username = old_username
                self._saved_password = old_password
                return False
                
        except Exception as e:
            logger.error(f"인증 정보 업데이트 오류: {e}")
            # 롤백
            self._saved_username = old_username
            self._saved_password = old_password
            return False
            
    def _save_credentials(self, username: str, password: str):
        """인증 정보를 설정 파일에 저장"""
        try:
            self.creds_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'username': username,
                'password': password,
                'updated_at': datetime.now().isoformat()
            }
            
            with open(self.creds_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            # 파일 권한 설정 (소유자만 읽기/쓰기)
            os.chmod(self.creds_file, 0o600)
            
            logger.info("인증 정보 저장 완료")
            
        except Exception as e:
            logger.error(f"인증 정보 저장 오류: {e}")


# 싱글톤 인스턴스
_auth_instance = None

def get_regtech_auth() -> RegtechAuth:
    """REGTECH 인증 인스턴스 반환"""
    global _auth_instance
    if _auth_instance is None:
        _auth_instance = RegtechAuth()
    return _auth_instance