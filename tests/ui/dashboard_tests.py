"""
대시보드 및 통계 페이지 UI 테스트

메인 대시보드와 통계 페이지의 UI 기능을 테스트합니다.
"""

from playwright.async_api import expect

from .base_test_suite import BaseUITestSuite


class DashboardTestSuite(BaseUITestSuite):
    """대시보드 테스트 스위트"""

    async def test_main_dashboard(self):
        """메인 대시보드 테스트"""

        async def dashboard_test():
            # 페이지 로딩 성능 측정
            await self.wait_for_page_load(self.config.get_page_url("main"))

            # 페이지 제목 확인
            await expect(self.page).to_have_title("Blacklist Management System")

            # 핵심 요소들 존재 확인
            selectors = self.config.get_selectors("main_dashboard")

            core_elements = [
                selectors["title"],
                selectors["stats_grid"],
                selectors["chart_container"],
                selectors["chart"],
                selectors["refresh_controls"],
            ]

            for selector in core_elements:
                await self.check_element_visibility(selector)

            # 통계 카드 데이터 확인
            stats_cards = self.page.locator(selectors["stat_cards"])
            count = await stats_cards.count()
            if count < 4:
                self.reporter.add_warning(f"통계 카드 수가 예상보다 적음: {count}/4")

            # 차트 렌더링 확인
            await self.test_chart_rendering(selectors["chart"])

            # 자동 새고침 기능 테스트
            await self.test_refresh_functionality()

        await self.execute_test_with_timing("main_dashboard", dashboard_test)

    async def test_refresh_functionality(self):
        """새고침 기능 테스트"""
        refresh_button = self.page.locator("button:has-text('새로고침')")
        if await refresh_button.count() > 0:
            await refresh_button.click()
            await self.check_loading_indicators()

    async def test_statistics_page(self):
        """통계 페이지 테스트"""

        async def statistics_test():
            await self.page.goto(self.config.get_page_url("statistics"))

            # 페이지 로딩 확인
            selectors = self.config.get_selectors("statistics")
            await expect(self.page.locator("h1")).to_contain_text("상세 통계")

            # 통계 차트들 확인
            chart_selectors = [
                selectors.get("trend_chart", ".trend-chart"),
                selectors.get("source_distribution", ".source-distribution"),
                selectors.get("geo_analysis", ".geo-analysis"),
                selectors.get("threat_level_chart", ".threat-level-chart"),
            ]

            found_charts = await self.check_multiple_elements(chart_selectors, "통계 차트")

            # 필터 기능 테스트
            await self.test_filter_functionality()

            # 데이터 테이블 확인
            await self.test_data_table()

        await self.execute_test_with_timing("statistics_page", statistics_test)

    async def test_filter_functionality(self):
        """필터 기능 테스트"""
        date_filter = self.page.locator("select[name='date_range'], input[type='date']")
        if await date_filter.count() > 0:
            await date_filter.first.click()
            await self.page.wait_for_timeout(1000)

    async def test_data_table(self):
        """데이터 테이블 테스트"""
        data_table = self.page.locator("table, .data-grid")
        if await data_table.count() > 0:
            await expect(data_table.first).to_be_visible()

            # 테이블 행 수 확인
            rows = self.page.locator("tr, .data-row")
            row_count = await rows.count()
            if row_count < 2:  # 헤더 + 최소 1행
                self.reporter.add_warning("통계 데이터 테이블에 데이터가 부족함")
