#!/usr/bin/env python3
"""
CI/CD 수정 전략 모듈
Claude Code v8.4.0 - 에러 별 수정 전략 구현
"""


class FixStrategyManager:
    """CI/CD 에러 수정 전략 관리"""

    def __init__(self):
        # 에러 타입과 수정 방법 매핑
        self.fix_methods = {
            "docker_not_found": self.fix_docker_not_found,
            "permission_denied": self.fix_permission_issues,
            "npm_errors": self.fix_npm_errors,
            "registry_auth": self.fix_registry_auth,
            "ssh_connection": self.fix_ssh_connection,
            "disk_space": self.fix_disk_space,
            "timeout": self.fix_timeout_issues,
            "network": self.fix_network_issues,
        }

    def apply_fix(
        self, error_type: str, project_id: str, error_log: str, utils
    ) -> bool:
        """에러 타입에 따른 수정 전략 적용"""
        if error_type in self.fix_methods:
            return self.fix_methods[error_type](project_id, error_log, utils)
        return False

    def fix_docker_not_found(self, project_id: str, error_log: str, utils) -> bool:
        """Docker 누락 문제 수정"""
        print("🔧 Docker 설정 수정 중...")

        try:
            # .gitlab-ci.yml에 docker:dind 서비스 추가
            ci_config = utils.get_file_content(project_id, ".gitlab-ci.yml")

            if "docker:dind" not in ci_config:
                fixed_ci = self._add_docker_service_to_ci(ci_config)
                utils.update_file(project_id, ".gitlab-ci.yml", fixed_ci)
                return True

            return False
        except Exception as e:
            print("❌ Docker 설정 수정 실패: {e}")
            return False

    def fix_permission_issues(self, project_id: str, error_log: str, utils) -> bool:
        """권한 문제 수정"""
        print("🔧 권한 설정 수정 중...")

        try:
            # SSH 키 권한 수정을 위한 스크립트 추가
            ci_config = utils.get_file_content(project_id, ".gitlab-ci.yml")

            permission_fixes = [
                "chmod 600 ~/.ssh/* || true",
                "chmod +x ./scripts/* || true",
                "chmod 755 . || true",
            ]

            # before_script에 권한 수정 명령어 추가
            for fix in permission_fixes:
                if fix not in ci_config:
                    ci_config = self._add_to_before_script(ci_config, fix)

            utils.update_file(project_id, ".gitlab-ci.yml", ci_config)
            return True

        except Exception as e:
            print("❌ 권한 설정 수정 실패: {e}")
            return False

    def fix_npm_errors(self, project_id: str, error_log: str, utils) -> bool:
        """NPM 오류 수정"""
        print("🔧 NPM 설정 수정 중...")

        try:
            # Dockerfile 수정
            dockerfile = utils.get_file_content(project_id, "Dockerfile")

            npm_fixes = [
                "npm cache clean --force",
                "npm ci --prefer-offline --no-audit",
            ]

            # npm install을 npm ci로 변경
            if "npm install" in dockerfile and "npm ci" not in dockerfile:
                dockerfile = dockerfile.replace(
                    "npm install", "{npm_fixes[0]} && {npm_fixes[1]}"
                )
                utils.update_file(project_id, "Dockerfile", dockerfile)
                return True

            return False

        except Exception as e:
            print("❌ NPM 설정 수정 실패: {e}")
            return False

    def fix_registry_auth(self, project_id: str, error_log: str, utils) -> bool:
        """레지스트리 인증 문제 수정"""
        print("🔧 레지스트리 인증 수정 중...")

        try:
            # CI/CD 변수 업데이트
            auth_variables = {
                "REGISTRY_USER": "gitlab-ci-token",
                "REGISTRY_PASS": "$CI_JOB_TOKEN",
            }

            for key, value in auth_variables.items():
                utils.set_cicd_variable(project_id, key, value)

            # .gitlab-ci.yml에 docker login 추가
            ci_config = utils.get_file_content(project_id, ".gitlab-ci.yml")

            login_command = (
                "echo $REGISTRY_PASS | docker login -u $REGISTRY_USER "
                "--password-stdin $REGISTRY_URL"
            )
            if login_command not in ci_config:
                ci_config = self._add_to_before_script(ci_config, login_command)
                utils.update_file(project_id, ".gitlab-ci.yml", ci_config)

            return True

        except Exception as e:
            print("❌ 레지스트리 인증 수정 실패: {e}")
            return False

    def fix_ssh_connection(self, project_id: str, error_log: str, utils) -> bool:
        """SSH 연결 문제 수정"""
        print("🔧 SSH 연결 설정 수정 중...")

        try:
            # SSH 연결 옵션 개선
            ci_config = utils.get_file_content(project_id, ".gitlab-ci.yml")

            # SSH 개선 옵션들 (현재 미사용)
            # ssh_improvements = [
            #     "ssh-keyscan -p $DEPLOY_PORT -H $DEPLOY_HOST >> ~/.ssh/known_hosts",
            #     "ssh -o ConnectTimeout=30 -o ServerAliveInterval=60",
            # ]

            # SSH 명령어를 개선된 버전으로 교체
            if "ssh -p $DEPLOY_PORT" in ci_config and "ConnectTimeout" not in ci_config:
                ci_config = ci_config.replace(
                    "ssh -p $DEPLOY_PORT",
                    "ssh -o ConnectTimeout=30 -o ServerAliveInterval=60 -p $DEPLOY_PORT",
                )
                utils.update_file(project_id, ".gitlab-ci.yml", ci_config)
                return True

            return False

        except Exception as e:
            print("❌ SSH 연결 설정 수정 실패: {e}")
            return False

    def fix_disk_space(self, project_id: str, error_log: str, utils) -> bool:
        """디스크 공간 문제 수정"""
        print("🔧 디스크 공간 정리 중...")

        try:
            # .gitlab-ci.yml에 정리 명령어 추가
            ci_config = utils.get_file_content(project_id, ".gitlab-ci.yml")

            cleanup_commands = [
                "docker system prune -af --volumes || true",
                "df -h",
                "rm -rf /tmp/* || true",
            ]

            # before_script에 정리 명령어 추가
            for cmd in cleanup_commands:
                if cmd not in ci_config:
                    ci_config = self._add_to_before_script(ci_config, cmd)

            utils.update_file(project_id, ".gitlab-ci.yml", ci_config)
            return True

        except Exception as e:
            print("❌ 디스크 공간 정리 실패: {e}")
            return False

    def fix_timeout_issues(self, project_id: str, error_log: str, utils) -> bool:
        """타임아웃 문제 수정"""
        print("🔧 타임아웃 설정 수정 중...")

        try:
            # .gitlab-ci.yml에 타임아웃 설정 추가
            ci_config = utils.get_file_content(project_id, ".gitlab-ci.yml")

            # 전역 타임아웃 설정 추가
            if "timeout:" not in ci_config:
                ci_config = self._add_global_timeout(ci_config)
                utils.update_file(project_id, ".gitlab-ci.yml", ci_config)
                return True

            return False

        except Exception as e:
            print("❌ 타임아웃 설정 수정 실패: {e}")
            return False

    def fix_network_issues(self, project_id: str, error_log: str, utils) -> bool:
        """네트워크 문제 수정"""
        print("🔧 네트워크 설정 수정 중...")

        try:
            # DNS 설정 및 재시도 로직 추가
            ci_config = utils.get_file_content(project_id, ".gitlab-ci.yml")

            network_fixes = [
                "echo 'nameserver 8.8.8.8' >> /etc/resolv.conf || true",
                "ping -c 1 google.com || true",
            ]

            for fix in network_fixes:
                if fix not in ci_config:
                    ci_config = self._add_to_before_script(ci_config, fix)

            utils.update_file(project_id, ".gitlab-ci.yml", ci_config)
            return True

        except Exception as e:
            print("❌ 네트워크 설정 수정 실패: {e}")
            return False

    # Helper methods for CI configuration manipulation
    def _add_docker_service_to_ci(self, ci_content: str) -> str:
        """CI 설정에 Docker 서비스 추가"""
        docker_service = """services:
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

    def _add_to_before_script(self, ci_content: str, command: str) -> str:
        """before_script에 명령어 추가"""
        lines = ci_content.split("\n")

        for i, line in enumerate(lines):
            if line.strip() == "before_script:":
                # 다음 라인에 명령어 추가
                lines.insert(i + 1, "    - {command}")
                break
        else:
            # before_script가 없으면 추가
            lines.insert(0, "before_script:\n  - {command}")

        return "\n".join(lines)

    def _add_global_timeout(self, ci_content: str) -> str:
        """전역 타임아웃 설정 추가"""
        timeout_config = """default:
  timeout: 1h
"""

        lines = ci_content.split("\n")
        lines.insert(0, timeout_config.strip())
        return "\n".join(lines)
