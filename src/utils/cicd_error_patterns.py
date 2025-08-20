#!/usr/bin/env python3
"""
CI/CD 에러 패턴 정의 및 관리
Claude Code v8.4.0 - 에러 패턴 매칭 시스템
"""

from typing import Any, Dict


class ErrorPatternManager:
    """CI/CD 에러 패턴 정의 및 매칭 관리"""

    def __init__(self):
        # 에러 패턴과 수정 방법 매핑
        self.error_patterns = {
            "docker_not_found": {
                "patterns": ["docker: command not found", "docker: not found"],
                "severity": "critical",
                "description": "Docker 명령어를 찾을 수 없음",
            },
            "permission_denied": {
                "patterns": ["Permission denied", "permission denied", "EACCES"],
                "severity": "high",
                "description": "파일 또는 디렉토리 권한 문제",
            },
            "npm_errors": {
                "patterns": ["npm ERR!", "npm WARN", "npm install failed"],
                "severity": "medium",
                "description": "NPM 패키지 관리 오류",
            },
            "registry_auth": {
                "patterns": [
                    "unauthorized: authentication required",
                    "docker login",
                    "registry auth",
                ],
                "severity": "high",
                "description": "Docker 레지스트리 인증 실패",
            },
            "ssh_connection": {
                "patterns": [
                    "ssh: connect to host",
                    "Connection refused",
                    "ssh timeout",
                ],
                "severity": "high",
                "description": "SSH 연결 실패",
            },
            "disk_space": {
                "patterns": ["no space left on device", "disk full", "ENOSPC"],
                "severity": "critical",
                "description": "디스크 공간 부족",
            },
            "timeout": {
                "patterns": ["timeout", "timed out", "operation timeout"],
                "severity": "medium",
                "description": "작업 시간 초과",
            },
            "network": {
                "patterns": [
                    "network unreachable",
                    "DNS resolution",
                    "network timeout",
                ],
                "severity": "medium",
                "description": "네트워크 연결 문제",
            },
        }

    def get_error_patterns(self) -> Dict[str, Any]:
        """모든 에러 패턴 반환"""
        return self.error_patterns

    def detect_error_type(self, error_log: str) -> str:
        """에러 로그에서 에러 타입 감지"""
        error_log_lower = error_log.lower()

        # 심각도별 우선순위로 검사
        critical_errors = []
        high_errors = []
        medium_errors = []

        for error_type, config in self.error_patterns.items():
            for pattern in config["patterns"]:
                if pattern.lower() in error_log_lower:
                    if config["severity"] == "critical":
                        critical_errors.append(error_type)
                    elif config["severity"] == "high":
                        high_errors.append(error_type)
                    else:
                        medium_errors.append(error_type)
                    break

        # 가장 심각한 에러부터 반환
        if critical_errors:
            return critical_errors[0]
        elif high_errors:
            return high_errors[0]
        elif medium_errors:
            return medium_errors[0]
        else:
            return "unknown"

    def get_error_severity(self, error_type: str) -> str:
        """에러 타입의 심각도 반환"""
        if error_type in self.error_patterns:
            return self.error_patterns[error_type]["severity"]
        return "unknown"

    def get_error_description(self, error_type: str) -> str:
        """에러 타입의 설명 반환"""
        if error_type in self.error_patterns:
            return self.error_patterns[error_type]["description"]
        return "알 수 없는 에러"

    def add_custom_pattern(
        self,
        error_type: str,
        patterns: list,
        severity: str = "medium",
        description: str = "",
    ):
        """사용자 정의 에러 패턴 추가"""
        self.error_patterns[error_type] = {
            "patterns": patterns,
            "severity": severity,
            "description": description or "사용자 정의 에러: {error_type}",
        }

    def remove_pattern(self, error_type: str) -> bool:
        """에러 패턴 제거"""
        if error_type in self.error_patterns:
            del self.error_patterns[error_type]
            return True
        return False

    def get_patterns_by_severity(self, severity: str) -> Dict[str, Any]:
        """특정 심각도의 에러 패턴들 반환"""
        return {
            error_type: config
            for error_type, config in self.error_patterns.items()
            if config["severity"] == severity
        }

    def analyze_error_frequency(self, error_logs: list) -> Dict[str, int]:
        """에러 로그 리스트에서 에러 타입별 빈도 분석"""
        frequency = {}

        for log in error_logs:
            error_type = self.detect_error_type(log)
            if error_type != "unknown":
                frequency[error_type] = frequency.get(error_type, 0) + 1

        # 빈도순으로 정렬하여 반환
        return dict(sorted(frequency.items(), key=lambda x: x[1], reverse=True))
