"""
UI 테스트 설정 및 기본 구성

UI 테스트에 필요한 기본 설정, 상수, 뷰포트 구성 등을 제공합니다.
"""

from typing import Any
from typing import Dict


class UITestConfig:
    """UI 테스트 설정"""

    BASE_URL = "http://localhost:32542"
    MOBILE_VIEWPORT = {"width": 375, "height": 667}
    DESKTOP_VIEWPORT = {"width": 1920, "height": 1080}
    PERFORMANCE_THRESHOLDS = {
        "page_load": 5000,  # 5초
        "api_response": 2000,  # 2초
        "chart_render": 3000,  # 3초
    }

    # 브라우저 설정
    BROWSER_CONFIG = {
        "headless": True,
        "user_agent": "Mozilla/5.0 (compatible; BlacklistUITest/1.0)",
        "timeout": 30000,  # 30초
    }

    # 테스트 대상 페이지 경로
    TEST_PAGES = {
        "main": "/",
        "statistics": "/statistics",
        "collection": "/collection",
        "api_docs": "/api-docs",
    }

    # 주요 API 엔드포인트
    API_ENDPOINTS = [
        "/health",
        "/api/health",
        "/api/blacklist/active",
        "/api/fortigate",
        "/api/collection/status",
        "/api/v2/analytics/summary",
        "/api/v2/sources/status",
    ]

    # UI 요소 선택자
    SELECTORS = {
        "main_dashboard": {
            "title": "h1:has-text('실시간 블랙리스트 현황')",
            "stats_grid": ".stats-grid",
            "chart_container": ".chart-container",
            "chart": "#blacklist-chart",
            "refresh_controls": ".refresh-controls",
            "stat_cards": ".stat-card",
        },
        "statistics": {
            "title": "h1:has-text('상세 통계')",
            "trend_chart": ".trend-chart",
            "source_distribution": ".source-distribution",
            "geo_analysis": ".geo-analysis",
            "threat_level_chart": ".threat-level-chart",
        },
        "collection": {
            "title": "h1:has-text('수집 관리')",
            "collection_status": ".collection-status",
            "regtech_status": ".regtech-status",
            "secudium_status": ".secudium-status",
            "logs_container": ".collection-logs, .log-container, .activity-feed",
        },
        "responsive": {
            "desktop_nav": ".sidebar, .nav-menu, .navigation",
            "mobile_menu_toggle": ".mobile-menu-toggle, .hamburger, .menu-icon",
            "mobile_menu": ".mobile-menu, .drawer, .slide-menu",
        },
        "realtime": {
            "auto_refresh_controls": [
                "input[type='checkbox']:has-text('자동 새고침')",
                ".auto-refresh-toggle",
                "button:has-text('자동')",
            ],
            "refresh_button": "button:has-text('새로고침'), .refresh-btn",
            "stat_values": ".stat-value, .metric-value",
            "loading_indicator": ".loading-spinner, .loading",
        },
    }

    @classmethod
    def get_page_url(cls, page_name: str) -> str:
        """페이지 이름으로 전체 URL 생성"""
        path = cls.TEST_PAGES.get(page_name, "/")
        return f"{cls.BASE_URL}{path}"

    @classmethod
    def get_api_url(cls, endpoint: str) -> str:
        """API 엔드포인트로 전체 URL 생성"""
        return f"{cls.BASE_URL}{endpoint}"

    @classmethod
    def get_selectors(cls, section: str) -> Dict[str, Any]:
        """특정 섹션의 선택자 반환"""
        return cls.SELECTORS.get(section, {})
