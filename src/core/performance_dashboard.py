"""
실시간 성능 모니터링 대시보드

이 모듈은 Blacklist 시스템의 성능을 실시간으로 모니터링하고
시각화하는 대시보드 기능을 제공합니다.

참고: 이 모듈은 하위 호환성을 위해 유지됩니다.
새로운 코드는 src.core.performance 패키지를 직접 사용하세요.
"""

# 하위 호환성을 위한 임포트 - 새로운 모듈 구조에서 가져옴
from .performance import (
    AlertManager,
    AlertRule,
    PerformanceDashboard,
    PerformanceMetric,
    dashboard_bp,
    get_global_dashboard,
)

# 하위 호환성을 위한 별칭
__all__ = [
    "PerformanceMetric",
    "AlertRule",
    "AlertManager",
    "PerformanceDashboard",
    "dashboard_bp",
    "get_global_dashboard",
]

# 이 파일은 하위 호환성을 위해 유지됩니다.
# 새로운 코드는 src.core.performance 패키지를 직접 사용하세요.
