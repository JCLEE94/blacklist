#!/usr/bin/env python3
"""
프로젝트 정리 자동화 스크립트
- 권한 문제 있는 디렉토리 처리
- 불필요한 파일 정리
- .gitignore 최적화
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple


class ProjectCleaner:
    """프로젝트 정리 자동화 클래스"""

    def __init__(self, project_root=None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.issues_found = []
        self.fixes_applied = []

    def clean_database_directories(self):
        """데이터베이스 관련 권한 문제 디렉토리 정리"""
        print("🗄️ 데이터베이스 디렉토리 권한 문제 해결 중...")

        problematic_dirs = [
            "test-postgresql-data/pgdata",
            "data/postgresql/pgdata",
            "config/redis-data/appendonlydir",
            "config/postgresql-data/pgdata",
            "docker/redis-data/appendonlydir",
        ]

        for dir_path in problematic_dirs:
            full_path = self.project_root / dir_path
            if full_path.exists():
                try:
                    # 권한 수정 시도
                    subprocess.run(
                        f"sudo chmod -R 755 {full_path}",
                        shell=True,
                        capture_output=True,
                    )
                    print(f"  ✅ {dir_path} 권한 수정 완료")
                    self.fixes_applied.append(f"Fixed permissions for {dir_path}")
                except:
                    # 권한 수정이 안 되면 .gitignore에 추가
                    self.add_to_gitignore(str(dir_path))
                    print(f"  🚫 {dir_path} .gitignore에 추가")
                    self.fixes_applied.append(f"Added {dir_path} to .gitignore")

    def add_to_gitignore(self, pattern: str):
        """패턴을 .gitignore에 추가"""
        gitignore_path = self.project_root / ".gitignore"

        # 기존 .gitignore 읽기
        existing_patterns = set()
        if gitignore_path.exists():
            with open(gitignore_path, "r", encoding="utf-8") as f:
                existing_patterns = set(line.strip() for line in f if line.strip())

        # 새 패턴 추가
        if pattern not in existing_patterns:
            with open(gitignore_path, "a", encoding="utf-8") as f:
                f.write(f"\n# Auto-added by project cleaner\n{pattern}\n")

    def cleanup_temporary_files(self):
        """임시 파일 및 캐시 파일 정리"""
        print("🧹 임시 파일 및 캐시 정리 중...")

        cleanup_patterns = [
            "**/__pycache__",
            "**/*.pyc",
            "**/*.pyo",
            "**/.pytest_cache",
            "**/node_modules",
            "**/.coverage",
            "**/htmlcov*",
            "**/*.log",
            "**/.DS_Store",
        ]

        cleaned_count = 0
        for pattern in cleanup_patterns:
            for path in self.project_root.glob(pattern):
                if path.is_file():
                    try:
                        path.unlink()
                        cleaned_count += 1
                    except:
                        pass
                elif path.is_dir():
                    try:
                        shutil.rmtree(path)
                        cleaned_count += 1
                    except:
                        pass

        if cleaned_count > 0:
            print(f"  ✅ {cleaned_count}개 임시 파일/디렉토리 정리 완료")
            self.fixes_applied.append(f"Cleaned {cleaned_count} temporary files")
        else:
            print("  ✅ 정리할 임시 파일 없음")

    def optimize_gitignore(self):
        """gitignore 파일 최적화"""
        print("📝 .gitignore 최적화 중...")

        essential_patterns = [
            "# Python",
            "__pycache__/",
            "*.pyc",
            "*.pyo",
            "*.egg-info/",
            ".pytest_cache/",
            ".coverage",
            "htmlcov*/",
            "",
            "# Database data",
            "*.db",
            "pgdata/",
            "appendonlydir/",
            "",
            "# Environment",
            ".env",
            ".env.local",
            ".venv/",
            "venv/",
            "",
            "# IDE",
            ".vscode/",
            ".idea/",
            "*.swp",
            "*.swo",
            "",
            "# OS",
            ".DS_Store",
            "Thumbs.db",
            "",
            "# Logs",
            "*.log",
            "logs/*.log",
        ]

        gitignore_path = self.project_root / ".gitignore"

        # 기존 내용 읽기
        existing_content = ""
        if gitignore_path.exists():
            with open(gitignore_path, "r", encoding="utf-8") as f:
                existing_content = f.read()

        # 필수 패턴들이 없으면 추가
        missing_patterns = []
        for pattern in essential_patterns:
            if pattern.strip() and pattern not in existing_content:
                missing_patterns.append(pattern)

        if missing_patterns:
            with open(gitignore_path, "a", encoding="utf-8") as f:
                f.write(f"\n# Auto-optimized by project cleaner\n")
                for pattern in missing_patterns:
                    f.write(f"{pattern}\n")

            print(f"  ✅ .gitignore에 {len(missing_patterns)}개 패턴 추가")
            self.fixes_applied.append(
                f"Added {len(missing_patterns)} patterns to .gitignore"
            )
        else:
            print("  ✅ .gitignore 이미 최적화됨")

    def check_large_files(self) -> List[Tuple[str, int]]:
        """큰 파일들 찾기 (10MB 이상)"""
        print("📏 큰 파일 검사 중...")

        large_files = []
        for file_path in self.project_root.rglob("*"):
            if file_path.is_file():
                try:
                    size = file_path.stat().st_size
                    if size > 10 * 1024 * 1024:  # 10MB
                        large_files.append(
                            (str(file_path.relative_to(self.project_root)), size)
                        )
                except:
                    pass

        if large_files:
            print(f"  ⚠️ {len(large_files)}개 큰 파일 발견:")
            for file_path, size in large_files[:5]:  # 상위 5개만 표시
                size_mb = size / (1024 * 1024)
                print(f"    - {file_path}: {size_mb:.1f}MB")
        else:
            print("  ✅ 큰 파일 없음")

        return large_files

    def optimize_package_json_scripts(self):
        """package.json 스크립트 최적화"""
        print("📦 package.json 스크립트 최적화 중...")

        package_json_path = self.project_root / "package.json"
        if not package_json_path.exists():
            print("  ⚠️ package.json 없음")
            return

        import json

        with open(package_json_path, "r", encoding="utf-8") as f:
            package_data = json.load(f)

        if "scripts" not in package_data:
            print("  ✅ scripts 섹션 없음")
            return

        scripts = package_data["scripts"]
        original_count = len(scripts)

        # 핵심 스크립트들 정의
        essential_scripts = {
            "start": "python scripts/run_with_credentials.py",
            "test": "pytest tests/ -v",
            "build": "docker build -t blacklist:latest .",
            "lint": "python -m flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics",
            "format": "black src/ tests/ && isort src/ tests/",
            "clean": "find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true",
            "version": "python scripts/auto_version_manager.py",
        }

        # 중복되거나 불필요한 스크립트 정리
        optimized_scripts = {}
        for key, value in scripts.items():
            if key in essential_scripts:
                optimized_scripts[key] = essential_scripts[key]
            elif key in ["dev", "deploy", "docker:build", "docker:push", "docker:run"]:
                # 유용한 스크립트들은 유지
                optimized_scripts[key] = value

        # 필수 스크립트 추가
        for key, value in essential_scripts.items():
            if key not in optimized_scripts:
                optimized_scripts[key] = value

        if len(optimized_scripts) != original_count:
            package_data["scripts"] = optimized_scripts
            with open(package_json_path, "w", encoding="utf-8") as f:
                json.dump(package_data, f, indent=2, ensure_ascii=False)

            print(f"  ✅ 스크립트 최적화: {original_count}개 → {len(optimized_scripts)}개")
            self.fixes_applied.append(
                f"Optimized package.json scripts: {original_count} → {len(optimized_scripts)}"
            )
        else:
            print("  ✅ 스크립트 이미 최적화됨")

    def run_all_cleanups(self):
        """모든 정리 작업 실행"""
        print("🚀 프로젝트 정리 자동화 시작")
        print("=" * 50)

        self.clean_database_directories()
        self.cleanup_temporary_files()
        self.optimize_gitignore()
        large_files = self.check_large_files()
        self.optimize_package_json_scripts()

        print("=" * 50)
        print("✅ 프로젝트 정리 완료")
        print(f"📊 적용된 수정사항: {len(self.fixes_applied)}개")

        for fix in self.fixes_applied:
            print(f"  - {fix}")

        if large_files:
            print(f"\n⚠️ 주의: {len(large_files)}개 큰 파일 발견됨")

        return {"fixes_applied": self.fixes_applied, "large_files": large_files}


if __name__ == "__main__":
    cleaner = ProjectCleaner()
    result = cleaner.run_all_cleanups()
