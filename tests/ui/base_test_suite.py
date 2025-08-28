"""
UI 테스트 기본 스위트

기본적인 UI 테스트 기능을 제공하는 기본 클래스입니다.
"""

import time
from typing import Any, Callable

from playwright.async_api import Page, expect

from .test_config import UITestConfig
from .test_reporter import UITestReporter


class BaseUITestSuite:
    """기본 UI 테스트 스위트"""

    def __init__(self, page: Page, reporter: UITestReporter):
        self.page = page
        self.reporter = reporter
        self.config = UITestConfig()

    async def measure_performance(
        self, action_name: str, action_func: Callable, threshold: float
    ) -> Any:
        """성능 측정 데코레이터"""
        start_time = time.time()
        try:
            result = await action_func()
            duration = (time.time() - start_time) * 1000  # ms
            self.reporter.add_performance_metric(action_name, duration, threshold)
            return result
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.reporter.add_error(
                f"Performance test failed for {action_name}: {str(e)}"
            )
            raise

    async def check_element_visibility(
        self, selector: str, timeout: int = 5000, required: bool = True
    ) -> bool:
        """요소 가시성 확인"""
        try:
            element = self.page.locator(selector)
            await expect(element).to_be_visible(timeout=timeout)
            return True
        except Exception as e:
            if required:
                self.reporter.add_error(
                    f"Required element not visible: {selector} - {str(e)}"
                )
                raise
            else:
                self.reporter.add_warning(f"Optional element not visible: {selector}")
                return False

    async def check_multiple_elements(self, selectors: list, section_name: str) -> int:
        """여러 요소 존재 확인"""
        found_count = 0

        for selector in selectors:
            element = self.page.locator(selector)
            if await element.count() > 0:
                try:
                    await expect(element.first).to_be_visible(timeout=3000)
                    found_count += 1
                except BaseException:
                    pass

        if found_count == 0:
            self.reporter.add_warning(f"{section_name} 섹션에서 필수 요소를 찾을 수 없음")

        return found_count

    async def execute_test_with_timing(
        self, test_name: str, test_func: Callable
    ) -> None:
        """테스트 실행 및 시간 측정"""
        start_time = time.time()

        try:
            await test_func()
            duration = (time.time() - start_time) * 1000
            self.reporter.add_result(test_name, "PASS", duration)
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.reporter.add_result(test_name, "FAIL", duration, {"error": str(e)})
            raise

    async def wait_for_page_load(self, url: str) -> None:
        """페이지 로드 대기 및 성능 측정"""
        await self.measure_performance(
            "page_load",
            lambda: self.page.goto(url),
            self.config.PERFORMANCE_THRESHOLDS["page_load"],
        )

    async def check_loading_indicators(self) -> None:
        """로딩 인디케이터 확인"""
        loading_selectors = self.config.get_selectors("realtime")["loading_indicator"]
        loading_indicator = self.page.locator(loading_selectors)

        if await loading_indicator.count() > 0:
            try:
                await expect(loading_indicator.first).to_be_visible(timeout=1000)
                await expect(loading_indicator.first).to_be_hidden(timeout=5000)
            except BaseException:
                self.reporter.add_warning("로딩 인디케이터 동작 이상")

    async def test_chart_rendering(self, chart_selector: str) -> None:
        """차트 렌더링 테스트"""
        await self.measure_performance(
            "chart_render",
            lambda: self.page.wait_for_selector(
                f"{chart_selector} canvas", timeout=3000
            ),
            self.config.PERFORMANCE_THRESHOLDS["chart_render"],
        )

    async def click_and_wait(self, selector: str, wait_time: int = 1000) -> None:
        """클릭 후 대기"""
        element = self.page.locator(selector)
        if await element.count() > 0:
            await element.first.click()
            await self.page.wait_for_timeout(wait_time)

    async def check_responsive_element(self, selector: str, max_width: int) -> bool:
        """반응형 요소 확인"""
        element = self.page.locator(selector)
        if await element.count() > 0:
            element_width = await element.first.evaluate("el => el.offsetWidth")
            if element_width > max_width:
                self.reporter.add_warning(
                    f"Element {selector} overflows on mobile: {element_width}px > {max_width}px"
                )
                return False
        return True
