"""
데이터 모델 및 타입 정의

시스템에서 사용하는 모든 데이터 구조와 모델을 정의합니다.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class HealthStatus(Enum):
    """시스템 상태 열거형"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class IPAddressType(Enum):
    """IP 주소 타입"""

    IPV4 = "ipv4"
    IPV6 = "ipv6"
    INVALID = "invalid"


@dataclass
class BlacklistEntry:
    """블랙리스트 항목 모델"""

    ip_address: str
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    detection_months: List[str] = field(default_factory=list)
    is_active: bool = False
    days_until_expiry: int = 0
    threat_level: str = "medium"
    source: str = "unknown"
    # 새로운 출처 관련 필드
    source_details: Dict[str, Any] = field(default_factory=dict)
    country: Optional[str] = None
    reason: Optional[str] = None
    reg_date: Optional[str] = None
    exp_date: Optional[str] = None
    view_count: int = 0
    uuid: Optional[str] = None

    def __post_init__(self):
        """초기화 후 처리"""
        if not self.detection_months:
            self.detection_months = []

    @property
    def total_occurrences(self) -> int:
        """총 발견 횟수"""
        return len(self.detection_months)

    @property
    def expire_date(self) -> Optional[str]:
        """만료 날짜 계산"""
        if self.last_seen:
            try:
                last_date = datetime.strptime(self.last_seen, "%Y-%m")
                expire_date = last_date + timedelta(days=90)
                return expire_date.isoformat()
            except ValueError:
                return None
        return None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "ip": self.ip_address,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "months": self.detection_months,
            "total_occurrences": self.total_occurrences,
            "is_active": self.is_active,
            "days_until_expiry": self.days_until_expiry,
            "expire_date": self.expire_date,
            "threat_level": self.threat_level,
            "source": self.source,
            "source_details": self.source_details,
            "country": self.country,
            "reason": self.reason,
            "reg_date": self.reg_date,
            "exp_date": self.exp_date,
            "view_count": self.view_count,
            "uuid": self.uuid,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BlacklistEntry":
        """딕셔너리에서 생성"""
        return cls(
            ip_address=data.get("ip", ""),
            first_seen=data.get("first_seen"),
            last_seen=data.get("last_seen"),
            detection_months=data.get("months", []),
            is_active=data.get("is_active", False),
            days_until_expiry=data.get("days_until_expiry", 0),
            threat_level=data.get("threat_level", "medium"),
            source=data.get("source", "unknown"),
            source_details=data.get("source_details", {}),
            country=data.get("country"),
            reason=data.get("reason"),
            reg_date=data.get("reg_date"),
            exp_date=data.get("exp_date"),
            view_count=data.get("view_count", 0),
            uuid=data.get("uuid"),
        )


@dataclass
class MonthData:
    """월별 데이터 모델"""

    month: str
    ip_count: int = 0
    total_detections: int = 0
    unique_sources: int = 0
    detection_date: Optional[str] = None
    expiry_date: Optional[str] = None
    status: str = "active"
    days_remaining: int = 0
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """초기화 후 처리"""
        if self.detection_date and not self.expiry_date:
            try:
                detection = datetime.fromisoformat(
                    self.detection_date.replace("Z", "+00:00")
                )
                expiry = detection + timedelta(days=90)
                self.expiry_date = expiry.isoformat()

                # 남은 일수 계산
                now = datetime.now()
                if expiry > now:
                    self.days_remaining = (expiry - now).days
                    self.status = "active"
                else:
                    self.days_remaining = 0
                    self.status = "expired"
            except (ValueError, TypeError):
                pass

    @property
    def month_date(self) -> Optional[str]:
        """월 날짜 ISO 형식"""
        try:
            month_dt = datetime.strptime(self.month, "%Y-%m")
            return month_dt.isoformat()
        except ValueError:
            return None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "month": self.month,
            "ip_count": self.ip_count,
            "total_detections": self.total_detections,
            "unique_sources": self.unique_sources,
            "detection_date": self.detection_date,
            "expiry_date": self.expiry_date,
            "month_date": self.month_date,
            "status": self.status,
            "days_remaining": self.days_remaining,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MonthData":
        """딕셔너리에서 생성"""
        return cls(
            month=data.get("month", ""),
            ip_count=data.get("ip_count", 0),
            total_detections=data.get("total_detections", 0),
            unique_sources=data.get("unique_sources", 0),
            detection_date=data.get("detection_date"),
            expiry_date=data.get("expiry_date"),
            status=data.get("status", "active"),
            days_remaining=data.get("days_remaining", 0),
            details=data.get("details", {}),
        )


