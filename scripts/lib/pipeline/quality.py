#!/usr/bin/env python3
"""
Code Quality Pipeline Stage - Code quality checks and validation
"""

import glob
import logging
import subprocess
from pathlib import Path

from .base import PipelineStage
from .config import PipelineConfig

logger = logging.getLogger(__name__)


class CodeQualityStage(PipelineStage):
    """Code quality check stage"""

    def __init__(self, config: PipelineConfig):
        super().__init__("code-quality", config)

    def run(self) -> bool:
        """Execute code quality checks"""
        checks = [
            ("Python Syntax", self._check_python_syntax),
            ("Code Style", self._check_code_style),
            ("Security Scan", self._check_security),
            ("Dependencies", self._check_dependencies),
        ]

        all_passed = True
        for check_name, check_func in checks:
            logger.info(f"Running {check_name}...")
            if not check_func():
                all_passed = False
                self.errors.append(f"{check_name} failed")

        return all_passed

    def _check_python_syntax(self) -> bool:
        """Python syntax check"""
        try:
            src_path = (
                Path(self.config.project_root)
                if hasattr(self.config, "project_root")
                else Path("src")
            )
            python_files = glob.glob(str(src_path / "**" / "*.py"), recursive=True)

            if not python_files:
                logger.warning("No Python files found in src/")
                return True  # No files = success

            # Check each file individually
            for py_file in python_files:
                result = subprocess.run(
                    ["python3", "-m", "py_compile", py_file],
                    capture_output=True,
                    timeout=30,  # 30 second timeout
                )
                if result.returncode != 0:
                    self.errors.append(
                        f"Syntax error in {py_file}: {result.stderr.decode()}"
                    )
                    return False

            return True
        except subprocess.TimeoutExpired:
            self.errors.append("Python syntax check timed out")
            return False
        except Exception as e:
            self.errors.append(f"Python syntax check failed: {e}")
            return False

    def _check_code_style(self) -> bool:
        """Code style check"""
        if not Path("src").exists():
            return True

        try:
            cmd = ["python3", "-m", "flake8", "src/", "--extend-ignore=E501,W503"]
            result = subprocess.run(cmd, capture_output=True, timeout=60)

            if result.returncode != 0 and self.config.verbose:
                logger.warning(f"Style issues found:\n{result.stdout.decode()}")

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            self.errors.append("Code style check timed out")
            return False
        except Exception as e:
            self.errors.append(f"Code style check failed: {e}")
            return False

    def _check_security(self) -> bool:
        """Security vulnerability check"""
        try:
            # Extended hardcoded secret patterns
            secret_patterns = [
                r'(password|passwd|pwd)\s*=\s*["\'][^"\']+["\']',
                r'(secret|token|key|api_key|apikey)\s*=\s*["\'][^"\']+["\']',
                r'(aws_access_key|aws_secret|aws_token)\s*=\s*["\'][^"\']+["\']',
                r'(database_url|db_url|connection_string)\s*=\s*["\'][^"\']+["\']',
                r'(private_key|priv_key|pem|cert)\s*=\s*["\'][^"\']+["\']',
                r"Bearer\s+[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.?[A-Za-z0-9\-_.+/=]*",
                r"Basic\s+[A-Za-z0-9+/=]+",
            ]

            # Replace grep command with Python
            cmd = [
                "grep",
                "-r",
                "-E",
                "|".join(f"({pattern})" for pattern in secret_patterns),
                "--include=*.py",
                "src/",
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=60)  # 60s timeout

            # grep returns returncode 1 when no matches found
            if result.returncode == 0 and result.stdout:
                logger.warning(
                    f"Potential hardcoded secrets found:\n{result.stdout.decode()}"
                )
                return False

            return True

        except subprocess.TimeoutExpired:
            self.errors.append("Security scan timed out")
            return False
        except FileNotFoundError:
            logger.warning("grep command not found, skipping security scan")
            return True
        except Exception as e:
            self.errors.append(f"Security scan failed: {e}")
            return False

    def _check_dependencies(self) -> bool:
        """Dependency check"""
        if not Path("config/requirements.txt").exists():
            return True

        # Validate dependency format
        with open("config/requirements.txt") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if not any(op in line for op in ["==", ">=", "~=", "<="]):
                        logger.warning(f"Unpinned dependency: {line}")
                        return False

        return True
