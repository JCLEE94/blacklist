"""
Test suite for Blacklist Manager

이 패키지는 시스템의 전체 테스트 스위트를 제공합니다:
- 단위 테스트 (unit tests)
- 통합 테스트 (integration tests)
- 성능 테스트 (performance tests)
- API 엔드포인트 테스트
"""

from unittest.mock import Mock

from flask import Flask
from flask.testing import FlaskClient

# Test utilities and fixtures
from .conftest import app
from .conftest import blacklist_manager
from .conftest import client
from .conftest import mock_cache
from .conftest import sample_ips
from .conftest import temp_data_dir

# Test markers for organization
# These are defined in conftest.py and available for use in tests


# Common test utilities
class TestHelpers:
    """테스트용 도우미 클래스"""

    @staticmethod
    def create_test_app(**config_overrides) -> Flask:
        """테스트용 Flask 앱 생성"""
        from core import create_compact_app

        test_config = {
            "TESTING": True,
            "DEBUG": True,
            "CACHE_TYPE": "memory",
            "DATA_DIR": "/tmp/test_data",
            **config_overrides,
        }

        app = create_compact_app("testing")
        app.config.update(test_config)

        return app

    @staticmethod
    def create_test_client(app: Flask) -> FlaskClient:
        """테스트용 클라이언트 생성"""
        return app.test_client()

    @staticmethod
    def mock_blacklist_manager(**attrs):
        """모크 블랙리스트 매니저 생성"""
        mock = Mock()

        # Default mock behaviors
        mock.load_all_ips.return_value = ["192.168.1.1", "10.0.0.1"]
        mock.get_active_ips.return_value = (["192.168.1.1"], ["2025-06"])
        mock.search_ip.return_value = {
            "ip": "192.168.1.1",
            "found": True,
            "months": ["2025-06"],
            "is_active": True,
        }
        mock.get_system_health.return_value = {
            "status": "healthy",
            "timestamp": "2025-06-09T00:00:00",
        }

        # Apply custom attributes
        for attr, value in attrs.items():
            setattr(mock, attr, value)

        return mock

    @staticmethod
    def assert_api_response(response, expected_status=200, expected_keys=None):
        """
        API 응답 검증 도우미"""
        assert response.status_code == expected_status

        if response.content_type == "application/json":
            data = response.get_json()
            if expected_keys:
                for key in expected_keys:
                    assert key in data, f"Expected key '{key}' not found in response"

        return (
            response.get_json()
            if response.content_type == "application/json"
            else response.data
        )

    @staticmethod
    def create_sample_data_structure(temp_dir: str) -> dict:
        """테스트용 데이터 구조 생성"""
        import json
        from pathlib import Path

        data_dir = Path(temp_dir)
        blacklist_dir = data_dir / "blacklist"
        detection_dir = blacklist_dir / "by_detection_month"

        # Create directories
        detection_dir.mkdir(parents=True, exist_ok=True)

        # Create test data for multiple months
        months_data = {
            "2025-06": ["192.168.1.1", "10.0.0.1", "172.16.0.1"],
            "2025-05": ["192.168.1.2", "10.0.0.2"],
            "2025-04": ["192.168.1.3"],
        }

        for month, ips in months_data.items():
            month_dir = detection_dir / month
            month_dir.mkdir(exist_ok=True)

            # Create IPs file
            ips_file = month_dir / "ips.txt"
            ips_file.write_text("\n".join(ips))

            # Create details file
            details_file = month_dir / "details.json"
            details = {
                "month": month,
                "total_ips": len(ips),
                "detection_date": f"{month}-01T00:00:00Z",
            }
            details_file.write_text(json.dumps(details, indent=2))

        # Create all_ips.txt
        all_ips = set()
        for ips in months_data.values():
            all_ips.update(ips)

        all_ips_file = blacklist_dir / "all_ips.txt"
        all_ips_file.write_text("\n".join(sorted(all_ips)))

        # Create stats.json
        stats_file = data_dir / "stats.json"
        stats = {
            "last_update": "2025-06-09T00:00:00Z",
            "total_ips": len(all_ips),
            "active_months": len(months_data),
        }
        stats_file.write_text(json.dumps(stats, indent=2))

        return {
            "data_dir": str(data_dir),
            "months_data": months_data,
            "all_ips": sorted(all_ips),
            "stats": stats,
        }


# Export test utilities
__all__ = [
    # Test fixtures from conftest
    "app",
    "client",
    "blacklist_manager",
    "temp_data_dir",
    "mock_cache",
    "sample_ips",
    # Test utilities
    "TestHelpers",
]

__version__ = "2.1.0-unified"
__description__ = "Test suite for Blacklist Manager"
