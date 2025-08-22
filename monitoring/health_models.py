"""
헬스체크 데이터 모델들
"""

from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class HealthMetric:
    """헬스 메트릭 클래스"""

    name: str
    value: Any
    status: str  # healthy, warning, critical
    timestamp: datetime
    unit: str = ""
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    description: str = ""


@dataclass
class ServiceStatus:
    """서비스 상태 클래스"""

    name: str
    status: str  # healthy, degraded, unhealthy
    response_time: Optional[float] = None
    last_check: Optional[datetime] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = None


def convert_health_status(status: str) -> str:
    """헬스 상태 변환 (표준화)"""
    status_mapping = {
        "healthy": "success",
        "warning": "warning",
        "critical": "danger",
        "degraded": "warning",
        "unhealthy": "danger",
    }
    return status_mapping.get(status, "secondary")


def get_status_from_thresholds(
    value: float, warning_threshold: float, critical_threshold: float
) -> str:
    """임계값 기준 상태 결정"""
    if value >= critical_threshold:
        return "critical"
    elif value >= warning_threshold:
        return "warning"
    else:
        return "healthy"
