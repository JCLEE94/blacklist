#!/usr/bin/env python3
"""
통합 자격증명 관리 시스템 (메인 관리자)

REGTECH, SECUDIUM 등 외부 서비스 자격증명을 안전하게 관리합니다.
환경 변수, 파일, 시크릿 매니저 등 다양한 소스를 지원합니다.
분할된 모듈들을 통합하여 단일 인터페이스를 제공합니다.

관련 패키지 문서:
- .credential_encryption: 암호화 기능
- .credential_storage: 저장소 관리
- .credential_validation: 검증 시스템

입력 예시:
- config_file: "instance/credentials.json"
- service: "regtech", username: "user", password: "pass"

출력 예시:
- 자격증명 관리 및 검증 결과
- 상태 보고서 및 개선 제안
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# 조건부 임포트로 독립 실행 지원
try:
    from .credential_encryption import CredentialEncryption
    from .credential_info import CredentialInfo
    from .credential_storage import CredentialStorage
    from .credential_validation import CredentialValidator
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from credential_encryption import CredentialEncryption
    from credential_info import CredentialInfo
    from credential_storage import CredentialStorage
    from credential_validation import CredentialValidator

logger = logging.getLogger(__name__)


class CredentialManager:
    """통합 자격증명 관리자"""

    def __init__(
        self, config_file: Optional[str] = None, enable_encryption: bool = True
    ):
        """자격증명 관리자 초기화

        Args:
            config_file: 자격증명 설정 파일 경로
            enable_encryption: 암호화 사용 여부
        """
        self.config_file = config_file or "instance/credentials.json"
        self.enable_encryption = enable_encryption
        
        # 구성 요소 초기화
        self.storage = CredentialStorage(self.config_file, enable_encryption)
        self.validator = CredentialValidator()
        self.encryption = CredentialEncryption() if enable_encryption else None
        
        # 자격증명 로드
        self.credentials = self.storage.load_credentials()

    def add_credential(
        self,
        service: str,
        username: str,
        password: str,
        additional_data: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None,
    ) -> bool:
        """새 자격증명 추가"""
        try:
            credential = CredentialInfo(
                service=service,
                username=username,
                password=password,
                additional_data=additional_data or {},
                expires_at=expires_at,
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

    def update_credential(
        self,
        service: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None,
    ) -> bool:
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

    def list_services(self) -> List[str]:
        """등록된 서비스 목록 반환"""
        return list(self.credentials.keys())

    def validate_credential(self, service: str) -> Dict[str, Any]:
        """자격증명 유효성 검증"""
        credential = self.get_credential(service)
        if not credential:
            return {"valid": False, "error": "자격증명이 없습니다."}

        return self.validator.validate_credential(service, credential)

    def save_credentials(self):
        """자격증명을 파일에 저장"""
        try:
            self.storage.save_credentials(self.credentials)
        except Exception as e:
            logger.error(f"자격증명 저장 실패: {e}")
            raise

    def get_status_report(self) -> Dict[str, Any]:
        """자격증명 상태 보고서"""
        return self.validator.generate_status_report(self.credentials)

    def rotate_credentials(self, service: str, new_password: str) -> bool:
        """자격증명 로테이션"""
        if service not in self.credentials:
            logger.error(f"서비스 {service}의 자격증명이 없습니다.")
            return False

        old_credential = self.credentials[service]

        # 백업 생성
        backup_data = {
            "old_password": old_credential.password,
            "rotated_at": datetime.now().isoformat(),
        }

        # 새 패스워드 설정
        success = self.update_credential(
            service=service,
            password=new_password,
            additional_data={"rotation_history": backup_data},
        )

        if success:
            logger.info(f"{service} 자격증명 로테이션 완료")

        return success

    def backup_credentials(self, backup_path: Optional[str] = None) -> str:
        """자격증명 백업"""
        return self.storage.backup_credentials(backup_path)

    def restore_credentials(self, backup_path: str):
        """자격증명 복원"""
        self.storage.restore_credentials(backup_path)
        self.credentials = self.storage.load_credentials()

    def get_suggestions(self, service: str) -> List[str]:
        """자격증명 개선 제안"""
        credential = self.get_credential(service)
        if not credential:
            return ["자격증명이 존재하지 않습니다."]
        
        return self.validator.suggest_improvements(service, credential)

    def check_strength(self, service: str) -> Dict[str, Any]:
        """자격증명 강도 검사"""
        credential = self.get_credential(service)
        if not credential:
            return {"error": "자격증명이 존재하지 않습니다."}
        
        return self.validator.check_credential_strength(credential)


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
    if not manager.get_credential("regtech"):
        regtech_user = os.getenv("REGTECH_USERNAME")
        regtech_pass = os.getenv("REGTECH_PASSWORD")

        if regtech_user and regtech_pass:
            manager.add_credential(
                service="regtech",
                username=regtech_user,
                password=regtech_pass,
                additional_data={"source": "environment"},
            )

    # SECUDIUM 자격증명 확인/추가
    if not manager.get_credential("secudium"):
        secudium_user = os.getenv("SECUDIUM_USERNAME")
        secudium_pass = os.getenv("SECUDIUM_PASSWORD")

        if secudium_user and secudium_pass:
            manager.add_credential(
                service="secudium",
                username=secudium_user,
                password=secudium_pass,
                additional_data={"source": "environment"},
            )

    return manager


if __name__ == "__main__":
    import sys
    import tempfile
    
    # 실제 데이터로 검증
    all_validation_failures = []
    total_tests = 0
    
    # 임시 디렉터리 생성
    with tempfile.TemporaryDirectory() as temp_dir:
        test_config_file = f"{temp_dir}/test_credentials.json"
        
        # 테스트 1: 관리자 초기화
        total_tests += 1
        try:
            manager = CredentialManager(test_config_file, enable_encryption=False)
            if not hasattr(manager, 'storage') or not hasattr(manager, 'validator'):
                all_validation_failures.append("관리자 초기화: 필수 구성 요소 누락")
        except Exception as e:
            all_validation_failures.append(f"관리자 초기화 오류: {e}")
        
        # 테스트 2: 자격증명 추가/조회
        total_tests += 1
        try:
            success = manager.add_credential(
                service="test_service",
                username="test_user",
                password="test_pass"
            )
            
            if not success:
                all_validation_failures.append("자격증명 추가 실패")
            
            credential = manager.get_credential("test_service")
            if not credential or credential.username != "test_user":
                all_validation_failures.append("자격증명 조회 실패")
        except Exception as e:
            all_validation_failures.append(f"자격증명 추가/조회 오류: {e}")
        
        # 테스트 3: 자격증명 검증
        total_tests += 1
        try:
            validation_result = manager.validate_credential("test_service")
            if not validation_result.get("valid"):
                all_validation_failures.append("자격증명 검증 실패")
        except Exception as e:
            all_validation_failures.append(f"자격증명 검증 오류: {e}")
        
        # 테스트 4: 상태 보고서
        total_tests += 1
        try:
            report = manager.get_status_report()
            if report["total_credentials"] == 0:
                all_validation_failures.append("상태 보고서: 자격증명이 없음")
        except Exception as e:
            all_validation_failures.append(f"상태 보고서 오류: {e}")
        
        # 테스트 5: 전역 관리자
        total_tests += 1
        try:
            global_manager = get_credential_manager()
            if not isinstance(global_manager, CredentialManager):
                all_validation_failures.append("전역 관리자 타입 오류")
        except Exception as e:
            all_validation_failures.append(f"전역 관리자 오류: {e}")
    
    # 최종 검증 결과
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("CredentialManager module is validated and ready for use")
        sys.exit(0)