@dataclass
class SystemHealth:
    """시스템 상태 모델"""

    status: HealthStatus = HealthStatus.UNKNOWN
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "2.1.0-unified"
    cache_entries: int = 0
    available_months: int = 0
    total_ips: int = 0
    active_ips: int = 0
    issues: List[str] = field(default_factory=list)
    services: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    data_directories: Dict[str, bool] = field(default_factory=dict)

    def add_issue(self, issue: str):
        """이슈 추가"""
        if issue not in self.issues:
            self.issues.append(issue)

    def add_service_status(
        self,
        service_name: str,
        status: str,
        response_time: Optional[float] = None,
        additional_info: Optional[Dict] = None,
    ):
        """서비스 상태 추가"""
        service_info = {"status": status, "last_check": datetime.now().isoformat()}

        if response_time is not None:
            service_info["response_time_ms"] = response_time

        if additional_info:
            service_info.update(additional_info)

        self.services[service_name] = service_info

    def update_performance_metric(self, metric_name: str, value: float):
        """성능 메트릭 업데이트"""
        self.performance_metrics[metric_name] = value

    def calculate_overall_status(self) -> HealthStatus:
        """전체 상태 계산"""
        if self.issues:
            if any(
                "critical" in issue.lower() or "error" in issue.lower()
                for issue in self.issues
            ):
                return HealthStatus.UNHEALTHY
            else:
                return HealthStatus.DEGRADED

        # 서비스 상태 확인
        unhealthy_services = [
            name
            for name, info in self.services.items()
            if info.get("status") not in ["online", "healthy", "connected"]
        ]

        if unhealthy_services:
            if len(unhealthy_services) > len(self.services) / 2:
                return HealthStatus.UNHEALTHY
            else:
                return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        # 상태 자동 계산
        self.status = self.calculate_overall_status()

        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "version": self.version,
            "cache_entries": self.cache_entries,
            "available_months": self.available_months,
            "total_ips": self.total_ips,
            "active_ips": self.active_ips,
            "issues": self.issues,
            "services": self.services,
            "performance_metrics": self.performance_metrics,
            "data_directories": self.data_directories,
            "overall_health_score": self._calculate_health_score(),
        }

    def _calculate_health_score(self) -> float:
        """상태 점수 계산 (0-100)"""
        score = 100.0

        # 이슈로 인한 점수 차감
        score -= len(self.issues) * 10

        # 서비스 상태로 인한 점수 차감
        unhealthy_services = [
            name
            for name, info in self.services.items()
            if info.get("status") not in ["online", "healthy", "connected"]
        ]
        if self.services:
            score -= (len(unhealthy_services) / len(self.services)) * 30

        # 데이터 상태로 인한 점수 차감
        if self.total_ips == 0:
            score -= 20
        if self.available_months == 0:
            score -= 20

        return max(0.0, min(100.0, score))


@dataclass
class ValidationResult:
    """검증 결과 모델"""

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    valid_items: List[Any] = field(default_factory=list)
    invalid_items: List[Any] = field(default_factory=list)

    def add_error(self, error: str):
        """에러 추가"""
        self.errors.append(error)
        self.valid = False

    def add_warning(self, warning: str):
        """경고 추가"""
        self.warnings.append(warning)

    def add_valid_item(self, item: Any):
        """유효한 항목 추가"""
        self.valid_items.append(item)

    def add_invalid_item(self, item: Any):
        """유효하지 않은 항목 추가"""
        self.invalid_items.append(item)
        self.valid = False

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "valid_count": len(self.valid_items),
            "invalid_count": len(self.invalid_items),
            "valid_items": self.valid_items,
            "invalid_items": self.invalid_items,
        }


@dataclass
class APIResponse:
    """API 응답 모델"""

    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        result = {"success": self.success, "timestamp": self.timestamp}

        if self.data is not None:
            result["data"] = self.data

        if self.error:
            result["error"] = self.error

        if self.message:
            result["message"] = self.message

        if self.metadata:
            result["metadata"] = self.metadata

        return result

    @classmethod
    def success_response(
        cls, data: Any = None, message: str = None, metadata: Dict[str, Any] = None
    ) -> "APIResponse":
        """성공 응답 생성"""
        return cls(success=True, data=data, message=message, metadata=metadata or {})

    @classmethod
    def error_response(
        cls, error: str, data: Any = None, metadata: Dict[str, Any] = None
    ) -> "APIResponse":
        """에러 응답 생성"""
        return cls(success=False, error=error, data=data, metadata=metadata or {})


@dataclass
class CacheEntry:
    """캐시 항목 모델"""

    key: str
    value: Any
    ttl: int
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0

    def update_access(self):
        """접근 정보 업데이트"""
        self.accessed_at = datetime.now()
        self.access_count += 1

    @property
    def is_expired(self) -> bool:
        """만료 여부 확인"""
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl)

    @property
    def remaining_ttl(self) -> int:
        """남은 TTL (초)"""
        if self.is_expired:
            return 0

        elapsed = datetime.now() - self.created_at
        remaining = timedelta(seconds=self.ttl) - elapsed
        return max(0, int(remaining.total_seconds()))


# 유틸리티 함수들
def serialize_model(obj: Any) -> str:
    """모델을 JSON 문자열로 직렬화"""
    if hasattr(obj, "to_dict"):
        return json.dumps(obj.to_dict(), ensure_ascii=False, indent=2)
    elif isinstance(obj, (list, dict)):
        return json.dumps(obj, ensure_ascii=False, indent=2)
    else:
        return str(obj)


def deserialize_model(model_class: type, data: Union[str, Dict]) -> Any:
    """JSON 문자열이나 딕셔너리에서 모델 생성"""
    if isinstance(data, str):
        data = json.loads(data)

    if hasattr(model_class, "from_dict"):
        return model_class.from_dict(data)
    else:
        return model_class(**data)
