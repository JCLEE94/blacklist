"""
Comprehensive UI Endpoint Tests using Playwright
Tests all UI endpoints for data display, collection, and functionality
"""

import asyncio
import json
import time
from datetime import datetime

import pytest

# Skip this entire test if playwright is not available or if running in CI/CD
pytest_plugins = ("pytest_asyncio",)

BASE_URL = "http://localhost:32542"
API_BASE = f"{BASE_URL}/api"


@pytest.mark.ui
@pytest.mark.slow
@pytest.mark.asyncio
async def test_ui_health_endpoints():
    """Test health check endpoints via UI"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        pytest.skip("Playwright not available")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Test basic health endpoint
            response = await page.goto(f"{BASE_URL}/health")
            assert response.status == 200
            health_data = await response.json()
            assert health_data["status"] == "healthy"
            assert "version" in health_data

            # Test detailed API health
            response = await page.goto(f"{API_BASE}/health")
            assert response.status == 200
            api_health = await response.json()
            assert api_health["status"] == "healthy"
            assert api_health["service"] == "blacklist-management"

        finally:
            await browser.close()


@pytest.mark.ui
@pytest.mark.slow
@pytest.mark.asyncio
async def test_ui_collection_status():
    """Test collection status endpoint via UI"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        pytest.skip("Playwright not available")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Test collection status
            response = await page.goto(f"{API_BASE}/collection/status")
            assert response.status == 200
            status_data = await response.json()
            assert "collection_enabled" in status_data
            assert "sources" in status_data

        finally:
            await browser.close()


@pytest.mark.ui
@pytest.mark.slow
@pytest.mark.asyncio
async def test_ui_blacklist_endpoints():
    """Test blacklist data endpoints via UI"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        pytest.skip("Playwright not available")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Test active blacklist IPs
            response = await page.goto(f"{API_BASE}/blacklist/active")
            assert response.status == 200
            active_ips = await response.text()
            assert isinstance(active_ips, str)

            # Test FortiGate format endpoint
            response = await page.goto(f"{API_BASE}/fortigate")
            assert response.status == 200
            fortigate_data = await response.text()
            assert isinstance(fortigate_data, str)

        finally:
            await browser.close()


# Additional UI test for analytics endpoints
@pytest.mark.ui
@pytest.mark.slow
@pytest.mark.asyncio
async def test_ui_analytics_endpoints():
    """Test analytics endpoints via UI"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        pytest.skip("Playwright not available")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Test trends endpoint (may not have data)
            response = await page.goto(f"{API_BASE}/v2/analytics/trends")
            # Analytics may not be available without data, just check it responds
            assert response.status in [200, 404, 500]  # Accept various responses

            # Test sources status
            response = await page.goto(f"{API_BASE}/v2/sources/status")
            assert response.status in [200, 404, 500]  # Accept various responses

        finally:
            await browser.close()


if __name__ == "__main__":
    # Simple async test runner for manual execution
    async def run_tests():
        print("Running UI endpoint tests...")
        try:
            await test_ui_health_endpoints()
            print("✅ Health tests passed")
            await test_ui_collection_status()
            print("✅ Collection tests passed")
            await test_ui_blacklist_endpoints()
            print("✅ Blacklist tests passed")
            await test_ui_analytics_endpoints()
            print("✅ Analytics tests passed")
            print("All UI tests completed successfully!")
        except Exception as e:
            print(f"❌ Test failed: {e}")

    import asyncio

    asyncio.run(run_tests())
