"""
수집 관리 및 API 문서 페이지 UI 테스트

수집 상태 관리와 API 문서 페이지의 UI 기능을 테스트합니다.
"""

from playwright.async_api import expect

from .base_test_suite import BaseUITestSuite


class CollectionTestSuite(BaseUITestSuite):
    """수집 관리 테스트 스위트"""
    
    async def test_collection_management(self):
        """수집 상태 관리 페이지 테스트"""
        async def collection_test():
            await self.page.goto(self.config.get_page_url("collection"))
            
            # 페이지 로딩 확인
            selectors = self.config.get_selectors("collection")
            await expect(self.page.locator("h1")).to_contain_text("수집 관리")
            
            # 수집 상태 표시 확인
            status_indicators = [
                selectors.get("collection_status", ".collection-status"),
                selectors.get("regtech_status", ".regtech-status"),
                selectors.get("secudium_status", ".secudium-status")
            ]
            
            await self.check_multiple_elements(status_indicators, "수집 상태")
            
            # 수집 제어 버튼들 확인
            await self.test_collection_controls()
            
            # 수집 로그 확인
            await self.test_collection_logs(selectors)
            
            # 수집 통계 확인
            await self.test_collection_stats()
        
        await self.execute_test_with_timing("collection_management", collection_test)
    
    async def test_collection_controls(self):
        """수집 제어 버튼 테스트"""
        control_buttons = [
            "button:has-text('수집 시작')",
            "button:has-text('수집 중지')",
            "button:has-text('수동 수집')"
        ]
        
        visible_buttons = await self.check_multiple_elements(control_buttons, "수집 제어")
        
        if visible_buttons == 0:
            self.reporter.add_warning("수집 제어 버튼이 발견되지 않음")
    
    async def test_collection_logs(self, selectors):
        """수집 로그 테스트"""
        log_container = self.page.locator(selectors.get("logs_container", ".collection-logs"))
        if await log_container.count() > 0:
            await expect(log_container.first).to_be_visible()
    
    async def test_collection_stats(self):
        """수집 통계 테스트"""
        stats_section = self.page.locator(".collection-stats, .metrics-section")
        if await stats_section.count() > 0:
            await expect(stats_section.first).to_be_visible()
    
    async def test_api_documentation(self):
        """수집 관리 API 문서 페이지 테스트"""
        async def api_docs_test():
            await self.page.goto(self.config.get_page_url("api_docs"))
            
            # API 문서 페이지 확인
            page_indicators = [
                "h1:has-text('API')",
                ".api-endpoint",
                ".endpoint-list",
                "code"
            ]
            
            found_indicators = await self.check_multiple_elements(page_indicators, "API 문서")
            
            if found_indicators < 2:
                self.reporter.add_warning("API 문서 페이지의 필수 요소가 부족함")
            
            # API 엔드포인트 링크 테스트
            await self.test_api_endpoint_links()
        
        await self.execute_test_with_timing("api_documentation", api_docs_test)
    
    async def test_api_endpoint_links(self):
        """수집 관리 API 엔드포인트 링크 테스트"""
        api_links = self.page.locator("a[href*='/api/']")
        link_count = await api_links.count()
        
        if link_count > 0:
            # 첫 번째 API 링크 테스트
            first_link = api_links.first
            href = await first_link.get_attribute("href")
            if href:
                # API 엔드포인트 직접 호출 테스트
                try:
                    response = await self.page.evaluate(f"""
                        fetch('{href}').then(r => r.status)
                    """)
                    if response not in [200, 401, 403]:  # 인증이 필요할 수 있음
                        self.reporter.add_warning(f"API 엔드포인트 {href} 응답 상태 이상: {response}")
                except Exception as e:
                    self.reporter.add_warning(f"API 엔드포인트 테스트 실패: {str(e)}")
