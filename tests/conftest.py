"""
통합 테스트 설정 및 픽스쳐 모듈
모듈화된 테스트 인프라를 통한 간소화된 구성
"""

from pathlib import Path

import pytest

from tests.test_collection_mocks import enable_collection_for_tests
# Import modularized test components
from tests.test_config import EnvironmentManagerHelper, create_test_app
# Database test imports removed - files deleted
from tests.test_fixtures import (blacklist_manager, enhanced_mock_container,
                                 mock_cache, mock_redis, reset_environment,
                                 sample_ips, sample_test_data, temp_data_dir)

# Add project root to Python path
project_root = Path(__file__).parent.parent
import sys

sys.path.insert(0, str(project_root))


# Core test fixtures are imported from modularized modules


@pytest.fixture(scope="session")
def test_environment():
    """Create comprehensive test environment (session scope)"""
    with EnvironmentManagerHelper() as env:
        yield env


@pytest.fixture
def app(test_environment):
    """Create Flask app for testing with enhanced configuration"""
    app = create_test_app("testing")

    # Use test environment temp directory
    app.config["DATA_DIR"] = test_environment.temp_dir

    yield app

    # Cleanup handled by test_environment fixture


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


# Expose all imported fixtures and configurations
__all__ = [
    # Core fixtures
    "test_environment",
    "app",
    "client",
    # Database fixtures
    # Mock fixtures
    "mock_redis",
    "mock_cache",
    "enhanced_mock_container",
    "enable_collection_for_tests",
    # Data fixtures
    "sample_test_data",
    "sample_ips",
    "temp_data_dir",
    "blacklist_manager",
    # Environment fixtures
    "reset_environment",
]
