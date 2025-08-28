#!/usr/bin/env python3
"""
자격증명 설정 자동화 스크립트

REGTECH, SECUDIUM 등 외부 서비스 자격증명을 안전하게 설정합니다.
대화식 및 배치 모드를 지원합니다.
"""

import os
import sys
import getpass
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.core.security.credential_manager import (
        CredentialManager,
        get_credential_manager,
    )
except ImportError as e:
    print(f"❌ 모듈 임포트 실패: {e}")
    print("src/core/security/credential_manager.py 파일이 존재하는지 확인하세요.")
    sys.exit(1)


class CredentialSetup:
    """자격증명 설정 클래스"""

    def __init__(self):
        self.manager = get_credential_manager()
        self.services = {
            "regtech": {
                "name": "REGTECH",
                "description": "REGTECH 위협 정보 서비스",
                "username_prompt": "REGTECH 사용자명 (이메일): ",
                "password_prompt": "REGTECH 패스워드: ",
                "env_vars": ["REGTECH_USERNAME", "REGTECH_PASSWORD"],
            },
            "secudium": {
                "name": "SECUDIUM",
                "description": "SECUDIUM 보안 정보 서비스",
                "username_prompt": "SECUDIUM 사용자명: ",
                "password_prompt": "SECUDIUM 패스워드: ",
                "env_vars": ["SECUDIUM_USERNAME", "SECUDIUM_PASSWORD"],
            },
            "api": {
                "name": "API",
                "description": "시스템 API 접근",
                "username_prompt": "API 사용자명: ",
                "password_prompt": "API 키/패스워드: ",
                "env_vars": ["API_USERNAME", "API_PASSWORD"],
            },
        }

    def interactive_setup(self):
        """대화식 자격증명 설정"""
        print("🔐 블랙리스트 시스템 자격증명 설정")
        print("=" * 50)

        # 현재 상태 확인
        self.show_current_status()

        print("\n어떤 서비스의 자격증명을 설정하시겠습니까?")
        for i, (service_id, info) in enumerate(self.services.items(), 1):
            status = "✅ 설정됨" if self.manager.get_credential(service_id) else "❌ 미설정"
            print(f"{i}. {info['name']} - {info['description']} ({status})")

        print("0. 모든 서비스 설정")
        print("q. 종료")

        choice = input("\n선택 (숫자 또는 q): ").strip()

        if choice.lower() == "q":
            print("설정을 종료합니다.")
            return

        try:
            if choice == "0":
                # 모든 서비스 설정
                for service_id in self.services.keys():
                    self.setup_service(service_id)
            else:
                choice_idx = int(choice) - 1
                service_id = list(self.services.keys())[choice_idx]
                self.setup_service(service_id)
        except (ValueError, IndexError):
            print("❌ 잘못된 선택입니다.")
            return

        # 설정 저장
        print("\n💾 자격증명을 저장하는 중...")
        try:
            self.manager.save_credentials()
            print("✅ 자격증명이 성공적으로 저장되었습니다.")
        except Exception as e:
            print(f"❌ 저장 실패: {e}")

        # 최종 상태 확인
        print("\n📊 최종 설정 상태:")
        self.show_current_status()

    def setup_service(self, service_id: str):
        """특정 서비스 자격증명 설정"""
        service_info = self.services[service_id]

        print(f"\n🔧 {service_info['name']} 자격증명 설정")
        print("-" * 30)

        # 기존 자격증명 확인
        existing = self.manager.get_credential(service_id)
        if existing:
            print(f"기존 사용자명: {existing.username}")
            update = input("기존 자격증명을 업데이트하시겠습니까? (y/N): ").strip().lower()
            if update != "y":
                return

        # 사용자명 입력
        username = input(service_info["username_prompt"]).strip()
        if not username:
            print("❌ 사용자명이 비어있습니다. 건너뜁니다.")
            return

        # 패스워드 입력 (보안)
        password = getpass.getpass(service_info["password_prompt"])
        if not password:
            print("❌ 패스워드가 비어있습니다. 건너뜁니다.")
            return

        # 만료일 설정 (선택사항)
        expire_choice = input("자격증명 만료일을 설정하시겠습니까? (y/N): ").strip().lower()
        expires_at = None

        if expire_choice == "y":
            try:
                days = int(input("몇 일 후 만료? (기본값: 90일): ") or "90")
                expires_at = datetime.now() + timedelta(days=days)
                print(f"만료일: {expires_at.strftime('%Y-%m-%d')}")
            except ValueError:
                print("❌ 잘못된 일수입니다. 만료일 설정을 건너뜁니다.")

        # 자격증명 추가/업데이트
        if existing:
            success = self.manager.update_credential(
                service=service_id,
                username=username,
                password=password,
                expires_at=expires_at,
            )
        else:
            success = self.manager.add_credential(
                service=service_id,
                username=username,
                password=password,
                expires_at=expires_at,
            )

        if success:
            print(f"✅ {service_info['name']} 자격증명이 설정되었습니다.")

            # 검증
            validation = self.manager.validate_credential(service_id)
            if validation["valid"]:
                print("✅ 자격증명 검증 성공")
            else:
                print(f"⚠️ 검증 경고: {validation.get('error', '알 수 없는 오류')}")
        else:
            print(f"❌ {service_info['name']} 자격증명 설정 실패")

    def batch_setup(self, config_file: str):
        """배치 모드 자격증명 설정"""
        config_path = Path(config_file)
        if not config_path.exists():
            print(f"❌ 설정 파일이 없습니다: {config_file}")
            return False

        try:
            import json

            with open(config_path) as f:
                config = json.load(f)

            for service_id, cred_info in config.items():
                if service_id not in self.services:
                    print(f"⚠️ 알 수 없는 서비스: {service_id}")
                    continue

                username = cred_info.get("username")
                password = cred_info.get("password")

                if not username or not password:
                    print(f"❌ {service_id}: 사용자명 또는 패스워드가 없습니다.")
                    continue

                # 만료일 처리
                expires_at = None
                if "expires_at" in cred_info:
                    try:
                        expires_at = datetime.fromisoformat(cred_info["expires_at"])
                    except ValueError:
                        print(f"⚠️ {service_id}: 잘못된 만료일 형식")

                # 자격증명 추가
                success = self.manager.add_credential(
                    service=service_id,
                    username=username,
                    password=password,
                    expires_at=expires_at,
                    additional_data={"source": "batch_config"},
                )

                if success:
                    print(f"✅ {service_id} 자격증명 설정 완료")
                else:
                    print(f"❌ {service_id} 자격증명 설정 실패")

            # 설정 저장
            self.manager.save_credentials()
            print("✅ 모든 자격증명이 저장되었습니다.")
            return True

        except Exception as e:
            print(f"❌ 배치 설정 실패: {e}")
            return False

    def show_current_status(self):
        """현재 자격증명 상태 표시"""
        print("\n📊 현재 자격증명 상태:")

        for service_id, info in self.services.items():
            credential = self.manager.get_credential(service_id)

            if credential:
                status = "✅ 설정됨"
                details = f"사용자: {credential.username}"

                if credential.is_expired():
                    status += " (❌ 만료됨)"
                elif credential.expires_soon():
                    status += " (⚠️ 곧 만료)"

                if credential.last_used:
                    details += (
                        f", 마지막 사용: {credential.last_used.strftime('%Y-%m-%d %H:%M')}"
                    )

                print(f"  {info['name']}: {status} - {details}")
            else:
                print(f"  {info['name']}: ❌ 미설정")

    def validate_all(self):
        """모든 자격증명 검증"""
        print("\n🔍 자격증명 검증 중...")

        all_valid = True
        for service_id in self.services.keys():
            validation = self.manager.validate_credential(service_id)

            if validation["valid"]:
                print(f"✅ {service_id}: 유효함")
            else:
                print(f"❌ {service_id}: {validation.get('error', '검증 실패')}")
                all_valid = False

            if "warning" in validation:
                print(f"⚠️ {service_id}: {validation['warning']}")

        return all_valid

    def export_env_template(self, output_file: str = ".env.credentials"):
        """환경변수 템플릿 생성"""
        print(f"\n📄 환경변수 템플릿 생성: {output_file}")

        template_lines = [
            "# 블랙리스트 시스템 자격증명 환경변수",
            "# 이 파일을 복사하여 실제 값으로 수정하세요",
            "# 주의: 이 파일을 Git에 커밋하지 마세요!",
            "",
        ]

        for service_id, info in self.services.items():
            template_lines.append(f"# {info['description']}")
            for env_var in info["env_vars"]:
                # 기존 자격증명이 있으면 마스킹해서 표시
                credential = self.manager.get_credential(service_id)
                if credential and env_var.endswith("_USERNAME"):
                    value = credential.username
                elif credential and env_var.endswith("_PASSWORD"):
                    value = "***MASKED***"
                else:
                    value = "your_value_here"

                template_lines.append(f"{env_var}={value}")

            template_lines.append("")

        try:
            with open(output_file, "w") as f:
                f.write("\n".join(template_lines))

            print(f"✅ 템플릿이 생성되었습니다: {output_file}")
            return True

        except Exception as e:
            print(f"❌ 템플릿 생성 실패: {e}")
            return False

    def create_config_template(self, output_file: str = "credentials.template.json"):
        """설정 파일 템플릿 생성"""
        template = {}

        for service_id, info in self.services.items():
            template[service_id] = {
                "username": "your_username_here",
                "password": "your_password_here",
                "expires_at": None,  # "2024-12-31T23:59:59" 형식
                "additional_data": {"description": info["description"]},
            }

        try:
            import json

            with open(output_file, "w") as f:
                json.dump(template, f, indent=2, ensure_ascii=False)

            print(f"✅ 설정 템플릿이 생성되었습니다: {output_file}")
            return True

        except Exception as e:
            print(f"❌ 템플릿 생성 실패: {e}")
            return False


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="블랙리스트 시스템 자격증명 설정 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python setup-credentials.py                    # 대화식 설정
  python setup-credentials.py --batch config.json   # 배치 설정
  python setup-credentials.py --validate            # 검증만 수행
  python setup-credentials.py --export-template     # 템플릿 생성
        """,
    )

    parser.add_argument("--batch", metavar="CONFIG_FILE", help="배치 모드로 설정 파일에서 자격증명 로드")
    parser.add_argument("--validate", action="store_true", help="기존 자격증명 검증만 수행")
    parser.add_argument("--status", action="store_true", help="현재 상태만 표시")
    parser.add_argument("--export-template", action="store_true", help="환경변수 템플릿 파일 생성")
    parser.add_argument("--create-template", action="store_true", help="설정 파일 템플릿 생성")

    args = parser.parse_args()

    try:
        setup = CredentialSetup()

        if args.status:
            setup.show_current_status()

        elif args.validate:
            valid = setup.validate_all()
            sys.exit(0 if valid else 1)

        elif args.export_template:
            success = setup.export_env_template()
            sys.exit(0 if success else 1)

        elif args.create_template:
            success = setup.create_config_template()
            sys.exit(0 if success else 1)

        elif args.batch:
            success = setup.batch_setup(args.batch)
            sys.exit(0 if success else 1)

        else:
            # 대화식 설정
            setup.interactive_setup()

    except KeyboardInterrupt:
        print("\n\n설정이 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
