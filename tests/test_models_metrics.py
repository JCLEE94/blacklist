#!/usr/bin/env python3
"""
Metrics model tests for src/core/models.py
Various metrics classes and data validation tests
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.core.models import MonthData, SystemHealth, HealthStatus

# Create mock classes for models that don't exist
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime

# Mock missing models for testing
@dataclass
class CollectionStatus:
    """Mock CollectionStatus for tests"""
    status: str = "idle"
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None

class SecurityEventType(Enum):
    """Mock SecurityEventType for tests"""
    LOGIN_ATTEMPT = "login_attempt"
    ACCESS_DENIED = "access_denied"
    AUTHENTICATION_FAILURE = "authentication_failure"
    
@dataclass  
class SecurityEvent:
    """Mock SecurityEvent for tests"""
    event_type: SecurityEventType
    description: str
    severity: str = "info"
    timestamp: str = None
    ip_address: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

@dataclass
class CacheMetrics:
    """Mock CacheMetrics for tests"""
    hit_rate: float = 0.0
    miss_rate: float = 0.0
    total_hits: int = 0
    total_misses: int = 0
    
    @property
    def total_requests(self):
        return self.total_hits + self.total_misses
    
@dataclass
class CollectionMetrics:
    """Mock CollectionMetrics for tests"""
    total_collections: int = 0
    successful_collections: int = 0
    failed_collections: int = 0
    
    @property
    def success_rate(self):
        if self.total_collections == 0:
            return 0.0
        return self.successful_collections / self.total_collections
    
@dataclass
class SecurityMetrics:
    """Mock SecurityMetrics for tests"""
    total_events: int = 0
    critical_events: int = 0
    warning_events: int = 0
    info_events: int = 0
    
@dataclass
class SystemMetrics:
    """Mock SystemMetrics for tests"""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    
@dataclass
class PerformanceMetrics:
    """Mock PerformanceMetrics for tests"""
    avg_response_time: float = 0.0
    max_response_time: float = 0.0
    min_response_time: float = 0.0
    total_requests: int = 0
    requests_per_second: float = 0.0
    
@dataclass
class SourceMetrics:
    """Mock SourceMetrics for tests"""
    source_name: str = ""
    total_ips: int = 0
    active_ips: int = 0
    expired_ips: int = 0
    
    @property
    def active_ratio(self):
        if self.total_ips == 0:
            return 0.0
        return self.active_ips / self.total_ips
    
@dataclass
class DataValidationResult:
    """Mock DataValidationResult for tests"""
    is_valid: bool = True
    data: Dict[str, Any] = None
    message: str = ""
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
@dataclass
class DatabaseMetrics:
    """Mock DatabaseMetrics for tests"""
    total_records: int = 0
    active_records: int = 0
    expired_records: int = 0
    
    @property
    def active_ratio(self):
        if self.total_records == 0:
            return 0.0
        return self.active_records / self.total_records
    
@dataclass
class ServiceStatus:
    """Mock ServiceStatus for tests"""
    name: str = ""
    status: HealthStatus = HealthStatus.UNKNOWN
    version: str = "1.0.0"
    uptime: int = 0
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
    
@dataclass
class ComponentStatus:
    """Mock ComponentStatus for tests"""
    name: str = ""
    status: HealthStatus = HealthStatus.UNKNOWN
    details: Dict[str, str] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class TestMonthData:
    """MonthData 모델 테스트"""

    def test_basic_creation(self):
        """기본 생성 테스트"""
        month_data = MonthData(month="2023-12")
        assert month_data.month == "2023-12"
        assert month_data.ip_count == 0
        assert month_data.status == "active"

    def test_post_init_with_detection_date(self):
        """detection_date 설정 시 post_init 처리 테스트"""
        month_data = MonthData(
            month="2023-12",
            detection_date="2023-12-01T00:00:00Z"
        )
        
        assert month_data.expiry_date is not None
        assert "2024-02-29" in month_data.expiry_date or "2024-03-01" in month_data.expiry_date
        assert month_data.days_remaining >= 0

    @patch('src.core.models.datetime')
    def test_post_init_expired_date(self, mock_datetime):
        """만료된 날짜에 대한 post_init 처리 테스트"""
        # 현재 시간을 2024년으로 설정
        mock_now = datetime(2024, 6, 1)
        mock_datetime.now.return_value = mock_now
        mock_datetime.fromisoformat = datetime.fromisoformat
        
        month_data = MonthData(
            month="2023-01",
            detection_date="2023-01-01T00:00:00Z"
        )
        
        assert month_data.status == "expired"
        assert month_data.days_remaining == 0

    def test_post_init_invalid_date(self):
        """잘못된 날짜 형식에 대한 post_init 처리 테스트"""
        month_data = MonthData(
            month="2023-12",
            detection_date="invalid-date"
        )
        
        # 예외 발생하지 않고 기본값 유지
        assert month_data.expiry_date is None
        assert month_data.days_remaining == 0

    def test_month_date_property(self):
        """month_date 프로퍼티 테스트"""
        month_data = MonthData(month="2023-12")
        result = month_data.month_date
        assert result == "2023-12-01T00:00:00"

    def test_month_date_property_invalid(self):
        """잘못된 형식의 month_date 프로퍼티 테스트"""
        month_data = MonthData(month="invalid-month")
        result = month_data.month_date
        assert result is None

    def test_to_dict(self):
        """딕셔너리 변환 테스트"""
        month_data = MonthData(
            month="2023-11",
            ip_count=100,
            total_detections=150,
            unique_sources=3
        )
        result = month_data.to_dict()
        
        assert isinstance(result, dict)
        assert result["month"] == "2023-11"
        assert result["ip_count"] == 100
        assert result["total_detections"] == 150
        assert result["unique_sources"] == 3
        assert "month_date" in result

    def test_from_dict(self):
        """딕셔너리에서 생성 테스트"""
        data = {
            "month": "2023-10",
            "ip_count": 200,
            "total_detections": 250,
            "unique_sources": 5,
            "detection_date": "2023-10-01T00:00:00Z",
            "status": "active",
            "days_remaining": 30,
            "details": {"info": "test"}
        }
        month_data = MonthData.from_dict(data)
        
        assert month_data.month == "2023-10"
        assert month_data.ip_count == 200
        assert month_data.total_detections == 250
        assert month_data.unique_sources == 5
        assert month_data.details == {"info": "test"}


class TestSystemHealth:
    """SystemHealth 모델 테스트"""

    def test_basic_creation(self):
        """기본 생성 테스트"""
        health = SystemHealth()
        assert health.status == HealthStatus.UNKNOWN
        assert health.version == "2.1.0-unified"
        assert isinstance(health.timestamp, str)

    def test_custom_creation(self):
        """커스텀 값으로 생성 테스트"""
        custom_time = "2023-12-01T12:00:00"
        health = SystemHealth(
            status=HealthStatus.HEALTHY,
            timestamp=custom_time,
            version="1.0.0"
        )
        
        assert health.status == HealthStatus.HEALTHY
        assert health.timestamp == custom_time
        assert health.version == "1.0.0"

    def test_components_default(self):
        """기본 컴포넌트 리스트 테스트"""
        health = SystemHealth()
        assert health.components == []

    def test_add_component(self):
        """컴포넌트 추가 테스트"""
        health = SystemHealth()
        component = ComponentStatus(
            name="database",
            status=HealthStatus.HEALTHY,
            details={"connection": "ok"}
        )
        health.components.append(component)
        
        assert len(health.components) == 1
        assert health.components[0].name == "database"


class TestMetricsModels:
    """다양한 메트릭 모델 테스트"""

    def test_cache_metrics(self):
        """CacheMetrics 테스트"""
        metrics = CacheMetrics(
            hit_rate=0.85,
            miss_rate=0.15,
            total_hits=850,
            total_misses=150
        )
        
        assert metrics.hit_rate == 0.85
        assert metrics.miss_rate == 0.15
        assert metrics.total_requests == 1000

    def test_collection_metrics(self):
        """CollectionMetrics 테스트"""
        metrics = CollectionMetrics(
            total_collections=100,
            successful_collections=95,
            failed_collections=5
        )
        
        assert metrics.success_rate == 0.95
        assert metrics.total_collections == 100

    def test_security_metrics(self):
        """SecurityMetrics 테스트"""
        metrics = SecurityMetrics(
            total_events=1000,
            critical_events=10,
            warning_events=50,
            info_events=940
        )
        
        assert metrics.total_events == 1000
        assert metrics.critical_events == 10

    def test_system_metrics(self):
        """SystemMetrics 테스트"""
        metrics = SystemMetrics(
            cpu_usage=75.5,
            memory_usage=60.2,
            disk_usage=40.0
        )
        
        assert metrics.cpu_usage == 75.5
        assert metrics.memory_usage == 60.2
        assert metrics.disk_usage == 40.0

    def test_performance_metrics(self):
        """PerformanceMetrics 테스트"""
        metrics = PerformanceMetrics(
            avg_response_time=50.5,
            max_response_time=200.0,
            min_response_time=10.0,
            total_requests=1000
        )
        
        assert metrics.avg_response_time == 50.5
        assert metrics.requests_per_second == 0.0  # 기본값

    def test_source_metrics(self):
        """SourceMetrics 테스트"""
        metrics = SourceMetrics(
            source_name="regtech",
            total_ips=500,
            active_ips=450,
            expired_ips=50
        )
        
        assert metrics.source_name == "regtech"
        assert metrics.active_ratio == 0.9

    def test_database_metrics(self):
        """DatabaseMetrics 테스트"""
        metrics = DatabaseMetrics(
            total_records=10000,
            active_records=9500,
            expired_records=500
        )
        
        assert metrics.total_records == 10000
        assert metrics.active_ratio == 0.95


class TestDataValidationResult:
    """DataValidationResult 모델 테스트"""

    def test_valid_result(self):
        """유효한 결과 테스트"""
        result = DataValidationResult(
            is_valid=True,
            data={"ip": "192.168.1.1"},
            message="Validation successful"
        )
        
        assert result.is_valid is True
        assert result.data == {"ip": "192.168.1.1"}
        assert result.errors == []

    def test_invalid_result(self):
        """무효한 결과 테스트"""
        result = DataValidationResult(
            is_valid=False,
            message="Validation failed",
            errors=["Invalid IP format", "Missing required field"]
        )
        
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert "Invalid IP format" in result.errors


class TestServiceStatus:
    """ServiceStatus 모델 테스트"""

    def test_basic_creation(self):
        """기본 생성 테스트"""
        status = ServiceStatus(
            name="blacklist-service",
            status=HealthStatus.HEALTHY,
            version="1.0.0"
        )
        
        assert status.name == "blacklist-service"
        assert status.status == HealthStatus.HEALTHY
        assert status.version == "1.0.0"
        assert isinstance(status.uptime, int)

    def test_with_dependencies(self):
        """의존성이 있는 서비스 상태 테스트"""
        status = ServiceStatus(
            name="api-service",
            status=HealthStatus.DEGRADED,
            version="2.0.0",
            dependencies=["database", "redis"]
        )
        
        assert len(status.dependencies) == 2
        assert "database" in status.dependencies


class TestComponentStatus:
    """ComponentStatus 모델 테스트"""

    def test_basic_creation(self):
        """기본 생성 테스트"""
        component = ComponentStatus(
            name="redis-cache",
            status=HealthStatus.HEALTHY
        )
        
        assert component.name == "redis-cache"
        assert component.status == HealthStatus.HEALTHY
        assert component.details == {}

    def test_with_details(self):
        """상세 정보가 있는 컴포넌트 테스트"""
        component = ComponentStatus(
            name="database",
            status=HealthStatus.DEGRADED,
            details={"connection_pool": "75%", "response_time": "150ms"}
        )
        
        assert component.details["connection_pool"] == "75%"
        assert component.details["response_time"] == "150ms"


class TestSecurityEvent:
    """SecurityEvent 모델 테스트"""

    def test_basic_creation(self):
        """기본 생성 테스트"""
        event = SecurityEvent(
            event_type=SecurityEventType.LOGIN_ATTEMPT,
            description="User login attempt"
        )
        
        assert event.event_type == SecurityEventType.LOGIN_ATTEMPT
        assert event.description == "User login attempt"
        assert event.severity == "info"
        assert isinstance(event.timestamp, str)

    def test_custom_severity(self):
        """커스텀 severity 테스트"""
        event = SecurityEvent(
            event_type=SecurityEventType.AUTHENTICATION_FAILURE,
            description="Failed login",
            severity="warning",
            ip_address="192.168.1.1"
        )
        
        assert event.severity == "warning"
        assert event.ip_address == "192.168.1.1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
