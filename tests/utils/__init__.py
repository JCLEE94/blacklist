"""Test utilities package"""

from .test_utils import (_create_test_app_with_mock_service,
                         create_simple_mock_container, run_all_tests)

# Import get_container from parent utils module
try:
    import sys
    from pathlib import Path

    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))
    from utils import get_container
except ImportError:
    # Fallback if parent utils not available
    def get_container():
        from unittest.mock import Mock

        mock_container = Mock()
        mock_container.get.return_value = Mock()
        return mock_container


__all__ = [
    "create_simple_mock_container",
    "_create_test_app_with_mock_service",
    "run_all_tests",
    "get_container",
]
