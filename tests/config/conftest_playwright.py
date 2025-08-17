"""
Playwright 전용 conftest 설정
UI 테스트를 위한 브라우저 설정 및 픽스처
"""

import pytest
from playwright.sync_api import Browser, BrowserContext, Page


@pytest.fixture(scope="session")
def browser_context_args():
    """브라우저 컨텍스트 인수"""
    return {
        "viewport": {"width": 1920, "height": 1080},
        "ignore_https_errors": True,
        "extra_http_headers": {"User-Agent": "BlacklistUITest/1.0"},
    }


@pytest.fixture
def context(browser: Browser, browser_context_args):
    """브라우저 컨텍스트"""
    context = browser.new_context(**browser_context_args)
    yield context
    context.close()


@pytest.fixture
def page(context: BrowserContext):
    """페이지"""
    page = context.new_page()
    yield page
    page.close()
