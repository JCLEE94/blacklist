#!/usr/bin/env python3
"""
자격증명 설정 스크립트
환경 변수 대신 사용자 입력을 받아 안전하게 저장
"""
import json
import os
import sys
from pathlib import Path
from getpass import getpass
from typing import Dict, Any
import hashlib
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2


class CredentialManager:
    """자격증명 관리 클래스"""

    def __init__(self):
        self.config_dir = Path.home() / ".blacklist"
        self.config_file = self.config_dir / "credentials.json"
        self.encrypted_file = self.config_dir / "credentials.enc"
        self.config_dir.mkdir(exist_ok=True)

    def get_encryption_key(self, password: str) -> bytes:
        """비밀번호로부터 암호화 키 생성"""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"blacklist_salt_2024",  # 실제로는 랜덤 salt 사용 권장
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def encrypt_credentials(self, credentials: Dict[str, Any], password: str) -> None:
        """자격증명 암호화하여 저장"""
        key = self.get_encryption_key(password)
        f = Fernet(key)

        json_data = json.dumps(credentials)
        encrypted_data = f.encrypt(json_data.encode())

        with open(self.encrypted_file, "wb") as file:
            file.write(encrypted_data)

        print(f"✅ 자격증명이 암호화되어 저장되었습니다: {self.encrypted_file}")

    def decrypt_credentials(self, password: str) -> Dict[str, Any]:
        """암호화된 자격증명 복호화"""
        if not self.encrypted_file.exists():
            return {}

        key = self.get_encryption_key(password)
        f = Fernet(key)

        with open(self.encrypted_file, "rb") as file:
            encrypted_data = file.read()

        try:
            decrypted_data = f.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            print(f"❌ 복호화 실패: {e}")
            return {}

    def setup_credentials(self) -> None:
        """대화식으로 자격증명 설정"""
        print("=" * 60)
        print("🔐 Blacklist 자격증명 설정")
        print("=" * 60)
        print("\n환경 변수 대신 안전하게 자격증명을 저장합니다.\n")

        credentials = {}

        # 필수 자격증명
        print("📋 필수 설정")
        print("-" * 40)

        # Database (PostgreSQL only)
        credentials["database"] = {
            "type": "postgresql",
            "host": input("PostgreSQL 호스트 [localhost]: ").strip() or "localhost",
            "port": input("PostgreSQL 포트 [5432]: ").strip() or "5432",
            "name": input("Database 이름 [blacklist]: ").strip() or "blacklist",
            "user": input("Database 사용자 [postgres]: ").strip() or "postgres",
            "password": getpass("Database 비밀번호: "),
        }

        # Redis (선택)
        print("\n📋 Redis 설정 (선택사항, Enter로 건너뛰기)")
        print("-" * 40)
        use_redis = input("Redis 사용? (y/N): ").strip().lower() == "y"

        if use_redis:
            credentials["redis"] = {
                "host": input("Redis 호스트 [localhost]: ").strip() or "localhost",
                "port": input("Redis 포트 [6379]: ").strip() or "6379",
                "password": getpass("Redis 비밀번호 (없으면 Enter): ").strip() or None,
                "db": input("Redis DB 번호 [0]: ").strip() or "0",
            }

        # Collection APIs
        print("\n📋 수집 API 자격증명 (선택사항)")
        print("-" * 40)

        use_regtech = input("REGTECH API 사용? (y/N): ").strip().lower() == "y"
        if use_regtech:
            credentials["regtech"] = {
                "username": input("REGTECH 사용자명: ").strip(),
                "password": getpass("REGTECH 비밀번호: "),
            }

        use_secudium = input("SECUDIUM API 사용? (y/N): ").strip().lower() == "y"
        if use_secudium:
            credentials["secudium"] = {
                "username": input("SECUDIUM 사용자명: ").strip(),
                "password": getpass("SECUDIUM 비밀번호: "),
            }

        # Security
        print("\n📋 보안 설정")
        print("-" * 40)

        credentials["security"] = {
            "secret_key": base64.b64encode(os.urandom(32)).decode(),
            "jwt_secret_key": base64.b64encode(os.urandom(32)).decode(),
            "admin_username": input("관리자 사용자명 [admin]: ").strip() or "admin",
            "admin_password": getpass("관리자 비밀번호: "),
        }

        # 마스터 비밀번호로 암호화
        print("\n🔒 마스터 비밀번호 설정")
        print("-" * 40)
        print("자격증명을 암호화할 마스터 비밀번호를 설정합니다.")

        while True:
            master_password = getpass("마스터 비밀번호: ")
            confirm_password = getpass("마스터 비밀번호 확인: ")

            if master_password == confirm_password:
                break
            print("❌ 비밀번호가 일치하지 않습니다. 다시 시도하세요.")

        # 저장
        self.encrypt_credentials(credentials, master_password)

        # 사용 방법 안내
        print("\n" + "=" * 60)
        print("✅ 설정 완료!")
        print("=" * 60)
        print("\n📖 사용 방법:")
        print("1. 애플리케이션 시작 시 마스터 비밀번호 입력")
        print("2. 자격증명이 자동으로 로드됨")
        print(f"3. 설정 파일 위치: {self.encrypted_file}")
        print("\n⚠️  주의사항:")
        print("- 마스터 비밀번호를 잊으면 복구 불가능")
        print("- credentials.enc 파일을 안전하게 백업하세요")

    def load_credentials(self) -> Dict[str, Any]:
        """저장된 자격증명 로드"""
        if not self.encrypted_file.exists():
            print(
                "⚠️  자격증명 파일이 없습니다. setup_credentials.py를 먼저 실행하세요."
            )
            return {}

        password = getpass("🔑 마스터 비밀번호: ")
        return self.decrypt_credentials(password)

    def get_environment_variables(self, credentials: Dict[str, Any]) -> Dict[str, str]:
        """자격증명을 환경 변수 형식으로 변환"""
        env_vars = {}

        # Database (PostgreSQL only)
        db = credentials["database"]
        env_vars["DATABASE_URL"] = (
            f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}"
        )

        # Redis
        if "redis" in credentials:
            redis = credentials["redis"]
            if redis.get("password"):
                env_vars["REDIS_URL"] = (
                    f"redis://:{redis['password']}@{redis['host']}:{redis['port']}/{redis['db']}"
                )
            else:
                env_vars["REDIS_URL"] = (
                    f"redis://{redis['host']}:{redis['port']}/{redis['db']}"
                )

        # Collection APIs
        if "regtech" in credentials:
            env_vars["REGTECH_USERNAME"] = credentials["regtech"]["username"]
            env_vars["REGTECH_PASSWORD"] = credentials["regtech"]["password"]

        if "secudium" in credentials:
            env_vars["SECUDIUM_USERNAME"] = credentials["secudium"]["username"]
            env_vars["SECUDIUM_PASSWORD"] = credentials["secudium"]["password"]

        # Security
        if "security" in credentials:
            sec = credentials["security"]
            env_vars["SECRET_KEY"] = sec["secret_key"]
            env_vars["JWT_SECRET_KEY"] = sec["jwt_secret_key"]
            env_vars["ADMIN_USERNAME"] = sec["admin_username"]
            env_vars["ADMIN_PASSWORD"] = sec["admin_password"]

        return env_vars


def main():
    """메인 함수"""
    manager = CredentialManager()

    if len(sys.argv) > 1:
        if sys.argv[1] == "load":
            # 자격증명 로드 테스트
            credentials = manager.load_credentials()
            if credentials:
                print("✅ 자격증명 로드 성공")
                env_vars = manager.get_environment_variables(credentials)
                print(f"📋 {len(env_vars)}개의 환경 변수 준비됨")
        elif sys.argv[1] == "export":
            # 환경 변수 export 명령 생성
            credentials = manager.load_credentials()
            if credentials:
                env_vars = manager.get_environment_variables(credentials)
                for key, value in env_vars.items():
                    print(f"export {key}='{value}'")
    else:
        # 대화식 설정
        manager.setup_credentials()


if __name__ == "__main__":
    try:
        # cryptography 패키지 확인
        import cryptography
    except ImportError:
        print("❌ cryptography 패키지가 필요합니다.")
        print("설치: pip install cryptography")
        sys.exit(1)

    main()
