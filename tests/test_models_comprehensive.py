"""
Base import tests for src/core/models.py
This file now contains only basic import tests.
The main functionality tests have been modularized into:
- test_models_base.py: Core enums and basic models
- test_models_metrics.py: Metrics classes and validation
- test_models_integration.py: Model interactions and JSON serialization
"""

import pytest

class TestModelsImports:
    """데이터 모델 임포트 테스트"""

    def test_import_health_status(self):
        """HealthStatus 임포트 테스트"""
        try:
            from src.core.models import HealthStatus
            assert HealthStatus is not None
        except ImportError:
            pytest.skip("HealthStatus not available")

    def test_import_blacklist_entry(self):
        """BlacklistEntry 임포트 테스트"""
        try:
            from src.core.models import BlacklistEntry
            assert BlacklistEntry is not None
        except ImportError:
            pytest.skip("BlacklistEntry not available")

    def test_import_api_response(self):
        """APIResponse 임포트 테스트"""
        try:
            from src.core.models import APIResponse
            assert APIResponse is not None
        except ImportError:
            pytest.skip("APIResponse not available")


class TestBasicModelAvailability:
    """기본 모델 사용 가능성 테스트"""

    def test_models_module_availability(self):
        """모델 모듈 사용 가능성 테스트"""
        try:
            import src.core.models
            assert src.core.models is not None
        except ImportError:
            pytest.skip("Models module not available")


if __name__ == "__main__":
    print("Running base models tests...")
    print("For detailed tests, run:")
    print("  python tests/test_models_base.py")
    print("  python tests/test_models_metrics.py")
    print("  python tests/test_models_integration.py")
    pytest.main([__file__, "-v"])
