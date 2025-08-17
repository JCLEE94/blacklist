"""
Playwright 설정 파일
blacklist.jclee.me UI 테스트를 위한 구성
"""

import os

# Playwright 설정
PLAYWRIGHT_CONFIG = {
    "testDir": "tests",
    "timeout": 30000,  # 30초 타임아웃
    "expect": {"timeout": 5000},  # 5초 expect 타임아웃
    "fullyParallel": False,  # UI 테스트는 순차 실행
    "forbidOnly": True,
    "retries": 1,  # 실패시 1회 재시도
    "workers": 1,  # 단일 워커로 실행
    "reporter": [
        ["list"],
        ["json", {"outputFile": "test-results/results.json"}],
        ["html", {"open": "never"}],
    ],
    "use": {
        "baseURL": "http://localhost:32542",
        "trace": "on-first-retry",
        "screenshot": "only-on-failure",
        "video": "retain-on-failure",
    },
    "projects": [{"name": "chromium", "use": {"channel": "chromium"}}],
}

# 환경 변수 설정
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "0")
