"""
시스템 안정성 모니터링 - 호환성 모듈
이 모듈은 기존 import를 유지하면서 새로운 모듈로 리다이렉트합니다.
"""

# Import all functionality from the new split modules
from .system_health import SystemHealth
from .system_monitors import (
    DatabaseStabilityManager,
    SystemMonitor,
    safe_execute,
    create_system_monitor,
    get_system_monitor,
    initialize_system_stability,
)

# Re-export everything for backward compatibility
__all__ = [
    "SystemHealth",
    "DatabaseStabilityManager", 
    "SystemMonitor",
    "safe_execute",
    "create_system_monitor",
    "get_system_monitor",
    "initialize_system_stability",
]
