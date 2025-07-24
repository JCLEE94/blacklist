#!/usr/bin/env python3
"""
CI/CD 자동 트러블슈팅 시스템
Claude Code v8.4.0 - 완전 자동화된 파이프라인 문제 해결
"""

import requests
import time
import json
import re
import subprocess
from typing import Dict, List, Optional, Any


class CICDTroubleshooter:
    """CI/CD 파이프라인 자동 트러블슈팅 및 복구"""

    def __init__(self, gateway_url=None, api_key=None):
        import os

        self.gateway_url = gateway_url or os.environ.get(
            "AI_GATEWAY_URL", "http://192.168.50.120:5678"
        )
        self.api_key = api_key or os.environ.get("AI_GATEWAY_API_KEY", "default-key")
        self.base_url = self.gateway_url
        self.headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # 에러 패턴과 수정 방법 매핑
        self.error_patterns = {
            "docker_not_found": {
                "patterns": ["docker: command not found", "docker: not found"],
                "fix_method": self.fix_docker_not_found,
                "severity": "critical",
            },
            "permission_denied": {
                "patterns": ["Permission denied", "permission denied", "EACCES"],
                "fix_method": self.fix_permission_issues,
                "severity": "high",
            },
            "npm_errors": {
                "patterns": ["npm ERR!", "npm WARN", "npm install failed"],
                "fix_method": self.fix_npm_errors,
                "severity": "medium",
            },
            "registry_auth": {
                "patterns": [
                    "unauthorized: authentication required",
                    "docker login",
                    "registry auth",
                ],
                "fix_method": self.fix_registry_auth,
                "severity": "high",
            },
            "ssh_connection": {
                "patterns": [
                    "ssh: connect to host",
                    "Connection refused",
                    "ssh timeout",
                ],
                "fix_method": self.fix_ssh_connection,
                "severity": "high",
            },
            "disk_space": {
                "patterns": ["no space left on device", "disk full", "ENOSPC"],
                "fix_method": self.fix_disk_space,
                "severity": "critical",
            },
            "timeout": {
                "patterns": ["timeout", "timed out", "operation timeout"],
                "fix_method": self.fix_timeout_issues,
                "severity": "medium",
            },
            "network": {
                "patterns": [
                    "network unreachable",
                    "DNS resolution",
                    "network timeout",
                ],
                "fix_method": self.fix_network_issues,
                "severity": "medium",
            },
        }

    def monitor_and_fix_pipeline(
        self, project_id: str, pipeline_id: str
    ) -> Dict[str, Any]:
        """파이프라인 모니터링 및 자동 수정"""
        print(f"🔧 파이프라인 자동 트러블슈팅 시작: {pipeline_id}")

        # 1. 파이프라인 상태 확인
        pipeline_status = self.get_pipeline_status(project_id, pipeline_id)

        if pipeline_status != "failed":
            return {"status": "success", "message": "파이프라인이 실패하지 않음"}

        # 2. 실패한 작업 분석
        failed_jobs = self.get_failed_jobs(project_id, pipeline_id)

        fixes_applied = []
        for job in failed_jobs:
            job_fixes = self.analyze_and_fix_job(project_id, job)
            fixes_applied.extend(job_fixes)

        # 3. 수정 후 재시도
        if fixes_applied:
            print(f"✅ 적용된 수정사항: {', '.join(fixes_applied)}")
            retry_result = self.retry_pipeline(project_id, pipeline_id)

            return {
                "status": "fixed_and_retried",
                "fixes_applied": fixes_applied,
                "retry_result": retry_result,
            }
        else:
            return {"status": "no_fixes_available", "message": "자동 수정할 수 있는 문제를 찾지 못함"}

    def get_pipeline_status(self, project_id: str, pipeline_id: str) -> str:
        """파이프라인 상태 확인"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/pipelines/{pipeline_id}",
                params={"project_id": project_id},
            )
            if response.status_code == 200:
                data = response.json().get("data", {})
                return data.get("pipeline_status", "unknown")
            else:
                return "unknown"
        except Exception as e:
            print(f"❌ 파이프라인 상태 확인 실패: {e}")
            return "unknown"

    def get_failed_jobs(
        self, project_id: str, pipeline_id: str
    ) -> List[Dict[str, Any]]:
        """실패한 작업 목록 조회"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/pipelines/{pipeline_id}/jobs",
                params={"project_id": project_id},
            )
            if response.status_code == 200:
                jobs_data = response.json().get("data", {})
                failed_jobs = [
                    job
                    for job in jobs_data.get("jobs", [])
                    if job.get("status") == "failed"
                ]
                return failed_jobs
            else:
                return []
        except Exception as e:
            print(f"❌ 실패한 작업 조회 실패: {e}")
            return []

    def analyze_and_fix_job(self, project_id: str, job: Dict[str, Any]) -> List[str]:
        """작업 분석 및 자동 수정"""
        job_name = job.get("name", "unknown")
        job_trace = job.get("trace", "")

        print(f"🔍 분석 중: {job_name}")

        fixes_applied = []

        # 에러 패턴 매칭 및 수정
        for error_type, error_config in self.error_patterns.items():
            for pattern in error_config["patterns"]:
                if pattern.lower() in job_trace.lower():
                    print(f"🎯 감지된 문제: {error_type} - {pattern}")

                    try:
                        fix_result = error_config["fix_method"](project_id, job_trace)
                        if fix_result:
                            fixes_applied.append(f"{error_type}_fix")
                            print(f"✅ 수정 완료: {error_type}")
                        else:
                            print(f"❌ 수정 실패: {error_type}")
                    except Exception as e:
                        print(f"❌ 수정 중 오류: {error_type} - {e}")

                    break  # 첫 번째 매칭된 패턴만 처리

        return fixes_applied

    def fix_docker_not_found(self, project_id: str, error_log: str) -> bool:
        """Docker 누락 문제 수정"""
        print("🔧 Docker 설정 수정 중...")

        try:
            # .gitlab-ci.yml에 docker:dind 서비스 추가
            ci_config = self.get_file_content(project_id, ".gitlab-ci.yml")

            if "docker:dind" not in ci_config:
                fixed_ci = self.add_docker_service_to_ci(ci_config)
                self.update_file(project_id, ".gitlab-ci.yml", fixed_ci)
                return True

            return False
        except Exception as e:
            print(f"❌ Docker 설정 수정 실패: {e}")
            return False

    def fix_permission_issues(self, project_id: str, error_log: str) -> bool:
        """권한 문제 수정"""
        print("🔧 권한 설정 수정 중...")

        try:
            # SSH 키 권한 수정을 위한 스크립트 추가
            ci_config = self.get_file_content(project_id, ".gitlab-ci.yml")

            permission_fixes = [
                "chmod 600 ~/.ssh/* || true",
                "chmod +x ./scripts/* || true",
                "chmod 755 . || true",
            ]

            # before_script에 권한 수정 명령어 추가
            for fix in permission_fixes:
                if fix not in ci_config:
                    ci_config = self.add_to_before_script(ci_config, fix)

            self.update_file(project_id, ".gitlab-ci.yml", ci_config)
            return True

        except Exception as e:
            print(f"❌ 권한 설정 수정 실패: {e}")
            return False

    def fix_npm_errors(self, project_id: str, error_log: str) -> bool:
        """NPM 오류 수정"""
        print("🔧 NPM 설정 수정 중...")

        try:
            # Dockerfile 수정
            dockerfile = self.get_file_content(project_id, "Dockerfile")

            npm_fixes = [
                "npm cache clean --force",
                "npm ci --prefer-offline --no-audit",
            ]

            # npm install을 npm ci로 변경
            if "npm install" in dockerfile and "npm ci" not in dockerfile:
                dockerfile = dockerfile.replace(
                    "npm install", f"{npm_fixes[0]} && {npm_fixes[1]}"
                )
                self.update_file(project_id, "Dockerfile", dockerfile)
                return True

            return False

        except Exception as e:
            print(f"❌ NPM 설정 수정 실패: {e}")
            return False

    def fix_registry_auth(self, project_id: str, error_log: str) -> bool:
        """레지스트리 인증 문제 수정"""
        print("🔧 레지스트리 인증 수정 중...")

        try:
            # CI/CD 변수 업데이트
            auth_variables = {
                "REGISTRY_USER": "gitlab-ci-token",
                "REGISTRY_PASS": "$CI_JOB_TOKEN",
            }

            for key, value in auth_variables.items():
                self.set_cicd_variable(project_id, key, value)

            # .gitlab-ci.yml에 docker login 추가
            ci_config = self.get_file_content(project_id, ".gitlab-ci.yml")

            login_command = "echo $REGISTRY_PASS | docker login -u $REGISTRY_USER --password-stdin $REGISTRY_URL"
            if login_command not in ci_config:
                ci_config = self.add_to_before_script(ci_config, login_command)
                self.update_file(project_id, ".gitlab-ci.yml", ci_config)

            return True

        except Exception as e:
            print(f"❌ 레지스트리 인증 수정 실패: {e}")
            return False

    def fix_ssh_connection(self, project_id: str, error_log: str) -> bool:
        """SSH 연결 문제 수정"""
        print("🔧 SSH 연결 설정 수정 중...")

        try:
            # SSH 연결 옵션 개선
            ci_config = self.get_file_content(project_id, ".gitlab-ci.yml")

            ssh_improvements = [
                "ssh-keyscan -p $DEPLOY_PORT -H $DEPLOY_HOST >> ~/.ssh/known_hosts",
                "ssh -o ConnectTimeout=30 -o ServerAliveInterval=60",
            ]

            # SSH 명령어를 개선된 버전으로 교체
            if "ssh -p $DEPLOY_PORT" in ci_config and "ConnectTimeout" not in ci_config:
                ci_config = ci_config.replace(
                    "ssh -p $DEPLOY_PORT",
                    "ssh -o ConnectTimeout=30 -o ServerAliveInterval=60 -p $DEPLOY_PORT",
                )
                self.update_file(project_id, ".gitlab-ci.yml", ci_config)
                return True

            return False

        except Exception as e:
            print(f"❌ SSH 연결 설정 수정 실패: {e}")
            return False

    def fix_disk_space(self, project_id: str, error_log: str) -> bool:
        """디스크 공간 문제 수정"""
        print("🔧 디스크 공간 정리 중...")

        try:
            # .gitlab-ci.yml에 정리 명령어 추가
            ci_config = self.get_file_content(project_id, ".gitlab-ci.yml")

            cleanup_commands = [
                "docker system prune -af --volumes || true",
                "df -h",
                "rm -rf /tmp/* || true",
            ]

            # before_script에 정리 명령어 추가
            for cmd in cleanup_commands:
                if cmd not in ci_config:
                    ci_config = self.add_to_before_script(ci_config, cmd)

            self.update_file(project_id, ".gitlab-ci.yml", ci_config)
            return True

        except Exception as e:
            print(f"❌ 디스크 공간 정리 실패: {e}")
            return False

    def fix_timeout_issues(self, project_id: str, error_log: str) -> bool:
        """타임아웃 문제 수정"""
        print("🔧 타임아웃 설정 수정 중...")

        try:
            # .gitlab-ci.yml에 타임아웃 설정 추가
            ci_config = self.get_file_content(project_id, ".gitlab-ci.yml")

            # 전역 타임아웃 설정 추가
            if "timeout:" not in ci_config:
                ci_config = self.add_global_timeout(ci_config)
                self.update_file(project_id, ".gitlab-ci.yml", ci_config)
                return True

            return False

        except Exception as e:
            print(f"❌ 타임아웃 설정 수정 실패: {e}")
            return False

    def fix_network_issues(self, project_id: str, error_log: str) -> bool:
        """네트워크 문제 수정"""
        print("🔧 네트워크 설정 수정 중...")

        try:
            # DNS 설정 및 재시도 로직 추가
            ci_config = self.get_file_content(project_id, ".gitlab-ci.yml")

            network_fixes = [
                "echo 'nameserver 8.8.8.8' >> /etc/resolv.conf || true",
                "ping -c 1 google.com || true",
            ]

            for fix in network_fixes:
                if fix not in ci_config:
                    ci_config = self.add_to_before_script(ci_config, fix)

            self.update_file(project_id, ".gitlab-ci.yml", ci_config)
            return True

        except Exception as e:
            print(f"❌ 네트워크 설정 수정 실패: {e}")
            return False

    # 유틸리티 메서드들
    def get_file_content(self, project_id: str, file_path: str) -> str:
        """파일 내용 조회"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/projects/{project_id}/files/{file_path}"
            )
            if response.status_code == 200:
                return response.json().get("content", "")
            return ""
        except:
            return ""

    def update_file(self, project_id: str, file_path: str, content: str) -> bool:
        """파일 내용 업데이트"""
        try:
            data = {
                "project_id": project_id,
                "file_path": file_path,
                "content": content,
                "commit_message": f"Auto-fix: {file_path}",
            }
            response = self.session.post(f"{self.base_url}/api/v1/files", json=data)
            return response.status_code in [200, 201]
        except:
            return False

    def set_cicd_variable(self, project_id: str, key: str, value: str) -> bool:
        """CI/CD 변수 설정"""
        try:
            data = {"key": key, "value": value, "protected": False, "masked": False}
            response = self.session.post(
                f"{self.base_url}/api/v1/projects/{project_id}/variables", json=data
            )
            return response.status_code in [200, 201]
        except:
            return False

    def retry_pipeline(self, project_id: str, pipeline_id: str) -> bool:
        """파이프라인 재시도"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/pipelines/{pipeline_id}/retry",
                json={"project_id": project_id},
            )
            return response.status_code in [200, 201]
        except:
            return False

    def add_docker_service_to_ci(self, ci_content: str) -> str:
        """CI 설정에 Docker 서비스 추가"""
        docker_service = """
services:
  - docker:dind

variables:
  DOCKER_DRIVER: overlay2
  DOCKER_TLS_CERTDIR: ""
"""

        # services: 섹션이 없으면 추가
        if "services:" not in ci_content:
            lines = ci_content.split("\n")
            # variables 섹션 앞에 services 추가
            for i, line in enumerate(lines):
                if line.strip().startswith("variables:"):
                    lines.insert(i, docker_service.strip())
                    break
            ci_content = "\n".join(lines)

        return ci_content

    def add_to_before_script(self, ci_content: str, command: str) -> str:
        """before_script에 명령어 추가"""
        lines = ci_content.split("\n")

        for i, line in enumerate(lines):
            if line.strip() == "before_script:":
                # 다음 라인에 명령어 추가
                lines.insert(i + 1, f"    - {command}")
                break
        else:
            # before_script가 없으면 추가
            lines.insert(0, f"before_script:\n  - {command}")

        return "\n".join(lines)

    def add_global_timeout(self, ci_content: str) -> str:
        """전역 타임아웃 설정 추가"""
        timeout_config = """
default:
  timeout: 1h
"""

        lines = ci_content.split("\n")
        lines.insert(0, timeout_config.strip())
        return "\n".join(lines)


def main():
    """테스트용 메인 함수"""
    troubleshooter = CICDTroubleshooter()

    # 예시: blacklist 프로젝트의 파이프라인 트러블슈팅
    project_id = "blacklist"
    pipeline_id = "12345"  # 실제 파이프라인 ID로 교체

    result = troubleshooter.monitor_and_fix_pipeline(project_id, pipeline_id)
    print(f"🎯 트러블슈팅 결과: {result}")


if __name__ == "__main__":
    main()
