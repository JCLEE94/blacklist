#!/usr/bin/env python3
"""
자격증명 암호화 시스템

Fernet 대칭 암호화를 사용하여 자격증명을 안전하게 보호합니다.
PBKDF2를 사용한 키 유도 기능을 제공합니다.

관련 패키지 문서:
- cryptography: https://cryptography.io/en/latest/
- Fernet: https://cryptography.io/en/latest/fernet/

입력 예시:
- 평문 자격증명: "password123"
- 마스터 키: "your-master-key" (옵션)

출력 예시:
- 암호화된 자격증명: "gAAAAABhZ...(base64 문자열)"
- 복호화된 자격증명: "password123"
"""

import base64
import logging
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

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
        master_key = os.getenv("CREDENTIAL_MASTER_KEY")
        if master_key:
            return master_key

        # 키 파일에서 확인
        key_file = Path("instance/.credential_key")
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
                salt=b"blacklist_credential_salt",
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        else:
            key = master_key.encode()

        return Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """문자열 암호화"""
        if not plaintext:
            return ""
        encrypted_bytes = self.fernet.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted_bytes).decode()

    def decrypt(self, ciphertext: str) -> str:
        """문자열 복호화"""
        if not ciphertext:
            return ""
        encrypted_bytes = base64.urlsafe_b64decode(ciphertext.encode())
        decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
        return decrypted_bytes.decode()

    def is_encrypted(self, text: str) -> bool:
        """텍스트가 암호화되었는지 확인"""
        try:
            self.decrypt(text)
            return True
        except Exception:
            return False

    def rotate_key(self, new_master_key: str) -> "CredentialEncryption":
        """새로운 키로 교체된 암호화 객체 반환"""
        return CredentialEncryption(new_master_key)


if __name__ == "__main__":
    import sys

    # 실제 데이터로 검증
    all_validation_failures = []
    total_tests = 0

    # 테스트 1: 기본 암호화/복호화
    total_tests += 1
    try:
        encryption = CredentialEncryption()
        test_password = "test_password_123"
        encrypted = encryption.encrypt(test_password)
        decrypted = encryption.decrypt(encrypted)

        if decrypted != test_password:
            all_validation_failures.append(
                f"기본 암호화: 예상 '{test_password}', 실제 '{decrypted}'"
            )
    except Exception as e:
        all_validation_failures.append(f"기본 암호화 오류: {e}")

    # 테스트 2: 빈 문자열 처리
    total_tests += 1
    try:
        empty_encrypted = encryption.encrypt("")
        empty_decrypted = encryption.decrypt(empty_encrypted)

        if empty_decrypted != "":
            all_validation_failures.append(f"빈 문자열: 예상 '', 실제 '{empty_decrypted}'")
    except Exception as e:
        all_validation_failures.append(f"빈 문자열 오류: {e}")

    # 테스트 3: 사용자 정의 키
    total_tests += 1
    try:
        custom_encryption = CredentialEncryption("custom_master_key")
        test_data = "custom_test_data"
        custom_encrypted = custom_encryption.encrypt(test_data)
        custom_decrypted = custom_encryption.decrypt(custom_encrypted)

        if custom_decrypted != test_data:
            all_validation_failures.append(
                f"사용자 정의 키: 예상 '{test_data}', 실제 '{custom_decrypted}'"
            )
    except Exception as e:
        all_validation_failures.append(f"사용자 정의 키 오류: {e}")

    # 테스트 4: 암호화 확인
    total_tests += 1
    try:
        encrypted_text = encryption.encrypt("test")
        is_encrypted_result = encryption.is_encrypted(encrypted_text)
        is_plain_result = encryption.is_encrypted("plain_text")

        if not is_encrypted_result:
            all_validation_failures.append("암호화 텍스트를 암호화된 것으로 인식하지 못함")
        if is_plain_result:
            all_validation_failures.append("평문 텍스트를 암호화된 것으로 잘못 인식")
    except Exception as e:
        all_validation_failures.append(f"암호화 확인 오류: {e}")

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
        print("CredentialEncryption module is validated and ready for use")
        sys.exit(0)
