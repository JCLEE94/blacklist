"""
동적 버전 관리 시스템
Git 커밋 기반 자동 버전 생성 및 관리
"""

import os
import subprocess
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class DynamicVersionManager:
    """동적 버전 관리 클래스"""

    def __init__(self, base_version: str = "1.0"):
        self.base_version = base_version
        self.version_file = Path("version.json")
        self._cached_version = None

    def get_git_info(self) -> Dict[str, str]:
        """Git 정보 수집"""
        git_info = {
            "commit_hash": "unknown",
            "commit_count": "0",
            "branch": "main",
            "commit_date": "",
            "commit_message": "",
        }

        try:
            # 커밋 해시
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd="."
            )
            if result.returncode == 0:
                git_info["commit_hash"] = result.stdout.strip()[:8]

            # 커밋 수 (버전 번호로 사용)
            result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                capture_output=True,
                text=True,
                cwd=".",
            )
            if result.returncode == 0:
                git_info["commit_count"] = result.stdout.strip()

            # 브랜치 명
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                cwd=".",
            )
            if result.returncode == 0:
                git_info["branch"] = result.stdout.strip()

            # 커밋 날짜
            result = subprocess.run(
                ["git", "log", "-1", "--format=%cd", "--date=iso"],
                capture_output=True,
                text=True,
                cwd=".",
            )
            if result.returncode == 0:
                git_info["commit_date"] = result.stdout.strip()

            # 커밋 메시지
            result = subprocess.run(
                ["git", "log", "-1", "--format=%s"],
                capture_output=True,
                text=True,
                cwd=".",
            )
            if result.returncode == 0:
                git_info["commit_message"] = result.stdout.strip()

        except Exception as e:
            logger.warning(f"Git 정보 수집 실패: {e}")

        return git_info

    def generate_version(self) -> str:
        """동적 버전 생성"""
        git_info = self.get_git_info()
        commit_count = git_info.get("commit_count", "0")

        # 기본 버전.커밋수 형식
        version = f"{self.base_version}.{commit_count}"

        # 개발 브랜치의 경우 브랜치명 추가
        branch = git_info.get("branch", "main")
        if branch != "main":
            version += f"-{branch}"

        # 커밋 해시 추가
        commit_hash = git_info.get("commit_hash", "unknown")
        if commit_hash != "unknown":
            version += f".{commit_hash}"

        return version

    def get_version_info(self) -> Dict:
        """완전한 버전 정보 반환"""
        if self._cached_version is None:
            git_info = self.get_git_info()
            version = self.generate_version()

            # GitHub Actions 환경변수에서 빌드 정보 수집
            build_info = {
                "build_number": os.getenv("GITHUB_RUN_NUMBER", "0"),
                "build_id": os.getenv("GITHUB_RUN_ID", "local"),
                "workflow": os.getenv("GITHUB_WORKFLOW", "Local Build"),
                "actor": os.getenv("GITHUB_ACTOR", "developer"),
                "repository": os.getenv("GITHUB_REPOSITORY", "local/blacklist"),
            }

            self._cached_version = {
                "version": version,
                "base_version": self.base_version,
                "build_timestamp": datetime.now().isoformat(),
                "git": git_info,
                "build": build_info,
                "environment": os.getenv("FLASK_ENV", "development"),
            }

        return self._cached_version

    def save_version_file(self) -> bool:
        """버전 정보를 파일로 저장"""
        try:
            version_info = self.get_version_info()
            with open(self.version_file, "w", encoding="utf-8") as f:
                json.dump(version_info, f, indent=2, ensure_ascii=False)

            logger.info(f"버전 정보 저장됨: {version_info['version']}")
            return True

        except Exception as e:
            logger.error(f"버전 파일 저장 실패: {e}")
            return False

    def load_version_file(self) -> Optional[Dict]:
        """저장된 버전 정보 로드"""
        try:
            if self.version_file.exists():
                with open(self.version_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"버전 파일 로드 실패: {e}")
        return None

    def get_current_version(self) -> str:
        """현재 버전 문자열 반환"""
        # 먼저 파일에서 로드 시도
        version_data = self.load_version_file()
        if version_data:
            return version_data.get("version", self.generate_version())

        # 없으면 동적 생성
        return self.generate_version()

    def is_production_build(self) -> bool:
        """프로덕션 빌드인지 확인"""
        return (
            os.getenv("FLASK_ENV") == "production"
            or os.getenv("GITHUB_ACTIONS") == "true"
        )

    def get_deployment_info(self) -> Dict:
        """배포 관련 정보"""
        version_info = self.get_version_info()

        return {
            "version": version_info["version"],
            "deployed_at": version_info["build_timestamp"],
            "git_hash": version_info["git"]["commit_hash"],
            "build_number": version_info["build"]["build_number"],
            "environment": version_info["environment"],
            "is_production": self.is_production_build(),
        }


# 전역 버전 관리자 인스턴스
version_manager = DynamicVersionManager()


def get_version() -> str:
    """간단한 버전 조회 함수"""
    return version_manager.get_current_version()


def get_version_info() -> Dict:
    """완전한 버전 정보 조회 함수"""
    return version_manager.get_version_info()


def initialize_version() -> bool:
    """애플리케이션 시작시 버전 초기화"""
    try:
        version_manager.save_version_file()
        logger.info(f"버전 관리 초기화 완료: {get_version()}")
        return True
    except Exception as e:
        logger.error(f"버전 초기화 실패: {e}")
        return False


if __name__ == "__main__":
    # 테스트 실행
    print("🔧 동적 버전 관리 시스템 테스트")
    print("=" * 40)

    vm = DynamicVersionManager()
    version_info = vm.get_version_info()

    print(f"버전: {version_info['version']}")
    print(f"Git 해시: {version_info['git']['commit_hash']}")
    print(f"커밋 수: {version_info['git']['commit_count']}")
    print(f"브랜치: {version_info['git']['branch']}")
    print(f"빌드 번호: {version_info['build']['build_number']}")
    print(f"환경: {version_info['environment']}")

    # 버전 파일 저장 테스트
    success = vm.save_version_file()
    print(f"버전 파일 저장: {'성공' if success else '실패'}")
