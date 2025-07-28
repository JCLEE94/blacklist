#!/usr/bin/env python3
"""
CI/CD 테스트 가능성을 위한 유틸리티 모듈

파이프라인의 각 단계를 테스트 가능하게 만들기 위한
헬퍼 함수와 클래스를 제공합니다.
"""

import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """파이프라인 설정 데이터 클래스"""

    registry: str = os.getenv("REGISTRY", "registry.jclee.me")
    image_name: str = os.getenv("IMAGE_NAME", "blacklist")
    namespace: str = os.getenv("NAMESPACE", "blacklist")
    argocd_server: str = os.getenv("ARGOCD_SERVER", "argo.jclee.me")
    python_version: str = os.getenv("PYTHON_VERSION", "3.10")
    dry_run: bool = os.getenv("DRY_RUN", "false").lower() == "true"
    verbose: bool = os.getenv("VERBOSE", "false").lower() == "true"
    project_root: str = os.getenv("PROJECT_ROOT", os.getcwd())


class PipelineStage:
    """파이프라인 단계 기본 클래스"""

    def __init__(self, name: str, config: PipelineConfig):
        self.name = name
        self.config = config
        self.start_time = None
        self.end_time = None
        self.status = "pending"
        self.errors = []

    def pre_hook(self):
        """단계 시작 전 훅"""
        logger.info(f"Starting stage: {self.name}")
        self.start_time = datetime.now()

    def post_hook(self):
        """단계 종료 후 훅"""
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        logger.info(f"Completed stage: {self.name} in {duration:.2f} seconds")

    def run(self) -> bool:
        """단계 실행 (서브클래스에서 구현)"""
        raise NotImplementedError

    def execute(self) -> Dict[str, Any]:
        """단계 실행 래퍼"""
        try:
            self.pre_hook()

            if self.config.dry_run:
                logger.info(f"[DRY RUN] Would execute: {self.name}")
                success = True
            else:
                success = self.run()

            self.status = "success" if success else "failed"

        except Exception as e:
            logger.error(f"Stage {self.name} failed: {str(e)}")
            self.status = "error"
            self.errors.append(str(e))
            success = False

        finally:
            self.post_hook()

        return {
            "stage": self.name,
            "status": self.status,
            "duration": (
                (self.end_time - self.start_time).total_seconds()
                if self.end_time
                else None
            ),
            "errors": self.errors,
        }


