"""
향상된 테스트 설정 및 픽스처 (리팩토링됨)

모든 통합 테스트에서 사용할 공통 픽스처와 모킹 유틸리티를 제공합니다.
모듈화되고 간소화된 구조로 재작성되었습니다.
"""

import os
import sys
from pathlib import Path

import pytest

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 테스트 환경 변수 설정
os.environ.update(
    {
        "FLASK_ENV": "testing",
        "TESTING": "true",
        "COLLECTION_ENABLED": "false",
        "FORCE_DISABLE_COLLECTION": "true",
        "CACHE_TYPE": "simple",
        "DATABASE_URL": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-key",
        "JWT_SECRET_KEY": "test-jwt-secret",
        "REGTECH_USERNAME": "test-regtech-user",
        "REGTECH_PASSWORD": "test-regtech-pass",
        "SECUDIUM_USERNAME": "test-secudium-user",
        "SECUDIUM_PASSWORD": "test-secudium-pass",
    }
)


# 모듈화된 픽스처들 import
try:
    from .fixtures import (
        MockResponse,
        does_not_raise,
        mock_container_system,
        mock_database_connection,
        mock_external_services,
        mock_file_system,
        mock_flask_app,
        mock_subprocess,
        test_database,
    )
except ImportError:
    # fixtures 모듈이 없는 경우 기본 픽스처들 정의
    print("⚠️  fixtures 모듈 import 실패 - 기본 픽스처 사용")

    @pytest.fixture(scope="session")
    def test_database():
        """기본 테스트 데이터베이스"""
        return "sqlite:///:memory:"

    @pytest.fixture
    def mock_file_system():
        """기본 파일 시스템 모킹"""
        from unittest.mock import MagicMock, patch

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("builtins.open", create=True) as mock_open,
        ):

            mock_open.return_value.__enter__.return_value.read.return_value = (
                "test content"
            )
            mock_open.return_value.__enter__.return_value.readlines.return_value = [
                "line1\n",
                "line2\n",
            ]

            yield {"open": mock_open}

    @pytest.fixture
    def mock_flask_app():
        """기본 Flask 앱 모킹"""
        from unittest.mock import MagicMock

        mock_app = MagicMock()
        mock_app.config = {"TESTING": True}
        return mock_app

    @pytest.fixture
    def mock_container_system():
        """기본 컨테이너 시스템 모킹"""
        from unittest.mock import MagicMock

        return MagicMock()


@pytest.fixture
def mock_ci_cd_environment():
    """CI/CD 환경 모킹 (GitOps 테스트용)"""
    from unittest.mock import MagicMock, patch

    env_vars = {
        "GITHUB_TOKEN": "test-github-token",
        "ARGOCD_TOKEN": "test-argocd-token",
        "REGISTRY_PASSWORD": "test-registry-pass",
        "CI": "true",
        "GITHUB_ACTIONS": "true",
    }

    with patch.dict(os.environ, env_vars):
        yield env_vars


# 테스트 마커 정의
pytest_markers = [
    "unit: 단위 테스트",
    "integration: 통합 테스트",
    "api: API 테스트",
    "collection: 데이터 수집 테스트",
    "regtech: REGTECH 관련 테스트",
    "secudium: SECUDIUM 관련 테스트",
    "slow: 느린 테스트 (CI에서 선택적 실행)",
    "external: 외부 서비스 의존 테스트",
]


def pytest_configure(config):
    """pytest 설정"""
    for marker in pytest_markers:
        config.addinivalue_line("markers", marker)


def pytest_collection_modifyitems(config, items):
    """테스트 수집 후 처리"""
    # 느린 테스트 마킹
    for item in items:
        if "slow" not in item.keywords and any(
            keyword in item.name.lower()
            for keyword in ["integration", "cicd", "performance"]
        ):
            item.add_marker(pytest.mark.slow)


# 전역 설정
pytest.register_assert_rewrite("tests.fixtures")

# __all__ 정의
__all__ = [
    "test_database",
    "mock_database_connection",
    "mock_flask_app",
    "mock_container_system",
    "mock_external_services",
    "mock_subprocess",
    "mock_file_system",
    "mock_ci_cd_environment",
    "MockResponse",
    "does_not_raise",
]
