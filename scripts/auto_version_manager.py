#!/usr/bin/env python3
"""
자동 버전 관리 시스템
Git 기반 자동 버전 증가 및 관리
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class AutoVersionManager:
    """자동 버전 관리 클래스"""

    def __init__(self, project_root=None):
        self.project_root = (
            Path(project_root) if project_root else Path(__file__).parent.parent
        )
        self.package_json_path = self.project_root / "package.json"

    def get_git_commit_count(self):
        """Git 커밋 수 조회"""
        try:
            result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )
            return int(result.stdout.strip()) if result.returncode == 0 else 0
        except:
            return 0

    def get_current_version(self):
        """현재 버전 조회"""
        try:
            with open(self.package_json_path, "r", encoding="utf-8") as f:
                package_data = json.load(f)
                return package_data.get("version", "1.0.0")
        except:
            return "1.0.0"

    def calculate_auto_version(self):
        """자동 버전 계산"""
        commit_count = self.get_git_commit_count()

        # 기본 버전 1.0 + 커밋 수
        major = 1
        minor = 0
        patch = commit_count

        return f"{major}.{minor}.{patch}"

    def update_version_in_files(self, new_version):
        """모든 파일의 버전 업데이트"""
        files_updated = []

        # 1. package.json 업데이트
        try:
            with open(self.package_json_path, "r", encoding="utf-8") as f:
                package_data = json.load(f)

            old_version = package_data.get("version", "unknown")
            package_data["version"] = new_version

            with open(self.package_json_path, "w", encoding="utf-8") as f:
                json.dump(package_data, f, indent=2, ensure_ascii=False)

            files_updated.append(f"package.json: {old_version} → {new_version}")
        except Exception as e:
            print(f"❌ package.json 업데이트 실패: {e}")

        # 2. README.md 업데이트
        readme_path = self.project_root / "README.md"
        if readme_path.exists():
            try:
                with open(readme_path, "r", encoding="utf-8") as f:
                    readme_content = f.read()

                # 버전 패턴 찾아서 교체
                import re

                patterns = [
                    (
                        r"# 🛡️ Blacklist Management System v\d+\.\d+\.\d+",
                        f"# 🛡️ Blacklist Management System v{new_version}",
                    ),
                    (
                        r"## 🆕 v\d+\.\d+\.\d+ 주요 변경사항",
                        f"## 🆕 v{new_version} 주요 변경사항",
                    ),
                    (
                        r"v\d+\.\d+\.\d+ \(.*?\)",
                        f'v{new_version} ({datetime.now().strftime("%Y-%m-%d")})',
                    ),
                ]

                updated = False
                for pattern, replacement in patterns:
                    if re.search(pattern, readme_content):
                        readme_content = re.sub(pattern, replacement, readme_content)
                        updated = True

                if updated:
                    with open(readme_path, "w", encoding="utf-8") as f:
                        f.write(readme_content)
                    files_updated.append(f"README.md: 버전 패턴 업데이트")

            except Exception as e:
                print(f"⚠️ README.md 업데이트 실패: {e}")

        return files_updated

    def auto_increment_version(self):
        """자동 버전 증가"""
        current_version = self.get_current_version()
        new_version = self.calculate_auto_version()

        print(f"🔄 자동 버전 관리 시스템 실행")
        print(f"📊 Git 커밋 수: {self.get_git_commit_count()}")
        print(f"📋 현재 버전: {current_version}")
        print(f"🆕 계산된 새 버전: {new_version}")

        if current_version != new_version:
            print(f"🔄 버전 업데이트 중...")
            updated_files = self.update_version_in_files(new_version)

            print(f"✅ 버전 업데이트 완료: {current_version} → {new_version}")
            for file_update in updated_files:
                print(f"   📝 {file_update}")

            return new_version, True
        else:
            print(f"✅ 버전이 이미 최신입니다: {current_version}")
            return current_version, False

    def create_version_info(self):
        """버전 정보 파일 생성"""
        version = self.get_current_version()
        version_info = {
            "version": version,
            "build_timestamp": datetime.now().isoformat(),
            "git_commit_count": self.get_git_commit_count(),
            "git_commit_hash": self.get_git_commit_hash(),
            "automated": True,
            "automation_system": "Real Automation System v11.0",
        }

        version_info_path = self.project_root / "version_info.json"
        with open(version_info_path, "w", encoding="utf-8") as f:
            json.dump(version_info, f, indent=2, ensure_ascii=False)

        print(f"📄 버전 정보 파일 생성: {version_info_path}")
        return version_info

    def get_git_commit_hash(self):
        """현재 Git 커밋 해시 조회"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            return "unknown"


def main():
    """메인 실행 함수"""
    print("🚀 Real Automation System v11.0 - 자동 버전 관리")
    print("=" * 60)

    manager = AutoVersionManager()

    # 자동 버전 증가
    new_version, was_updated = manager.auto_increment_version()

    # 버전 정보 파일 생성
    version_info = manager.create_version_info()

    print("=" * 60)
    print(f"✅ 자동 버전 관리 완료")
    print(f"📦 최종 버전: {new_version}")
    print(f"🔄 업데이트됨: {'예' if was_updated else '아니오'}")
    print(f"⏰ 빌드 시간: {version_info['build_timestamp']}")

    return 0 if not was_updated else 1  # 업데이트된 경우 1 반환 (후속 작업 트리거)


if __name__ == "__main__":
    sys.exit(main())
