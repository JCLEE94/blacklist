"""
Comprehensive UI Endpoint Tests using Playwright
Tests all UI endpoints for data display, collection, and functionality
"""

import asyncio
import json
import time
from datetime import datetime

import pytest
from playwright.async_api import async_playwright


class TestUIEndpoints:
    """Test all UI endpoints and data display functionality"""

    BASE_URL = "http://localhost:32542"
    API_BASE = f"{BASE_URL}/api"

    @pytest.fixture(scope="class")
    async def browser_context(self):
        """Create browser context for testing"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            yield page
            await browser.close()

    async def test_health_endpoints(self, browser_context):
        """Test health check endpoints"""
        page = browser_context

        # Test basic health endpoint
        response = await page.goto(f"{self.BASE_URL}/health")
        assert response.status == 200
        health_data = await response.json()
        assert health_data["status"] == "healthy"
        assert "version" in health_data
        print(f"✅ Health check passed: {health_data}")

        # Test detailed API health
        response = await page.goto(f"{self.API_BASE}/health")
        assert response.status == 200
        api_health = await response.json()
        assert api_health["success"] is True
        assert api_health["data"]["service_status"] == "running"
        print(f"✅ API health check passed: {api_health}")

    async def test_collection_endpoints(self, browser_context):
        """Test collection status and control endpoints"""
        page = browser_context

        # Test collection status
        response = await page.goto(f"{self.API_BASE}/collection/status")
        assert response.status == 200
        status_data = await response.json()
        assert "collection_enabled" in status_data
        assert "sources" in status_data
        print(f"✅ Collection status: {status_data['collection_enabled']}")

        # Test enabling collection
        response = await page.request.post(
            f"{self.API_BASE}/collection/enable",
            data=json.dumps({"clear_data": False}),
            headers={"Content-Type": "application/json"},
        )
        if response.status == 200:
            enable_data = await response.json()
            print(f"✅ Collection enabled: {enable_data}")

    async def test_blacklist_data_endpoints(self, browser_context):
        """Test blacklist data retrieval endpoints"""
        page = browser_context

        # Test active blacklist IPs
        response = await page.goto(f"{self.API_BASE}/blacklist/active")
        assert response.status == 200
        active_ips = await response.text()
        print(f"✅ Active IPs retrieved: {len(active_ips.splitlines())} IPs")

        # Test FortiGate format endpoint
        response = await page.goto(f"{self.API_BASE}/fortigate")
        assert response.status == 200
        fortigate_data = await response.text()
        print(f"✅ FortiGate format data retrieved")

        # Test enhanced blacklist endpoint
        response = await page.goto(f"{self.API_BASE}/v2/blacklist/enhanced")
        if response.status == 200:
            enhanced_data = await response.json()
            print(f"✅ Enhanced blacklist data: {len(enhanced_data.get('data', []))} entries")

    async def test_analytics_endpoints(self, browser_context):
        """Test analytics and statistics endpoints"""
        page = browser_context

        # Test trends endpoint
        response = await page.goto(f"{self.API_BASE}/v2/analytics/trends")
        if response.status == 200:
            trends_data = await response.json()
            print(f"✅ Trends data retrieved: {trends_data.get('success')}")

        # Test summary endpoint
        response = await page.goto(f"{self.API_BASE}/v2/analytics/summary")
        if response.status == 200:
            summary_data = await response.json()
            print(f"✅ Analytics summary retrieved")

        # Test sources status
        response = await page.goto(f"{self.API_BASE}/v2/sources/status")
        if response.status == 200:
            sources_data = await response.json()
            print(f"✅ Sources status: {sources_data}")

    async def test_ui_pages(self, browser_context):
        """Test UI pages load correctly"""
        page = browser_context

        # Test main dashboard
        await page.goto(f"{self.BASE_URL}/")
        title = await page.title()
        print(f"✅ Main dashboard loaded: {title}")

        # Check for key UI elements
        await page.wait_for_selector("body", timeout=5000)
        
        # Test if dashboard contains expected elements
        has_content = await page.evaluate(
            """() => {
                return document.body.innerText.length > 0;
            }"""
        )
        assert has_content, "Dashboard should have content"

    async def test_collection_trigger_endpoints(self, browser_context):
        """Test manual collection trigger endpoints"""
        page = browser_context

        # Test REGTECH collection trigger
        response = await page.request.post(
            f"{self.API_BASE}/collection/regtech/trigger",
            headers={"Content-Type": "application/json"},
        )
        if response.status == 200:
            regtech_result = await response.json()
            print(f"✅ REGTECH collection triggered: {regtech_result}")
        else:
            print(f"⚠️ REGTECH trigger status: {response.status}")

        # Test SECUDIUM collection trigger
        response = await page.request.post(
            f"{self.API_BASE}/collection/secudium/trigger",
            headers={"Content-Type": "application/json"},
        )
        if response.status == 200:
            secudium_result = await response.json()
            print(f"✅ SECUDIUM collection triggered: {secudium_result}")
        else:
            print(f"⚠️ SECUDIUM trigger status: {response.status}")

    async def test_monitoring_endpoints(self, browser_context):
        """Test monitoring and metrics endpoints"""
        page = browser_context

        # Test metrics endpoint
        response = await page.goto(f"{self.BASE_URL}/metrics")
        if response.status == 200:
            metrics_text = await response.text()
            assert "blacklist_" in metrics_text or "http_" in metrics_text
            print(f"✅ Prometheus metrics available")

        # Test monitoring dashboard
        response = await page.goto(f"{self.BASE_URL}/monitoring/dashboard")
        if response.status == 200:
            dashboard_data = await response.text()
            print(f"✅ Monitoring dashboard accessible")


async def run_ui_tests():
    """Run all UI endpoint tests"""
    print("\n" + "="*60)
    print("🧪 Starting Comprehensive UI Endpoint Tests")
    print("="*60 + "\n")

    test_suite = TestUIEndpoints()
    
    # Create browser context
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Run all test methods
            print("1️⃣ Testing Health Endpoints...")
            await test_suite.test_health_endpoints(page)
            
            print("\n2️⃣ Testing Collection Endpoints...")
            await test_suite.test_collection_endpoints(page)
            
            print("\n3️⃣ Testing Blacklist Data Endpoints...")
            await test_suite.test_blacklist_data_endpoints(page)
            
            print("\n4️⃣ Testing Analytics Endpoints...")
            await test_suite.test_analytics_endpoints(page)
            
            print("\n5️⃣ Testing UI Pages...")
            await test_suite.test_ui_pages(page)
            
            print("\n6️⃣ Testing Collection Triggers...")
            await test_suite.test_collection_trigger_endpoints(page)
            
            print("\n7️⃣ Testing Monitoring Endpoints...")
            await test_suite.test_monitoring_endpoints(page)

            print("\n" + "="*60)
            print("✅ All UI Endpoint Tests Completed Successfully!")
            print("="*60)

        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            raise
        finally:
            await browser.close()


if __name__ == "__main__":
    # Run the async tests
    asyncio.run(run_ui_tests())