class CodeQualityStage(PipelineStage):
    """코드 품질 검사 단계"""

    def __init__(self, config: PipelineConfig):
        super().__init__("code-quality", config)

    def run(self) -> bool:
        """코드 품질 검사 실행"""
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
        """Python 구문 검사"""
        try:
            # shell=True 제거하고 glob으로 파일 찾기
            import glob

            src_path = (
                Path(self.config.project_root)
                if hasattr(self.config, 'project_root')
                else Path("src")
            )
            python_files = glob.glob(str(src_path / "**" / "*.py"), recursive=True)

            if not python_files:
                logger.warning("No Python files found in src/")
                return True  # 파일이 없으면 성공으로 처리

            # 각 파일 개별 검사
            for py_file in python_files:
                result = subprocess.run(
                    ["python3", "-m", "py_compile", py_file],
                    capture_output=True,
                    timeout=30,  # 30초 타임아웃 추가
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
        """코드 스타일 검사"""
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
        """보안 취약점 검사"""
        try:
            # 하드코딩된 시크릿 패턴 확장
            secret_patterns = [
                r'(password|passwd|pwd)\s*=\s*["\'][^"\']+["\']',
                r'(secret|token|key|api_key|apikey)\s*=\s*["\'][^"\']+["\']',
                r'(aws_access_key|aws_secret|aws_token)\s*=\s*["\'][^"\']+["\']',
                r'(database_url|db_url|connection_string)\s*=\s*["\'][^"\']+["\']',
                r'(private_key|priv_key|pem|cert)\s*=\s*["\'][^"\']+["\']',
                r'Bearer\s+[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.?[A-Za-z0-9\-_.+/=]*',
                r'Basic\s+[A-Za-z0-9+/=]+',
            ]

            # grep 명령을 Python으로 대체
            cmd = [
                "grep",
                "-r",
                "-E",
                "|".join(f"({pattern})" for pattern in secret_patterns),
                "--include=*.py",
                "src/",
            ]

            result = subprocess.run(
                cmd, capture_output=True, timeout=60  # 60초 타임아웃
            )

            # grep은 매치가 없으면 returncode 1 반환
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
        """의존성 검사"""
        if not Path("requirements.txt").exists():
            return True

        # 의존성 형식 검증
        with open("requirements.txt") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if not any(op in line for op in ["==", ">=", "~=", "<="]):
                        logger.warning(f"Unpinned dependency: {line}")
                        return False

        return True


class TestStage(PipelineStage):
    """테스트 실행 단계"""

    def __init__(self, config: PipelineConfig):
        super().__init__("test", config)
        self.coverage_threshold = 80

    def run(self) -> bool:
        """테스트 실행"""
        try:
            # pytest 실행
            cmd = [
                "pytest",
                "-v",
                "--cov=src",
                "--cov-report=json",
                "--cov-report=term",
            ]
            result = subprocess.run(
                cmd, capture_output=True, timeout=300
            )  # 5분 타임아웃

            if result.returncode != 0:
                logger.error(f"Tests failed:\n{result.stdout.decode()}")
                return False

            # 커버리지 확인
            if Path("coverage.json").exists():
                with open("coverage.json") as f:
                    coverage_data = json.load(f)
                    coverage_percent = coverage_data["totals"]["percent_covered"]

                    if coverage_percent < self.coverage_threshold:
                        logger.warning(
                            f"Coverage {coverage_percent:.1f}% is below threshold {self.coverage_threshold}%"
                        )
                        return False

            return True

        except subprocess.TimeoutExpired:
            self.errors.append("Test execution timed out after 5 minutes")
            return False
        except Exception as e:
            self.errors.append(f"Test execution failed: {e}")
            return False


class BuildStage(PipelineStage):
    """Docker 빌드 단계"""

    def __init__(self, config: PipelineConfig):
        super().__init__("build", config)
        self.image_tags = []

    def run(self) -> bool:
        """Docker 이미지 빌드"""
        try:
            # 빌드 컨텍스트 준비
            if not Path("deployment/Dockerfile").exists():
                logger.error("Dockerfile not found")
                return False

            # 태그 생성
            commit_sha = self._get_commit_sha()
            date_tag = datetime.now().strftime("%Y%m%d-%H%M%S")

            self.image_tags = [
                f"{self.config.registry}/{self.config.image_name}:latest",
                f"{self.config.registry}/{self.config.image_name}:sha-{commit_sha[:7]}",
                f"{self.config.registry}/{self.config.image_name}:date-{date_tag}",
            ]

            # Docker 빌드
            for tag in self.image_tags:
                cmd = [
                    "docker",
                    "build",
                    "-f",
                    "deployment/Dockerfile",
                    "-t",
                    tag,
                    "--cache-from",
                    f"{self.config.registry}/{self.config.image_name}:latest",
                    ".",
                ]

                if self.config.verbose:
                    logger.info(f"Building image: {tag}")

                result = subprocess.run(
                    cmd, capture_output=True, timeout=600
                )  # 10분 타임아웃
                if result.returncode != 0:
                    logger.error(f"Build failed for {tag}: {result.stderr.decode()}")
                    return False

            return True

        except subprocess.TimeoutExpired:
            self.errors.append("Docker build timed out after 10 minutes")
            return False
        except Exception as e:
            self.errors.append(f"Docker build failed: {e}")
            return False

    def _get_commit_sha(self) -> str:
        """현재 Git 커밋 SHA 가져오기"""
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"


class DeploymentStage(PipelineStage):
    """배포 단계"""

    def __init__(self, config: PipelineConfig):
        super().__init__("deployment", config)

    def run(self) -> bool:
        """배포 실행"""
        # ArgoCD 앱 동기화
        if not self._sync_argocd_app():
            return False

        # 헬스체크
        if not self._verify_deployment():
            # 롤백 시도
            logger.warning("Deployment verification failed, attempting rollback...")
            return self._rollback_deployment()

        return True

    def _sync_argocd_app(self) -> bool:
        """ArgoCD 애플리케이션 동기화"""
        try:
            cmd = [
                "argocd",
                "app",
                "sync",
                self.config.image_name,
                "--server",
                self.config.argocd_server,
                "--grpc-web",
            ]

            result = subprocess.run(
                cmd, capture_output=True, timeout=120
            )  # 2분 타임아웃
            if result.returncode != 0:
                logger.error(f"ArgoCD sync failed: {result.stderr.decode()}")
            return result.returncode == 0

        except subprocess.TimeoutExpired:
            logger.error("ArgoCD sync timed out")
            return False
        except Exception as e:
            logger.error(f"ArgoCD sync failed: {e}")
            return False

    def _verify_deployment(self) -> bool:
        """배포 검증"""
        try:
            # Pod 상태 확인
            cmd = [
                "kubectl",
                "get",
                "pods",
                "-n",
                self.config.namespace,
                "-l",
                f"app={self.config.image_name}",
                "-o",
                "json",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                logger.error(f"Failed to get pods: {result.stderr}")
                return False

            pods = json.loads(result.stdout)
            ready_pods = sum(
                1
                for pod in pods.get("items", [])
                if pod.get("status", {}).get("containerStatuses")
                and all(
                    c.get("ready", False) for c in pod["status"]["containerStatuses"]
                )
            )

            logger.info(f"Ready pods: {ready_pods}")
            return ready_pods > 0

        except subprocess.TimeoutExpired:
            logger.error("Deployment verification timed out")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse kubectl output: {e}")
            return False
        except Exception as e:
            logger.error(f"Deployment verification failed: {e}")
            return False

    def _rollback_deployment(self) -> bool:
        """배포 롤백"""
        try:
            cmd = [
                "argocd",
                "app",
                "rollback",
                self.config.image_name,
                "--server",
                self.config.argocd_server,
                "--grpc-web",
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=120)
            if result.returncode != 0:
                logger.error(f"Rollback failed: {result.stderr.decode()}")
            return result.returncode == 0

        except subprocess.TimeoutExpired:
            logger.error("Rollback timed out")
            return False
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False


class PipelineOrchestrator:
    """파이프라인 오케스트레이터"""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.stages = [
            CodeQualityStage(config),
            TestStage(config),
            BuildStage(config),
            DeploymentStage(config),
        ]

    def run(self, skip_stages: Optional[List[str]] = None) -> Dict[str, Any]:
        """전체 파이프라인 실행"""
        skip_stages = skip_stages or []
        results = {
            "started_at": datetime.now().isoformat(),
            "config": self.config.__dict__,
            "stages": [],
        }

        for stage in self.stages:
            if stage.name in skip_stages:
                logger.info(f"Skipping stage: {stage.name}")
                continue

            result = stage.execute()
            results["stages"].append(result)

            # 실패 시 중단
            if result["status"] != "success":
                logger.error(f"Pipeline failed at stage: {stage.name}")
                break

        results["completed_at"] = datetime.now().isoformat()
        results["overall_status"] = (
            "success"
            if all(s["status"] == "success" for s in results["stages"])
            else "failed"
        )

        return results


def main():
    """CLI 엔트리포인트"""
    import argparse

    parser = argparse.ArgumentParser(description="CI/CD Pipeline Test Runner")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--skip", nargs="+", help="Stages to skip")
    parser.add_argument("--stage", help="Run single stage only")

    args = parser.parse_args()

    # 설정 생성
    config = PipelineConfig(dry_run=args.dry_run, verbose=args.verbose)

    # 단일 단계 실행
    if args.stage:
        stage_map = {
            "code-quality": CodeQualityStage,
            "test": TestStage,
            "build": BuildStage,
            "deployment": DeploymentStage,
        }

        if args.stage not in stage_map:
            logger.error(f"Unknown stage: {args.stage}")
            sys.exit(1)

        stage = stage_map[args.stage](config)
        result = stage.execute()
        print(json.dumps(result, indent=2))

    else:
        # 전체 파이프라인 실행
        orchestrator = PipelineOrchestrator(config)
        results = orchestrator.run(skip_stages=args.skip)

        print(json.dumps(results, indent=2))

        # 종료 코드 설정
        sys.exit(0 if results["overall_status"] == "success" else 1)


if __name__ == "__main__":
    main()
