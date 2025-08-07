"""
성능 메트릭 데이터 구조

성능 모니터링을 위한 기본 데이터 클래스들을 정의합니다.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class PerformanceMetric:
    """성능 메트릭"""

    timestamp: datetime
    response_time_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    active_connections: int
    cache_hit_rate: float
    database_queries: int
    errors_count: int


@dataclass
class AlertRule:
    """알림 규칙"""

    name: str
    condition: str  # "response_time > 1000", "memory_usage > 80"
    severity: str  # "warning", "critical"
    enabled: bool = True
    last_triggered: Optional[datetime] = None
