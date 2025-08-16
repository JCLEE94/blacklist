"""
반응형 디자인 및 실시간 기능 UI 테스트

모바일/데스크톱 반응형 디자인과 실시간 기능을 테스트합니다.
"""

import time
from playwright.async_api import expect

from .base_test_suite import BaseUITestSuite


class ResponsiveTestSuite(BaseUITestSuite):
    """반응형 디자인 테스트 스위트"""
    
    async def test_responsive_design(self):
        """반응형 디자인 테스트"""
        async def responsive_test():
            # 데스크톱 뷰포트 테스트
            await self.test_desktop_layout()
            
            # 모바일 뷰포트 테스트
            await self.test_mobile_layout()
            
            # 차트 반응형 확인
            await self.test_chart_responsive()
            
            # 테이블 반응형 확인
            await self.test_table_responsive()
        
        await self.execute_test_with_timing("responsive_design", responsive_test)
    
    async def test_desktop_layout(self):
        """데스크톱 레이아웃 테스트"""
        await self.page.set_viewport_size(self.config.DESKTOP_VIEWPORT)
        await self.page.goto(self.config.get_page_url("main"))
        
        # 데스크톱에서 사이드바/네비게이션 확인
        selectors = self.config.get_selectors("responsive")
        desktop_nav = self.page.locator(selectors["desktop_nav"])
        desktop_nav_visible = await desktop_nav.count() > 0 and await desktop_nav.first.is_visible()
        
        if not desktop_nav_visible:
            self.reporter.add_warning("데스크톱에서 네비게이션이 보이지 않음")
    
    async def test_mobile_layout(self):
        """모바일 레이아웃 테스트"""
        await self.page.set_viewport_size(self.config.MOBILE_VIEWPORT)
        await self.page.reload()
        
        selectors = self.config.get_selectors("responsive")
        
        # 모바일 햄버거 메뉴 확인
        mobile_menu_toggle = self.page.locator(selectors["mobile_menu_toggle"])
        if await mobile_menu_toggle.count() > 0:
            await mobile_menu_toggle.first.click()
            
            # 모바일 메뉴 표시 확인
            mobile_menu = self.page.locator(selectors["mobile_menu"])
            if await mobile_menu.count() > 0:
                try:
                    await expect(mobile_menu.first).to_be_visible(timeout=2000)
                except:
                    self.reporter.add_warning("모바일 메뉴가 제대로 표시되지 않음")
    
    async def test_chart_responsive(self):
        """차트 반응형 테스트"""
        chart_container = self.page.locator(".chart-container, #blacklist-chart")
        if await chart_container.count() > 0:
            viewport_width = self.config.MOBILE_VIEWPORT["width"]
            await self.check_responsive_element(".chart-container, #blacklist-chart", viewport_width)
    
    async def test_table_responsive(self):
        """테이블 반응형 테스트"""
        tables = self.page.locator("table")
        table_count = await tables.count()
        viewport_width = self.config.MOBILE_VIEWPORT["width"]
        
        if table_count > 0:
            for i in range(min(table_count, 3)):  # 최대 3개 테이블만 확인
                table = tables.nth(i)
                is_scrollable = await table.evaluate("""
                    el => el.scrollWidth > el.clientWidth
                """)
                
                if not is_scrollable:
                    await self.check_responsive_element(f"table:nth-of-type({i+1})", viewport_width)


class RealtimeTestSuite(BaseUITestSuite):
    """실시간 기능 테스트 스위트"""
    
    async def test_realtime_features(self):
        """실시간 기능 테스트"""
        async def realtime_test():
            await self.page.goto(self.config.get_page_url("main"))
            
            # 자동 새고침 설정 확인
            await self.test_auto_refresh_controls()
            
            # 실시간 데이터 업데이트 테스트
            await self.test_data_updates()
            
            # WebSocket 또는 SSE 연결 확인
            await self.test_realtime_connections()
        
        await self.execute_test_with_timing("realtime_features", realtime_test)
    
    async def test_auto_refresh_controls(self):
        """자동 새고침 제어 테스트"""
        selectors = self.config.get_selectors("realtime")
        auto_refresh_controls = selectors["auto_refresh_controls"]
        
        auto_refresh_found = await self.check_multiple_elements(auto_refresh_controls, "자동 새고침")
        
        if auto_refresh_found == 0:
            self.reporter.add_warning("자동 새고침 제어 요소를 찾을 수 없음")
    
    async def test_data_updates(self):
        """데이터 업데이트 테스트"""
        selectors = self.config.get_selectors("realtime")
        
        # 초기 통계 값 기록
        initial_stats = await self.capture_current_stats(selectors["stat_values"])
        
        # 새고침 트리거
        refresh_button = self.page.locator(selectors["refresh_button"])
        if await refresh_button.count() > 0:
            await refresh_button.first.click()
            
            # 로딩 상태 확인
            await self.page.wait_for_timeout(500)
            
            # 데이터 업데이트 확인 (최대 5초 대기)
            await self.verify_data_updates(initial_stats, selectors["stat_values"])
    
    async def capture_current_stats(self, stat_selector: str) -> dict:
        """현재 통계 값 수집"""
        initial_stats = {}
        stat_elements = self.page.locator(stat_selector)
        stat_count = await stat_elements.count()
        
        for i in range(min(stat_count, 5)):  # 최대 5개 통계만 확인
            stat = stat_elements.nth(i)
            value = await stat.text_content()
            initial_stats[f"stat_{i}"] = value
        
        return initial_stats
    
    async def verify_data_updates(self, initial_stats: dict, stat_selector: str):
        """데이터 업데이트 확인"""
        stat_elements = self.page.locator(stat_selector)
        stat_count = await stat_elements.count()
        
        for attempt in range(10):  # 0.5초씩 10번 = 5초
            await self.page.wait_for_timeout(500)
            
            current_stats = {}
            for i in range(min(stat_count, 5)):
                stat = stat_elements.nth(i)
                value = await stat.text_content()
                current_stats[f"stat_{i}"] = value
            
            # 통계가 업데이트되었는지 확인
            if current_stats != initial_stats:
                return
        
        self.reporter.add_warning("실시간 데이터 업데이트가 감지되지 않음")
    
    async def test_realtime_connections(self):
        """실시간 연결 테스트"""
        realtime_status = await self.page.evaluate("""
            () => {
                // WebSocket 연결 확인
                const hasWebSocket = window.WebSocket && window.location.protocol.includes('ws');
                
                // EventSource 확인
                const hasEventSource = window.EventSource;
                
                // 페이지에서 실시간 관련 JavaScript 확인
                const hasRealtimeCode = document.documentElement.innerHTML.includes('setInterval') ||
                                      document.documentElement.innerHTML.includes('setTimeout') ||
                                      document.documentElement.innerHTML.includes('WebSocket') ||
                                      document.documentElement.innerHTML.includes('EventSource');
                
                return {
                    hasWebSocket,
                    hasEventSource,
                    hasRealtimeCode
                };
            }
        """)
        
        if not any(realtime_status.values()):
            self.reporter.add_warning("실시간 기능 관련 코드를 찾을 수 없음")
