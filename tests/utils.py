"""
테스트 유틸리티 모듈
테스트에서 공통으로 사용되는 헬퍼 함수들
"""

import sys
from pathlib import Path

# Add src to path if not already there
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

try:
    from src.core.container import get_container as _get_container
except ImportError:
    try:
        from core.container import get_container as _get_container
    except ImportError:
        from .blacklist_container import BlacklistContainer

        def _get_container():
            """Fallback container getter"""
            return BlacklistContainer()


def get_container():
    """테스트용 컨테이너 인스턴스 반환"""
    try:
        return _get_container()
    except Exception:
        # Fallback to local container
        from .blacklist_container import BlacklistContainer

        return BlacklistContainer()


def setup_test_environment():
    """테스트 환경 설정"""
    import os

    os.environ.setdefault("TESTING", "true")
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


def cleanup_test_environment():
    """테스트 환경 정리"""
    import os

    if "TESTING" in os.environ:
        del os.environ["TESTING"]
