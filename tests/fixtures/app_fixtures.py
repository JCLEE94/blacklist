"""
Flask 애플리케이션 관련 테스트 픽스처
"""

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest


@pytest.fixture
def mock_flask_app():
    """모킹된 Flask 애플리케이션"""
    mock_app = MagicMock()
    mock_app.config = {
        "TESTING": True,
        "DATABASE_URL": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret",
        "COLLECTION_ENABLED": False,
        "FORCE_DISABLE_COLLECTION": True,
    }

    # 기본 응답 설정
    mock_app.test_client.return_value.get.return_value.status_code = 200
    mock_app.test_client.return_value.get.return_value.json = {"status": "healthy"}
    mock_app.test_client.return_value.post.return_value.status_code = 200

    return mock_app


@pytest.fixture
def mock_container_system():
    """모킹된 DI 컨테이너 시스템"""
    from unittest.mock import MagicMock

    mock_container = MagicMock()

    # 서비스 목록
    services = {
        "unified_service": MagicMock(),
        "blacklist_manager": MagicMock(),
        "cache_manager": MagicMock(),
        "collection_manager": MagicMock(),
        "auth_manager": MagicMock(),
    }

    def get_service(service_name):
        return services.get(service_name)

    mock_container.get = get_service

    # 각 서비스의 기본 동작 설정
    services["blacklist_manager"].get_active_ips.return_value = [
        "192.168.1.1",
        "10.0.0.1",
    ]
    services["blacklist_manager"].get_system_health.return_value = {
        "status": "healthy",
        "database": {"active_ips": 2, "total_records": 5},
    }

    services["cache_manager"].get.return_value = None
    services["cache_manager"].set.return_value = True

    return mock_container
