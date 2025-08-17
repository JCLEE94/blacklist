"""
포괄적인 UI 기능 테스트 - blacklist.jclee.me 웹사이트
Playwright 기반 브라우저 자동화 테스트

이 파일은 모듈화된 UI 테스트의 메인 진입점입니다.
실제 테스트 구현은 tests/ui/ 모듈에 분산되어 있습니다.

테스트 영역:
1. 메인 대시보드 (/) - 데이터 로딩, 차트, 통계
2. 통계 페이지 (/statistics) - 상세 분석
3. 수집 상태 페이지 (/collection) - 관리 기능
4. API 문서 페이지 (/api-docs) - 문서 확인
5. 실시간 대시보드 - 자동 새고침
6. 반응형 디자인 - 모바일/데스크톱
7. API 엔드포인트 상태 확인
"""

import pytest

# Import modular UI test components
try:
    from .ui import UITestConfig, UITestReporter
    from .ui.api_tests import APITestSuite
    from .ui.collection_tests import CollectionTestSuite
    from .ui.comprehensive_ui_test import ComprehensiveUITestOrchestrator
    from .ui.dashboard_tests import DashboardTestSuite
    from .ui.responsive_tests import ResponsiveTestSuite
except ImportError:
    # Fallback for direct execution
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), "ui"))

    from api_tests import APITestSuite
    from collection_tests import CollectionTestSuite
    from comprehensive_ui_test import ComprehensiveUITestOrchestrator
    from dashboard_tests import DashboardTestSuite
    from responsive_tests import ResponsiveTestSuite
    from test_config import UITestConfig
    from test_reporter import UITestReporter


@pytest.fixture
def ui_config():
    """UI test configuration fixture"""
    return UITestConfig()


@pytest.fixture
def ui_reporter():
    """UI test reporter fixture"""
    return UITestReporter()


@pytest.mark.ui
@pytest.mark.slow
@pytest.mark.skip(reason="UI tests require Playwright setup and running server - skipping in CI/CD")
class TestComprehensiveUI:
    """Comprehensive UI test orchestration - DISABLED for CI/CD"""

    def test_full_ui_suite(self, ui_config, ui_reporter):
        """Run complete UI test suite - DISABLED"""
        pytest.skip("UI tests require Playwright and running server")

    def test_dashboard_functionality(self, ui_config, ui_reporter):
        """Test dashboard functionality - DISABLED"""
        pytest.skip("UI tests require Playwright and running server")

    def test_api_endpoints(self, ui_config, ui_reporter):
        """Test API endpoint responses - DISABLED"""
        pytest.skip("UI tests require Playwright and running server")

    def test_collection_interface(self, ui_config, ui_reporter):
        """Test collection management interface - DISABLED"""
        pytest.skip("UI tests require Playwright and running server")

    def test_responsive_design(self, ui_config, ui_reporter):
        """Test responsive design across viewports - DISABLED"""
        pytest.skip("UI tests require Playwright and running server")


@pytest.mark.ui
@pytest.mark.integration
@pytest.mark.skip(reason="UI integration tests require Playwright setup - skipping in CI/CD")
def test_ui_suite_integration(ui_config, ui_reporter):
    """Integration test for UI suite components - DISABLED"""
    pytest.skip("UI integration tests require Playwright setup")


if __name__ == "__main__":
    # Direct execution support
    pytest.main([__file__, "-v", "--tb=short"])
