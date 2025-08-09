#!/usr/bin/env python3
"""
CI/CD 유틸리티 모듈
Claude Code v8.4.0 - 파일 및 API 유틸리티
"""

from typing import Any, Dict

import requests


class CICDUtils:
    """CI/CD 작업을 위한 유틸리티 함수들"""

    def __init__(self, session: requests.Session, base_url: str):
        self.session = session
        self.base_url = base_url

    def get_file_content(self, project_id: str, file_path: str) -> str:
        """파일 내용 조회"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/projects/{project_id}/files/{file_path}"
            )
            if response.status_code == 200:
                return response.json().get("content", "")
            return ""
        except Exception as e:
            print(f"❌ 파일 조회 실패 ({file_path}): {e}")
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
            if response.status_code in [200, 201]:
                print(f"✅ 파일 업데이트 완료: {file_path}")
                return True
            else:
                print(f"❌ 파일 업데이트 실패 ({file_path}): {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 파일 업데이트 실패 ({file_path}): {e}")
            return False

    def set_cicd_variable(self, project_id: str, key: str, value: str) -> bool:
        """CI/CD 변수 설정"""
        try:
            data = {"key": key, "value": value, "protected": False, "masked": False}
            response = self.session.post(
                f"{self.base_url}/api/v1/projects/{project_id}/variables", json=data
            )
            if response.status_code in [200, 201]:
                print(f"✅ CI/CD 변수 설정 완료: {key}")
                return True
            else:
                print(f"❌ CI/CD 변수 설정 실패 ({key}): {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ CI/CD 변수 설정 실패 ({key}): {e}")
            return False

    def retry_pipeline(self, project_id: str, pipeline_id: str) -> bool:
        """파이프라인 재시도"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/pipelines/{pipeline_id}/retry",
                json={"project_id": project_id},
            )
            if response.status_code in [200, 201]:
                print(f"✅ 파이프라인 재시도 시작: {pipeline_id}")
                return True
            else:
                print(
                    f"❌ 파이프라인 재시도 실패 ({pipeline_id}): {response.status_code}"
                )
                return False
        except Exception as e:
            print(f"❌ 파이프라인 재시도 실패 ({pipeline_id}): {e}")
            return False

    def get_project_info(self, project_id: str) -> Dict[str, Any]:
        """프로젝트 정보 조회"""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/projects/{project_id}")
            if response.status_code == 200:
                return response.json().get("data", {})
            return {}
        except Exception as e:
            print(f"❌ 프로젝트 정보 조회 실패: {e}")
            return {}

    def list_pipelines(self, project_id: str, status: str = "failed") -> list:
        """파이프라인 목록 조회"""
        try:
            params = {"project_id": project_id, "status": status}
            response = self.session.get(
                f"{self.base_url}/api/v1/pipelines", params=params
            )
            if response.status_code == 200:
                return response.json().get("data", {}).get("pipelines", [])
            return []
        except Exception as e:
            print(f"❌ 파이프라인 목록 조회 실패: {e}")
            return []

    def create_issue(self, project_id: str, title: str, description: str) -> bool:
        """이슈 생성 (수정 기록 보고용)"""
        try:
            data = {
                "project_id": project_id,
                "title": title,
                "description": description,
                "labels": ["auto-fix", "ci-cd"],
            }
            response = self.session.post(f"{self.base_url}/api/v1/issues", json=data)
            if response.status_code in [200, 201]:
                print(f"✅ 이슈 생성 완료: {title}")
                return True
            return False
        except Exception as e:
            print(f"❌ 이슈 생성 실패: {e}")
            return False

    def send_notification(
        self, project_id: str, message: str, channel: str = "general"
    ) -> bool:
        """알림 발송"""
        try:
            data = {
                "project_id": project_id,
                "message": message,
                "channel": channel,
                "type": "ci_cd_fix",
            }
            response = self.session.post(
                f"{self.base_url}/api/v1/notifications", json=data
            )
            return response.status_code in [200, 201]
        except Exception as e:
            print(f"❌ 알림 발송 실패: {e}")
            return False

    def backup_file(self, project_id: str, file_path: str) -> str:
        """파일 백업 (수정 전)"""
        try:
            content = self.get_file_content(project_id, file_path)
            if content:
                backup_path = f"{file_path}.backup"
                if self.update_file(project_id, backup_path, content):
                    return backup_path
            return ""
        except Exception as e:
            print(f"❌ 파일 백업 실패: {e}")
            return ""

    def validate_yaml_syntax(self, yaml_content: str) -> bool:
        """
        YAML 문법 검증"""
        try:
            import yaml

            yaml.safe_load(yaml_content)
            return True
        except yaml.YAMLError as e:
            print(f"❌ YAML 문법 오류: {e}")
            return False
        except ImportError:
            print("⚠️ PyYAML이 설치되지 않음 - YAML 검증 생략")
            return True

    def analyze_log_patterns(self, log_content: str) -> Dict[str, Any]:
        """로그 패턴 분석"""
        import re

        patterns = {
            "error_count": len(re.findall(r"(?i)error", log_content)),
            "warning_count": len(re.findall(r"(?i)warning", log_content)),
            "timeout_issues": len(re.findall(r"(?i)timeout|timed out", log_content)),
            "permission_issues": len(
                re.findall(r"(?i)permission denied|access denied", log_content)
            ),
            "network_issues": len(
                re.findall(r"(?i)network|dns|connection", log_content)
            ),
        }

        return patterns

    def generate_fix_report(self, project_id: str, fixes_applied: list) -> str:
        """수정 보고서 생성"""
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = f"""# CI/CD Auto-Fix Report

**Project**: {project_id}
**Timestamp**: {timestamp}
**Total Fixes Applied**: {len(fixes_applied)}

## Applied Fixes:

"""

        for i, fix in enumerate(fixes_applied, 1):
            report += f"{i}. {fix.replace('_', ' ').title()}\n"

        report += "\n---\n*Generated by Claude Code CI/CD Troubleshooter*\n"

        return report
