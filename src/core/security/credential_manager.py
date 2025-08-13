"""
보안 자격증명 관리 시스템

REGTECH, SECUDIUM 등 외부 서비스 자격증명을 안전하게 관리합니다.
환경 변수, 파일, 시크릿 매니저 등 다양한 소스를 지원합니다.
"""

import os
import json
import base64
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .credential_info import CredentialInfo

logger = logging.getLogger(__name__)



class CredentialEncryption:
    """자격증명 암호화 클래스"""
    
    def __init__(self, master_key: Optional[str] = None):
        """암호화 초기화
        
        Args:
            master_key: 마스터 키 (없으면 환경변수나 생성)
        """
        self.master_key = master_key or self._get_or_create_master_key()
        self.fernet = self._create_fernet(self.master_key)
    
    def _get_or_create_master_key(self) -> str:
        """마스터 키 획득 또는 생성"""
        # 환경변수에서 키 확인
        master_key = os.getenv('CREDENTIAL_MASTER_KEY')
        if master_key:
            return master_key
        
        # 키 파일에서 확인
        key_file = Path('instance/.credential_key')
        if key_file.exists():
            return key_file.read_text().strip()
        
        # 새 키 생성
        new_key = Fernet.generate_key().decode()
        
        # 키 파일에 저장 (안전한 권한으로)
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_text(new_key)
        key_file.chmod(0o600)  # 소유자만 읽기/쓰기
        
        logger.info("새로운 자격증명 마스터 키를 생성했습니다.")
        return new_key
    
    def _create_fernet(self, master_key: str) -> Fernet:
        """Fernet 암호화 객체 생성"""
        # 키 길이가 맞지 않으면 PBKDF2로 파생
        if len(master_key) != 44:  # Base64 encoded 32 bytes = 44 chars
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'blacklist_credential_salt',
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        else:
            key = master_key.encode()
        
        return Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """문자열 암호화"""
        encrypted_bytes = self.fernet.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted_bytes).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """문자열 복호화"""
        encrypted_bytes = base64.urlsafe_b64decode(ciphertext.encode())
        decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
        return decrypted_bytes.decode()


