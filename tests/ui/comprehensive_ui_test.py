"""
포괄적인 UI 기능 테스트 - blacklist.jclee.me 웹사이트
Playwright 기반 브라우저 자동화 테스트 오케스트레이터

모듈화된 UI 테스트 스위트를 통합하여 실행합니다.
"""

import asyncio
import pytest
from playwright.async_api import async_playwright, BrowserContext, Page

from .test_config import UITestConfig
from .test_reporter import UITestReporter
from .dashboard_tests import DashboardTestSuite
from .collection_tests import CollectionTestSuite
from .responsive_tests import ResponsiveTestSuite, RealtimeTestSuite
from .api_tests import APITestSuite


class ComprehensiveUITestOrchestrator:
    """포괄적 UI 테스트 오케스트레이터"""
    
    def __init__(self, page: Page, reporter: UITestReporter):
        self.page = page
        self.reporter = reporter
        self.config = UITestConfig()
        
        # 테스트 스위트 초기화
        self.dashboard_suite = DashboardTestSuite(page, reporter)
        self.collection_suite = CollectionTestSuite(page, reporter)
        self.responsive_suite = ResponsiveTestSuite(page, reporter)
        self.realtime_suite = RealtimeTestSuite(page, reporter)
        self.api_suite = APITestSuite(page, reporter)
    
    async def run_all_tests(self):
        """모든 UI 테스트 실행"""
        test_functions = [
            self.dashboard_suite.test_main_dashboard,
            self.dashboard_suite.test_statistics_page,
            self.collection_suite.test_collection_management,
            self.collection_suite.test_api_documentation,
            self.responsive_suite.test_responsive_design,
            self.realtime_suite.test_realtime_features,
            self.api_suite.test_api_endpoints
        ]
        
        for test_func in test_functions:
            try:
                await test_func()
            except Exception as e:
                self.reporter.add_error(f"테스트 {test_func.__name__} 실행 중 오류: {str(e)}")
    
    async def run_performance_tests(self):
        """성능 테스트만 실행"""
        performance_tests = [
            self.api_suite.test_api_performance,
            self.api_suite.test_api_health_checks,
        ]
        
        for test_func in performance_tests:
            try:
                await test_func()
            except Exception as e:
                self.reporter.add_error(f"성능 테스트 {test_func.__name__} 실행 중 오류: {str(e)}")
    
    async def run_core_tests(self):
        """핵심 기능만 테스트"""
        core_tests = [
            self.dashboard_suite.test_main_dashboard,
            self.collection_suite.test_collection_management,
            self.api_suite.test_api_health_checks,
        ]
        
        for test_func in core_tests:
            try:
                await test_func()
            except Exception as e:
                self.reporter.add_error(f"핵심 테스트 {test_func.__name__} 실행 중 오류: {str(e)}")


@pytest.fixture
def ui_reporter():
    """UI 테스트 리포터 픽스처"""
    return UITestReporter()


@pytest.mark.asyncio
async def test_comprehensive_ui_functionality(ui_reporter):
    """포괄적 UI 기능 테스트 실행"""
    async with async_playwright() as p:
        # 브라우저 컨텍스트 설정
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport=UITestConfig.DESKTOP_VIEWPORT,
            user_agent=UITestConfig.BROWSER_CONFIG["user_agent"]
        )
        
        page = await context.new_page()
        
        # 네트워크 및 콘솔 에러 모니터링
        await setup_error_monitoring(page, ui_reporter)
        
        try:
            # 테스트 오케스트레이터 실행
            orchestrator = ComprehensiveUITestOrchestrator(page, ui_reporter)
            await orchestrator.run_all_tests()
            
        finally:
            await browser.close()
    
    # 테스트 결과 출력
    print(ui_reporter.generate_report())
    
    # 테스트 실패가 있으면 assertion error
    if ui_reporter.has_failures():
        pytest.fail(f"UI 테스트 실패: {len(ui_reporter.results['failed_tests'])}개 테스트 실패")


@pytest.mark.asyncio
async def test_performance_only(ui_reporter):
    """성능 테스트만 실행"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport=UITestConfig.DESKTOP_VIEWPORT)
        page = await context.new_page()
        
        try:
            orchestrator = ComprehensiveUITestOrchestrator(page, ui_reporter)
            await orchestrator.run_performance_tests()
        finally:
            await browser.close()
    
    print(ui_reporter.generate_report())


@pytest.mark.asyncio
async def test_core_functionality_only(ui_reporter):
    """핵심 기능만 테스트"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport=UITestConfig.DESKTOP_VIEWPORT)
        page = await context.new_page()
        
        try:
            orchestrator = ComprehensiveUITestOrchestrator(page, ui_reporter)
            await orchestrator.run_core_tests()
        finally:
            await browser.close()
    
    print(ui_reporter.generate_report())


async def setup_error_monitoring(page: Page, reporter: UITestReporter):
    """네트워크 및 콘솔 에러 모니터링 설정"""
    # 네트워크 에러 리스닝
    network_errors = []
    
    def handle_response(response):
        if response.status >= 400:
            network_errors.append({
                "url": response.url,
                "status": response.status,
                "method": response.request.method
            })
    
    page.on("response", handle_response)
    
    # 콘솔 에러 리스닝
    console_errors = []
    
    def handle_console(msg):
        if msg.type == "error":
            console_errors.append(msg.text)
    
    page.on("console", handle_console)
    
    # 에러 보고 함수
    async def report_errors():
        if network_errors:
            for error in network_errors[:10]:  # 최대 10개만
                reporter.add_error(
                    f"네트워크 에러: {error['method']} {error['url']} -> {error['status']}"
                )
        
        if console_errors:
            for error in console_errors[:10]:  # 최대 10개만
                reporter.add_error(f"콘솔 에러: {error}")
    
    return report_errors


if __name__ == "__main__":
    """독립 실행을 위한 코드"""
    async def run_standalone_test():
        """독립 실행 테스트"""
        reporter = UITestReporter()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # 브라우저 표시
            context = await browser.new_context(viewport=UITestConfig.DESKTOP_VIEWPORT)
            page = await context.new_page()
            
            orchestrator = ComprehensiveUITestOrchestrator(page, reporter)
            
            try:
                print("🚀 포괄적 UI 테스트 시작...")
                await orchestrator.run_all_tests()
                print(reporter.generate_report())
                
            except Exception as e:
                print(f"❌ 테스트 실행 중 오류: {e}")
                print(reporter.generate_report())
            
            finally:
                await browser.close()
    
    # 실행
    asyncio.run(run_standalone_test())
