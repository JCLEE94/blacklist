#!/usr/bin/env python3
"""
자격증명을 로드하여 애플리케이션 실행
환경 변수를 자동으로 설정하고 애플리케이션 시작
"""
import os
import sys
import subprocess
from pathlib import Path
from getpass import getpass

# 상위 디렉토리를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.setup_credentials import CredentialManager


def main():
    """메인 함수"""
    # 자격증명 관리자 초기화
    manager = CredentialManager()

    # 자격증명 파일 확인
    if not manager.encrypted_file.exists():
        print("⚠️  자격증명이 설정되지 않았습니다.")
        print("먼저 다음 명령을 실행하세요:")
        print("  python scripts/setup_credentials.py")
        sys.exit(1)

    # 자격증명 로드
    print("🔐 자격증명 로드 중...")
    credentials = manager.load_credentials()

    if not credentials:
        print("❌ 자격증명 로드 실패")
        sys.exit(1)

    # 환경 변수 설정
    env_vars = manager.get_environment_variables(credentials)
    current_env = os.environ.copy()
    current_env.update(env_vars)

    print(f"✅ {len(env_vars)}개의 환경 변수 설정됨")

    # 애플리케이션 실행 명령 결정
    if len(sys.argv) > 1:
        # 사용자가 지정한 명령 실행
        command = sys.argv[1:]
    else:
        # 기본 명령: Flask 애플리케이션 실행
        command = ["python", "main.py"]

    print(f"🚀 실행 중: {' '.join(command)}")
    print("-" * 60)

    # 애플리케이션 실행
    try:
        result = subprocess.run(command, env=current_env)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n⏹️  애플리케이션 중지됨")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 실행 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