class CredentialManager:
    """자격증명 관리자"""
    
    def __init__(self, 
                 config_file: Optional[str] = None,
                 enable_encryption: bool = True):
        """자격증명 관리자 초기화
        
        Args:
            config_file: 자격증명 설정 파일 경로
            enable_encryption: 암호화 사용 여부
        """
        self.config_file = config_file or 'instance/credentials.json'
        self.enable_encryption = enable_encryption
        self.encryption = CredentialEncryption() if enable_encryption else None
        self.credentials: Dict[str, CredentialInfo] = {}
        
        # 설정 파일에서 자격증명 로드
        self._load_credentials()
        
        # 환경변수에서 자격증명 로드
        self._load_from_environment()
    
    def _load_credentials(self):
        """설정 파일에서 자격증명 로드"""
        config_path = Path(self.config_file)
        if not config_path.exists():
            logger.info("자격증명 설정 파일이 없습니다. 새로 생성합니다.")
            return
        
        try:
            with open(config_path) as f:
                data = json.load(f)
            
            for service, cred_data in data.items():
                # 암호화된 패스워드 복호화
                password = cred_data['password']
                if cred_data.get('is_encrypted', False) and self.encryption:
                    try:
                        password = self.encryption.decrypt(password)
                    except Exception as e:
                        logger.error(f"자격증명 복호화 실패 ({service}): {e}")
                        continue
                
                credential = CredentialInfo(
                    service=service,
                    username=cred_data['username'],
                    password=password,
                    additional_data=cred_data.get('additional_data', {}),
                    expires_at=datetime.fromisoformat(cred_data['expires_at']) 
                        if cred_data.get('expires_at') else None,
                    created_at=datetime.fromisoformat(cred_data.get('created_at', 
                        datetime.now().isoformat())),
                    is_encrypted=cred_data.get('is_encrypted', False)
                )
                
                self.credentials[service] = credential
            
            logger.info(f"{len(self.credentials)}개의 자격증명을 로드했습니다.")
            
        except Exception as e:
            logger.error(f"자격증명 로드 실패: {e}")
    
    def _load_from_environment(self):
        """환경변수에서 자격증명 로드"""
        # 지원되는 서비스들
        services = {
            'regtech': {
                'username_var': 'REGTECH_USERNAME',
                'password_var': 'REGTECH_PASSWORD'
            },
            'secudium': {
                'username_var': 'SECUDIUM_USERNAME',
                'password_var': 'SECUDIUM_PASSWORD'
            },
            'api': {
                'username_var': 'API_USERNAME',
                'password_var': 'API_PASSWORD'
            }
        }
        
        for service, vars_info in services.items():
            username = os.getenv(vars_info['username_var'])
            password = os.getenv(vars_info['password_var'])
            
            if username and password:
                # 환경변수가 우선권을 가짐
                self.credentials[service] = CredentialInfo(
                    service=service,
                    username=username,
                    password=password,
                    additional_data={'source': 'environment'}
                )
                logger.debug(f"환경변수에서 {service} 자격증명을 로드했습니다.")
    
    def save_credentials(self):
        """자격증명을 파일에 저장"""
        config_path = Path(self.config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {}
        for service, credential in self.credentials.items():
            # 환경변수 소스는 저장하지 않음
            if credential.additional_data.get('source') == 'environment':
                continue
            
            cred_data = credential.to_dict()
            
            # 패스워드 암호화
            if self.enable_encryption and self.encryption and not credential.is_encrypted:
                cred_data['password'] = self.encryption.encrypt(credential.password)
                cred_data['is_encrypted'] = True
            
            data[service] = cred_data
        
        try:
            with open(config_path, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 파일 권한 설정 (소유자만 읽기/쓰기)
            config_path.chmod(0o600)
            
            logger.info(f"자격증명을 {config_path}에 저장했습니다.")
            
        except Exception as e:
            logger.error(f"자격증명 저장 실패: {e}")
            raise
    
    def add_credential(self, 
                      service: str, 
                      username: str, 
                      password: str,
                      additional_data: Optional[Dict[str, Any]] = None,
                      expires_at: Optional[datetime] = None) -> bool:
        """새 자격증명 추가"""
        try:
            credential = CredentialInfo(
                service=service,
                username=username,
                password=password,
                additional_data=additional_data or {},
                expires_at=expires_at
            )
            
            self.credentials[service] = credential
            logger.info(f"{service} 자격증명을 추가했습니다.")
            return True
            
        except Exception as e:
            logger.error(f"자격증명 추가 실패 ({service}): {e}")
            return False
    
    def get_credential(self, service: str) -> Optional[CredentialInfo]:
        """서비스 자격증명 조회"""
        credential = self.credentials.get(service)
        if credential:
            credential.update_last_used()
            
            # 만료 확인
            if credential.is_expired():
                logger.warning(f"{service} 자격증명이 만료되었습니다.")
                return None
            
            # 곧 만료 경고
            if credential.expires_soon():
                logger.warning(f"{service} 자격증명이 곧 만료됩니다.")
        
        return credential
    
    def update_credential(self, 
                         service: str, 
                         username: Optional[str] = None,
                         password: Optional[str] = None,
                         additional_data: Optional[Dict[str, Any]] = None,
                         expires_at: Optional[datetime] = None) -> bool:
        """기존 자격증명 업데이트"""
        if service not in self.credentials:
            logger.error(f"서비스 {service}의 자격증명이 없습니다.")
            return False
        
        try:
            credential = self.credentials[service]
            
            if username is not None:
                credential.username = username
            if password is not None:
                credential.password = password
            if additional_data is not None:
                credential.additional_data.update(additional_data)
            if expires_at is not None:
                credential.expires_at = expires_at
            
            logger.info(f"{service} 자격증명을 업데이트했습니다.")
            return True
            
        except Exception as e:
            logger.error(f"자격증명 업데이트 실패 ({service}): {e}")
            return False
    
    def remove_credential(self, service: str) -> bool:
        """자격증명 제거"""
        if service in self.credentials:
            del self.credentials[service]
            logger.info(f"{service} 자격증명을 제거했습니다.")
            return True
        else:
            logger.warning(f"서비스 {service}의 자격증명이 없습니다.")
            return False
    
    def list_services(self) -> list:
        """등록된 서비스 목록 반환"""
        return list(self.credentials.keys())
    
    def validate_credential(self, service: str) -> Dict[str, Any]:
        """자격증명 유효성 검증"""
        credential = self.get_credential(service)
        if not credential:
            return {
                'valid': False,
                'error': '자격증명이 없습니다.'
            }
        
        validation_result = {
            'valid': True,
            'service': service,
            'username': credential.username,
            'is_expired': credential.is_expired(),
            'expires_soon': credential.expires_soon(),
            'last_used': credential.last_used,
            'created_at': credential.created_at
        }
        
        if credential.is_expired():
            validation_result['valid'] = False
            validation_result['error'] = '자격증명이 만료되었습니다.'
        
        # 서비스별 추가 검증
        if service == 'regtech':
            validation_result.update(self._validate_regtech_credential(credential))
        elif service == 'secudium':
            validation_result.update(self._validate_secudium_credential(credential))
        
        return validation_result
    
    def _validate_regtech_credential(self, credential: CredentialInfo) -> Dict[str, Any]:
        """REGTECH 자격증명 유효성 검증"""
        # 실제 API 호출 없이 기본 검증만 수행
        validation = {}
        
        if not credential.username or not credential.password:
            validation['valid'] = False
            validation['error'] = 'REGTECH 사용자명 또는 패스워드가 비어있습니다.'
        
        # 사용자명 형식 검증 (이메일 또는 아이디)
        if '@' in credential.username:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, credential.username):
                validation['warning'] = 'REGTECH 이메일 형식이 올바르지 않을 수 있습니다.'
        
        return validation
    
    def _validate_secudium_credential(self, credential: CredentialInfo) -> Dict[str, Any]:
        """SECUDIUM 자격증명 유효성 검증"""
        validation = {}
        
        if not credential.username or not credential.password:
            validation['valid'] = False
            validation['error'] = 'SECUDIUM 사용자명 또는 패스워드가 비어있습니다.'
        
        # 패스워드 복잡성 검증
        password = credential.password
        if len(password) < 8:
            validation['warning'] = 'SECUDIUM 패스워드가 너무 짧을 수 있습니다.'
        
        return validation
    
    def get_status_report(self) -> Dict[str, Any]:
        """자격증명 상태 보고서"""
        report = {
            'total_credentials': len(self.credentials),
            'services': [],
            'expired_count': 0,
            'expiring_soon_count': 0,
            'warnings': []
        }
        
        for service, credential in self.credentials.items():
            service_info = {
                'service': service,
                'username': credential.username,
                'is_expired': credential.is_expired(),
                'expires_soon': credential.expires_soon(),
                'last_used': credential.last_used.isoformat() if credential.last_used else None,
                'source': credential.additional_data.get('source', 'file')
            }
            
            if credential.is_expired():
                report['expired_count'] += 1
                report['warnings'].append(f"{service} 자격증명이 만료되었습니다.")
            elif credential.expires_soon():
                report['expiring_soon_count'] += 1
                report['warnings'].append(f"{service} 자격증명이 곧 만료됩니다.")
            
            report['services'].append(service_info)
        
        return report
    
    def rotate_credentials(self, service: str, new_password: str) -> bool:
        """자격증명 로테이션"""
        if service not in self.credentials:
            logger.error(f"서비스 {service}의 자격증명이 없습니다.")
            return False
        
        old_credential = self.credentials[service]
        
        # 백업 생성
        backup_data = {
            'old_password': old_credential.password,
            'rotated_at': datetime.now().isoformat()
        }
        
        # 새 패스워드 설정
        success = self.update_credential(
            service=service,
            password=new_password,
            additional_data={'rotation_history': backup_data}
        )
        
        if success:
            logger.info(f"{service} 자격증명 로테이션 완료")
        
        return success


# 전역 자격증명 관리자 인스턴스
_credential_manager = None

def get_credential_manager() -> CredentialManager:
    """전역 자격증명 관리자 인스턴스 반환"""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    return _credential_manager

def setup_default_credentials():
    """기본 자격증명 설정"""
    manager = get_credential_manager()
    
    # REGTECH 자격증명 확인/추가
    if not manager.get_credential('regtech'):
        regtech_user = os.getenv('REGTECH_USERNAME')
        regtech_pass = os.getenv('REGTECH_PASSWORD')
        
        if regtech_user and regtech_pass:
            manager.add_credential(
                service='regtech',
                username=regtech_user,
                password=regtech_pass,
                additional_data={'source': 'environment'}
            )
    
    # SECUDIUM 자격증명 확인/추가
    if not manager.get_credential('secudium'):
        secudium_user = os.getenv('SECUDIUM_USERNAME')
        secudium_pass = os.getenv('SECUDIUM_PASSWORD')
        
        if secudium_user and secudium_pass:
            manager.add_credential(
                service='secudium',
                username=secudium_user,
                password=secudium_pass,
                additional_data={'source': 'environment'}
            )
    
    return manager
