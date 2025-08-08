#!/usr/bin/env python3
"""
CI/CD 자동 트러블슈팅 시스템 - 모듈화된 버전
Claude Code v8.4.0 - 완전 자동화된 파이프라인 문제 해결

이 파일은 이제 모듈화된 구조로 리팩토링되었습니다.
실제 구현은 다음 모듈들로 분리되어 있습니다:
- cicd_troubleshooter_core: 메인 오케스트레이션 로직
- cicd_error_patterns: 에러 패턴 정의 및 매칭
- cicd_fix_strategies: 에러별 수정 전략
- cicd_utils: 파일 및 API 유틸리티
"""

from .cicd_error_patterns import ErrorPatternManager
from .cicd_fix_strategies import FixStrategyManager
# 모듈화된 구조에서 가져오기
from .cicd_troubleshooter_core import CICDTroubleshooter

# 하위 호환성을 위한 aliases
CICDTroubleshooterCore = CICDTroubleshooter


# 편의를 위한 팩토리 함수
def create_troubleshooter(gateway_url=None, api_key=None):
    """트러블슈터 인스턴스 생성 (팩토리 함수)"""
    return CICDTroubleshooter(gateway_url=gateway_url, api_key=api_key)


def create_error_manager():
    """에러 패턴 매니저 생성"""
    return ErrorPatternManager()


def create_fix_manager():
    """수정 전략 매니저 생성"""
    return FixStrategyManager()


def analyze_pipeline_errors(
    project_id: str, pipeline_id: str, gateway_url=None, api_key=None
):
    """파이프라인 에러 분석 단축 함수"""
    troubleshooter = create_troubleshooter(gateway_url, api_key)
    return troubleshooter.monitor_and_fix_pipeline(project_id, pipeline_id)


# 하위 호환성을 위한 레거시 함수들 (deprecated)
def main():
    """테스트용 메인 함수"""
    troubleshooter = create_troubleshooter()

    # 예시: blacklist 프로젝트의 파이프라인 트러블슈팅
    project_id = "blacklist"
    pipeline_id = "12345"  # 실제 파이프라인 ID로 교체

    result = troubleshooter.monitor_and_fix_pipeline(project_id, pipeline_id)
    print(f"🎯 트러블슈팅 결과: {result}")


if __name__ == "__main__":
    main()
