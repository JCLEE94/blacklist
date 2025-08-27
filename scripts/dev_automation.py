#!/usr/bin/env python3
"""
Development Automation Script
Automates common development tasks with intelligent dependency management
"""
import os
import sys
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Optional


class DevAutomation:
    def __init__(self):
        self.root_path = Path(__file__).parent.parent
        self.scripts_path = self.root_path / "scripts"
        self.venv_path = self.root_path / ".venv"

    def log(self, message: str, level: str = "INFO"):
        """Enhanced logging with colors"""
        colors = {
            "INFO": "\033[94m",
            "SUCCESS": "\033[92m",
            "WARNING": "\033[93m",
            "ERROR": "\033[91m",
            "RESET": "\033[0m",
        }
        print(f"{colors.get(level, '')}{level}: {message}{colors['RESET']}")

    def run_command(
        self, cmd: List[str], check: bool = True
    ) -> subprocess.CompletedProcess:
        """Run command with proper error handling"""
        self.log(f"실행 중: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=check, cwd=self.root_path
            )
            if result.returncode == 0:
                self.log(f"성공: {' '.join(cmd)}", "SUCCESS")
            return result
        except subprocess.CalledProcessError as e:
            self.log(f"명령 실행 실패: {' '.join(cmd)}", "ERROR")
            self.log(f"오류: {e.stderr}", "ERROR")
            if check:
                raise
            return e

    def setup_dependencies(self) -> bool:
        """Smart dependency installation with fallback options"""
        self.log("의존성 설치 중...")

        # Try requirements-docker.txt first (has psycopg2-binary)
        if (self.root_path / "requirements-docker.txt").exists():
            self.log("requirements-docker.txt 사용 중 (Docker 호환)")
            result = self.run_command(
                ["pip", "install", "-r", "requirements-docker.txt"], check=False
            )
            if result.returncode == 0:
                return True

        # Fallback to requirements.txt with substitution
        self.log("requirements.txt를 psycopg2-binary로 수정하여 설치")
        try:
            with open(self.root_path / "requirements.txt", "r") as f:
                requirements = f.read()

            # Substitute psycopg2 with psycopg2-binary
            requirements = requirements.replace("psycopg2==", "psycopg2-binary==")

            # Create temporary requirements file
            temp_req = self.root_path / "requirements-temp.txt"
            with open(temp_req, "w") as f:
                f.write(requirements)

            result = self.run_command(
                ["pip", "install", "-r", str(temp_req)], check=False
            )
            temp_req.unlink()  # Clean up

            return result.returncode == 0

        except Exception as e:
            self.log(f"의존성 설치 실패: {e}", "ERROR")
            return False

    def run_tests(self) -> Dict[str, any]:
        """Run tests with comprehensive reporting"""
        self.log("테스트 실행 중...")

        # Try pytest
        result = self.run_command(
            ["python", "-m", "pytest", "--tb=short", "-v", "--no-header"], check=False
        )

        if result.returncode == 0:
            self.log("모든 테스트 통과!", "SUCCESS")
            return {"status": "success", "output": result.stdout}
        else:
            self.log("테스트 실패 발견", "WARNING")
            return {
                "status": "failed",
                "output": result.stdout,
                "errors": result.stderr,
            }

    def format_code(self) -> bool:
        """Code formatting automation"""
        self.log("코드 포맷팅 중...")

        try:
            # Install formatters if needed
            self.run_command(["pip", "install", "black", "isort"], check=False)

            # Run black
            black_result = self.run_command(
                ["python", "-m", "black", "src/", "tests/", "scripts/"], check=False
            )

            # Run isort
            isort_result = self.run_command(
                ["python", "-m", "isort", "src/", "tests/", "scripts/"], check=False
            )

            success = black_result.returncode == 0 and isort_result.returncode == 0
            if success:
                self.log("코드 포맷팅 완료", "SUCCESS")
            return success

        except Exception as e:
            self.log(f"코드 포맷팅 실패: {e}", "ERROR")
            return False

    def check_git_status(self) -> Dict[str, List[str]]:
        """Check git status and categorize changes"""
        result = self.run_command(["git", "status", "--porcelain"], check=False)

        if result.returncode != 0:
            return {"modified": [], "untracked": [], "error": "Git not available"}

        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        modified = []
        untracked = []

        for line in lines:
            if line.startswith(" M") or line.startswith("M"):
                modified.append(line[3:])
            elif line.startswith("??"):
                untracked.append(line[3:])

        return {"modified": modified, "untracked": untracked}

    def auto_commit_improvements(self) -> bool:
        """Auto-commit development improvements"""
        git_status = self.check_git_status()

        if not git_status["modified"] and not git_status["untracked"]:
            self.log("커밋할 변경사항 없음", "INFO")
            return True

        # Add all changes
        self.run_command(["git", "add", "-A"])

        # Create commit message based on changes
        commit_msg = "feat: 개발 자동화 시스템 개선"
        if git_status["untracked"]:
            commit_msg += f" - {len(git_status['untracked'])}개 새 파일 추가"
        if git_status["modified"]:
            commit_msg += f" - {len(git_status['modified'])}개 파일 수정"

        result = self.run_command(["git", "commit", "-m", commit_msg], check=False)
        return result.returncode == 0

    def full_automation_workflow(self):
        """Complete development automation workflow"""
        self.log("=== 개발 자동화 워크플로우 시작 ===")

        steps = [
            ("의존성 설치", self.setup_dependencies),
            ("코드 포맷팅", self.format_code),
            ("테스트 실행", lambda: self.run_tests()["status"] == "success"),
            ("변경사항 커밋", self.auto_commit_improvements),
        ]

        results = {}
        for step_name, step_func in steps:
            self.log(f"단계: {step_name}")
            try:
                results[step_name] = step_func()
                if results[step_name]:
                    self.log(f"{step_name} 완료", "SUCCESS")
                else:
                    self.log(f"{step_name} 실패", "WARNING")
            except Exception as e:
                self.log(f"{step_name} 오류: {e}", "ERROR")
                results[step_name] = False

        # Summary
        self.log("=== 자동화 워크플로우 결과 ===")
        successful = sum(1 for v in results.values() if v)
        total = len(results)
        self.log(f"성공: {successful}/{total} 단계")

        return results


def main():
    """Main entry point"""
    automation = DevAutomation()

    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "deps":
            automation.setup_dependencies()
        elif command == "test":
            automation.run_tests()
        elif command == "format":
            automation.format_code()
        elif command == "commit":
            automation.auto_commit_improvements()
        elif command == "full":
            automation.full_automation_workflow()
        else:
            print(f"알 수 없는 명령: {command}")
            print("사용법: python dev_automation.py [deps|test|format|commit|full]")
    else:
        automation.full_automation_workflow()


if __name__ == "__main__":
    main()
