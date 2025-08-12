#!/usr/bin/env python3
"""
CI/CD 트러블슈터 코어 모듈
Claude Code v8.4.0 - 메인 오케스트레이션 로직
"""

from typing import Any
from typing import Dict
from typing import List

import requests

from .cicd_error_patterns import ErrorPatternManager
from .cicd_fix_strategies import FixStrategyManager
from .cicd_utils import CICDUtils


class CICDTroubleshooter:
    """CI/CD 파이프라인 자동 트러블슈팅 및 복구 - 코어 클래스"""

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

        # 의존성 초기화
        self.error_manager = ErrorPatternManager()
        self.fix_manager = FixStrategyManager()
        self.utils = CICDUtils(self.session, self.base_url)

    def monitor_and_fix_pipeline(
        self, project_id: str, pipeline_id: str
    ) -> Dict[str, Any]:
        """파이프라인 모니터링 및 자동 수정 - 메인 오케스트레이션"""
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
            retry_result = self.utils.retry_pipeline(project_id, pipeline_id)

            return {
                "status": "fixed_and_retried",
                "fixes_applied": fixes_applied,
                "retry_result": retry_result,
            }
        else:
            return {
                "status": "no_fixes_available",
                "message": "자동 수정할 수 있는 문제를 찾지 못함",
            }

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
        """작업 분석 및 자동 수정 - 에러 패턴 매칭 및 수정 적용"""
        job_name = job.get("name", "unknown")
        job_trace = job.get("trace", "")

        print(f"🔍 분석 중: {job_name}")

        fixes_applied = []

        # 에러 패턴 매칭 및 수정
        error_patterns = self.error_manager.get_error_patterns()

        for error_type, error_config in error_patterns.items():
            for pattern in error_config["patterns"]:
                if pattern.lower() in job_trace.lower():
                    print(f"🎯 감지된 문제: {error_type} - {pattern}")

                    try:
                        # 수정 전략 적용
                        fix_result = self.fix_manager.apply_fix(
                            error_type, project_id, job_trace, self.utils
                        )
                        if fix_result:
                            fixes_applied.append(f"{error_type}_fix")
                            print(f"✅ 수정 완료: {error_type}")
                        else:
                            print(f"❌ 수정 실패: {error_type}")
                    except Exception as e:
                        print(f"❌ 수정 중 오류: {error_type} - {e}")

                    break  # 첫 번째 매칭된 패턴만 처리

        return fixes_applied


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
