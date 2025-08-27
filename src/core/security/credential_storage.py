#!/usr/bin/env python3
"""
자격증명 저장소 관리 시스템

JSON 파일 기반 자격증명 저장 및 환경변수 로드 기능을 제공합니다.
안전한 파일 권한 및 암호화 상태 관리를 지원합니다.

관련 패키지 문서:
- json: https://docs.python.org/3/library/json.html
- pathlib: https://docs.python.org/3/library/pathlib.html

입력 예시:
- config_file: "instance/credentials.json"
- 환경변수: REGTECH_USERNAME, REGTECH_PASSWORD

출력 예시:
- 로드된 자격증명 정보 딕셔너리
- 저장된 자격증명 파일
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# 조건부 임포트로 독립 실행 지원
try:
    from .credential_encryption import CredentialEncryption
    from .credential_info import CredentialInfo
except ImportError:
    import os
    import sys

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from credential_encryption import CredentialEncryption
    from credential_info import CredentialInfo

logger = logging.getLogger(__name__)


class CredentialStorage:
    """자격증명 저장소 클래스"""

    def __init__(
        self, config_file: Optional[str] = None, enable_encryption: bool = True
    ):
        """저장소 초기화

        Args:
            config_file: 자격증명 설정 파일 경로
            enable_encryption: 암호화 사용 여부
        """
        self.config_file = config_file or "instance/credentials.json"
        self.enable_encryption = enable_encryption
        self.encryption = CredentialEncryption() if enable_encryption else None
        self.credentials: Dict[str, CredentialInfo] = {}

    def load_credentials(self) -> Dict[str, CredentialInfo]:
        """설정 파일과 환경변수에서 자격증명 로드"""
        self.credentials = {}

        # 설정 파일에서 로드
        self._load_from_file()

        # 환경변수에서 로드 (우선권)
        self._load_from_environment()

        return self.credentials

    def _load_from_file(self):
        """설정 파일에서 자격증명 로드"""
        config_path = Path(self.config_file)
        if not config_path.exists():
            logger.info("자격증명 설정 파일이 없습니다. 새로 생성합니다.")
            return

        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)

            for service, cred_data in data.items():
                credential = self._parse_credential_data(service, cred_data)
                if credential:
                    self.credentials[service] = credential

            logger.info(f"{len(self.credentials)}개의 자격증명을 로드했습니다.")

        except Exception as e:
            logger.error(f"자격증명 로드 실패: {e}")

    def _parse_credential_data(
        self, service: str, cred_data: Dict[str, Any]
    ) -> Optional[CredentialInfo]:
        """자격증명 데이터 파싱"""
        try:
            # 암호화된 패스워드 복호화
            password = cred_data["password"]
            if cred_data.get("is_encrypted", False) and self.encryption:
                try:
                    password = self.encryption.decrypt(password)
                except Exception as e:
                    logger.error(f"자격증명 복호화 실패 ({service}): {e}")
                    return None

            credential = CredentialInfo(
                service=service,
                username=cred_data["username"],
                password=password,
                additional_data=cred_data.get("additional_data", {}),
                expires_at=(
                    datetime.fromisoformat(cred_data["expires_at"])
                    if cred_data.get("expires_at")
                    else None
                ),
                created_at=datetime.fromisoformat(
                    cred_data.get("created_at", datetime.now().isoformat())
                ),
                is_encrypted=cred_data.get("is_encrypted", False),
            )

            return credential

        except Exception as e:
            logger.error(f"자격증명 데이터 파싱 실패 ({service}): {e}")
            return None

    def _load_from_environment(self):
        """환경변수에서 자격증명 로드"""
        # 지원되는 서비스들
        services = {
            "regtech": {
                "username_var": "REGTECH_USERNAME",
                "password_var": "REGTECH_PASSWORD",
            },
            "secudium": {
                "username_var": "SECUDIUM_USERNAME",
                "password_var": "SECUDIUM_PASSWORD",
            },
            "api": {"username_var": "API_USERNAME", "password_var": "API_PASSWORD"},
        }

        for service, vars_info in services.items():
            username = os.getenv(vars_info["username_var"])
            password = os.getenv(vars_info["password_var"])

            if username and password:
                # 환경변수가 우선권을 가짐
                self.credentials[service] = CredentialInfo(
                    service=service,
                    username=username,
                    password=password,
                    additional_data={"source": "environment"},
                )
                logger.debug(f"환경변수에서 {service} 자격증명을 로드했습니다.")

    def save_credentials(self, credentials: Dict[str, CredentialInfo]):
        """자격증명을 파일에 저장"""
        config_path = Path(self.config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        for service, credential in credentials.items():
            # 환경변수 소스는 저장하지 않음
            if credential.additional_data.get("source") == "environment":
                continue

            cred_data = credential.to_dict()

            # 패스워드 암호화
            if (
                self.enable_encryption
                and self.encryption
                and not credential.is_encrypted
            ):
                cred_data["password"] = self.encryption.encrypt(credential.password)
                cred_data["is_encrypted"] = True

            data[service] = cred_data

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # 파일 권한 설정 (소유자만 읽기/쓰기)
            config_path.chmod(0o600)

            logger.info(f"자격증명을 {config_path}에 저장했습니다.")

        except Exception as e:
            logger.error(f"자격증명 저장 실패: {e}")
            raise

    def backup_credentials(self, backup_path: Optional[str] = None) -> str:
        """자격증명 백업"""
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"instance/credentials_backup_{timestamp}.json"

        backup_file = Path(backup_path)
        backup_file.parent.mkdir(parents=True, exist_ok=True)

        # 현재 파일 복사
        config_path = Path(self.config_file)
        if config_path.exists():
            backup_file.write_bytes(config_path.read_bytes())
            backup_file.chmod(0o600)
            logger.info(f"자격증명을 {backup_path}에 백업했습니다.")

        return backup_path

    def restore_credentials(self, backup_path: str):
        """자격증명 복원"""
        backup_file = Path(backup_path)
        if not backup_file.exists():
            raise FileNotFoundError(f"백업 파일을 찾을 수 없습니다: {backup_path}")

        config_path = Path(self.config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # 백업 파일 복사
        config_path.write_bytes(backup_file.read_bytes())
        config_path.chmod(0o600)

        # 자격증명 재로드
        self.load_credentials()

        logger.info(f"자격증명을 {backup_path}에서 복원했습니다.")

    def get_file_info(self) -> Dict[str, Any]:
        """자격증명 파일 정보 반환"""
        config_path = Path(self.config_file)

        if not config_path.exists():
            return {
                "exists": False,
                "path": str(config_path),
                "size": 0,
                "modified": None,
                "permissions": None,
            }

        stat = config_path.stat()
        return {
            "exists": True,
            "path": str(config_path),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "permissions": oct(stat.st_mode)[-3:],
        }


if __name__ == "__main__":
    import sys
    import tempfile

    # 실제 데이터로 검증
    all_validation_failures = []
    total_tests = 0

    # 임시 디렉터리 생성
    with tempfile.TemporaryDirectory() as temp_dir:
        test_config_file = f"{temp_dir}/test_credentials.json"

        # 테스트 1: 스토리지 초기화
        total_tests += 1
        try:
            storage = CredentialStorage(test_config_file, enable_encryption=False)
            if storage.config_file != test_config_file:
                all_validation_failures.append(
                    f"스토리지 초기화: 예상 '{test_config_file}', 실제 '{storage.config_file}'"
                )
        except Exception as e:
            all_validation_failures.append(f"스토리지 초기화 오류: {e}")

        # 테스트 2: 자격증명 저장 및 로드
        total_tests += 1
        try:
            test_credential = CredentialInfo(
                service="test_service", username="test_user", password="test_pass"
            )

            storage.save_credentials({"test_service": test_credential})
            loaded_credentials = storage.load_credentials()

            if "test_service" not in loaded_credentials:
                all_validation_failures.append(
                    "자격증명 저장/로드: test_service가 로드되지 않음"
                )
            elif loaded_credentials["test_service"].username != "test_user":
                all_validation_failures.append("자격증명 데이터 불일치")
        except Exception as e:
            all_validation_failures.append(f"자격증명 저장/로드 오류: {e}")

        # 테스트 3: 파일 정보 확인
        total_tests += 1
        try:
            file_info = storage.get_file_info()
            if not file_info["exists"]:
                all_validation_failures.append(
                    "파일 정보: 자격증명 파일이 존재하지 않음"
                )
        except Exception as e:
            all_validation_failures.append(f"파일 정보 오류: {e}")

        # 테스트 4: 백업 및 복원
        total_tests += 1
        try:
            backup_path = storage.backup_credentials(f"{temp_dir}/backup.json")

            # 원본 삭제
            Path(test_config_file).unlink()

            # 복원
            storage.restore_credentials(backup_path)
            restored_credentials = storage.load_credentials()

            if "test_service" not in restored_credentials:
                all_validation_failures.append("백업/복원: 복원된 자격증명이 없음")
        except Exception as e:
            all_validation_failures.append(f"백업/복원 오류: {e}")

    # 최종 검증 결과
    if all_validation_failures:
        print(
            f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print("CredentialStorage module is validated and ready for use")
        sys.exit(0)
