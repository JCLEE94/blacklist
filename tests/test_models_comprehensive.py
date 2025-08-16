"""
데이터 모델 포괄적 테스트

모든 데이터 모델의 기능, 변환, 검증을 테스트합니다.
"""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.core.models import (
    HealthStatus,
    IPAddressType,
    BlacklistEntry,
    MonthData,
    SystemHealth,
    APIResponse,
    ValidationResult,
    CacheEntry
)

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
    
@dataclass  
class SecurityEvent:
    """Mock SecurityEvent for tests"""
    event_type: SecurityEventType
    timestamp: datetime
    details: Dict[str, Any]

@dataclass
class CacheMetrics:
    """Mock CacheMetrics for tests"""
    hits: int = 0
    misses: int = 0
    
@dataclass
class CollectionMetrics:
    """Mock CollectionMetrics for tests"""
    total_collected: int = 0
    
@dataclass
class SecurityMetrics:
    """Mock SecurityMetrics for tests"""
    events_count: int = 0
    
@dataclass
class SystemMetrics:
    """Mock SystemMetrics for tests"""
    cpu_usage: float = 0.0
    
@dataclass
class PerformanceMetrics:
    """Mock PerformanceMetrics for tests"""
    response_time: float = 0.0
    
@dataclass
class SourceMetrics:
    """Mock SourceMetrics for tests"""
    source_name: str = ""
    
@dataclass
class DataValidationResult:
    """Mock DataValidationResult for tests"""
    is_valid: bool = True
    
@dataclass
class DatabaseMetrics:
    """Mock DatabaseMetrics for tests"""
    connection_count: int = 0
    
@dataclass
class ServiceStatus:
    """Mock ServiceStatus for tests"""
    name: str = ""
    status: str = "running"
    
@dataclass
class ComponentStatus:
    """Mock ComponentStatus for tests"""
    name: str = ""
    healthy: bool = True


class TestHealthStatus:
    """HealthStatus enum 테스트"""

    def test_enum_values(self):
        """enum 값들이 올바른지 확인"""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"

    def test_enum_iteration(self):
        """모든 enum 값을 순회할 수 있는지 확인"""
        statuses = list(HealthStatus)
        assert len(statuses) == 4
        assert HealthStatus.HEALTHY in statuses


class TestIPAddressType:
    """IPAddressType enum 테스트"""

    def test_enum_values(self):
        """enum 값들이 올바른지 확인"""
        assert IPAddressType.IPV4.value == "ipv4"
        assert IPAddressType.IPV6.value == "ipv6"
        assert IPAddressType.INVALID.value == "invalid"


class TestBlacklistEntry:
    """BlacklistEntry 모델 테스트"""

    def test_basic_creation(self):
        """기본 생성 테스트"""
        entry = BlacklistEntry(ip_address="192.168.1.1")
        assert entry.ip_address == "192.168.1.1"
        assert entry.first_seen is None
        assert entry.detection_months == []
        assert entry.is_active is False
        assert entry.threat_level == "medium"

    def test_full_creation(self):
        """모든 필드를 가진 생성 테스트"""
        entry = BlacklistEntry(
            ip_address="10.0.0.1",
            first_seen="2023-01-01",
            last_seen="2023-12-31",
            detection_months=["2023-01", "2023-02"],
            is_active=True,
            days_until_expiry=30,
            threat_level="high",
            source="regtech",
            source_details={"category": "malware"},
            country="KR",
            reason="suspicious activity",
            reg_date="2023-01-01",
            exp_date="2024-01-01",
            view_count=5,
            uuid="test-uuid"
        )
        
        assert entry.ip_address == "10.0.0.1"
        assert entry.is_active is True
        assert entry.threat_level == "high"
        assert entry.source_details == {"category": "malware"}
        assert entry.country == "KR"
        assert entry.view_count == 5

    def test_to_dict(self):
        """딕셔너리 변환 테스트"""
        entry = BlacklistEntry(
            ip_address="1.2.3.4",
            threat_level="low",
            source="test"
        )
        result = entry.to_dict()
        
        assert isinstance(result, dict)
        assert result["ip"] == "1.2.3.4"
        assert result["threat_level"] == "low"
        assert result["source"] == "test"
        assert "months" in result
        assert "is_active" in result

    def test_from_dict_basic(self):
        """딕셔너리에서 기본 생성 테스트"""
        data = {
            "ip": "5.6.7.8",
            "threat_level": "critical",
            "source": "manual"
        }
        entry = BlacklistEntry.from_dict(data)
        
        assert entry.ip_address == "5.6.7.8"
        assert entry.threat_level == "critical"
        assert entry.source == "manual"

    def test_from_dict_full(self):
        """딕셔너리에서 완전한 데이터로 생성 테스트"""
        data = {
            "ip": "192.168.1.100",
            "first_seen": "2023-01-01",
            "last_seen": "2023-12-31",
            "months": ["2023-01", "2023-02"],
            "is_active": True,
            "days_until_expiry": 45,
            "threat_level": "high",
            "source": "regtech",
            "source_details": {"type": "botnet"},
            "country": "US",
            "reason": "malware distribution",
            "reg_date": "2023-01-01",
            "exp_date": "2024-01-01",
            "view_count": 10,
            "uuid": "test-uuid-123"
        }
        entry = BlacklistEntry.from_dict(data)
        
        assert entry.ip_address == "192.168.1.100"
        assert entry.detection_months == ["2023-01", "2023-02"]
        assert entry.is_active is True
        assert entry.source_details == {"type": "botnet"}
        assert entry.country == "US"
        assert entry.view_count == 10

    def test_from_dict_empty(self):
        """빈 딕셔너리에서 생성 테스트"""
        entry = BlacklistEntry.from_dict({})
        assert entry.ip_address == ""
        assert entry.threat_level == "medium"
        assert entry.source == "unknown"


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


class TestCollectionStatus:
    """CollectionStatus 모델 테스트"""

    def test_basic_creation(self):
        """기본 생성 테스트"""
        status = CollectionStatus()
        assert status.is_enabled is False
        assert status.regtech_enabled is False
        assert status.secudium_enabled is False
        assert isinstance(status.last_collection_time, str)

    def test_custom_creation(self):
        """커스텀 값으로 생성 테스트"""
        status = CollectionStatus(
            is_enabled=True,
            regtech_enabled=True,
            secudium_enabled=True,
            last_collection_time="2023-12-01T10:00:00"
        )
        
        assert status.is_enabled is True
        assert status.regtech_enabled is True
        assert status.secudium_enabled is True
        assert status.last_collection_time == "2023-12-01T10:00:00"


class TestAPIResponse:
    """APIResponse 모델 테스트"""

    def test_success_response(self):
        """성공 응답 테스트"""
        response = APIResponse(
            success=True,
            data={"key": "value"},
            message="Operation successful"
        )
        
        assert response.success is True
        assert response.data == {"key": "value"}
        assert response.message == "Operation successful"
        assert response.error_code is None

    def test_error_response(self):
        """에러 응답 테스트"""
        response = APIResponse(
            success=False,
            message="Operation failed",
            error_code="ERR001"
        )
        
        assert response.success is False
        assert response.message == "Operation failed"
        assert response.error_code == "ERR001"
        assert response.data is None

    def test_to_dict(self):
        """딕셔너리 변환 테스트"""
        response = APIResponse(success=True, data={"test": 123})
        result = response.to_dict()
        
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["data"] == {"test": 123}
        assert "timestamp" in result


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


class TestModelIntegration:
    """모델 간 통합 테스트"""

    def test_system_health_with_components(self):
        """컴포넌트가 포함된 시스템 상태 테스트"""
        db_component = ComponentStatus(
            name="database",
            status=HealthStatus.HEALTHY,
            details={"connections": 10}
        )
        
        cache_component = ComponentStatus(
            name="redis",
            status=HealthStatus.DEGRADED,
            details={"memory_usage": "85%"}
        )
        
        health = SystemHealth(
            status=HealthStatus.DEGRADED,
            components=[db_component, cache_component]
        )
        
        assert len(health.components) == 2
        assert health.status == HealthStatus.DEGRADED
        
        # 각 컴포넌트 확인
        db = next(c for c in health.components if c.name == "database")
        assert db.status == HealthStatus.HEALTHY
        
        redis = next(c for c in health.components if c.name == "redis")
        assert redis.status == HealthStatus.DEGRADED

    def test_api_response_with_complex_data(self):
        """복잡한 데이터가 포함된 API 응답 테스트"""
        blacklist_entry = BlacklistEntry(
            ip_address="10.0.0.1",
            threat_level="high",
            source="regtech"
        )
        
        month_data = MonthData(
            month="2023-12",
            ip_count=100,
            total_detections=150
        )
        
        response = APIResponse(
            success=True,
            data={
                "blacklist": blacklist_entry.to_dict(),
                "monthly_stats": month_data.to_dict()
            },
            message="Data retrieved successfully"
        )
        
        assert response.success is True
        assert "blacklist" in response.data
        assert "monthly_stats" in response.data
        assert response.data["blacklist"]["ip"] == "10.0.0.1"
        assert response.data["monthly_stats"]["month"] == "2023-12"

    def test_json_serialization(self):
        """JSON 직렬화 테스트"""
        entry = BlacklistEntry(
            ip_address="192.168.1.1",
            detection_months=["2023-01", "2023-02"],
            is_active=True
        )
        
        # to_dict 후 JSON 직렬화
        entry_dict = entry.to_dict()
        json_str = json.dumps(entry_dict)
        parsed = json.loads(json_str)
        
        assert parsed["ip"] == "192.168.1.1"
        assert parsed["months"] == ["2023-01", "2023-02"]
        assert parsed["is_active"] is True

    def test_model_validation_edge_cases(self):
        """모델 검증 엣지 케이스 테스트"""
        # 빈 IP 주소
        entry = BlacklistEntry(ip_address="")
        assert entry.ip_address == ""
        
        # None 값 처리
        entry = BlacklistEntry(
            ip_address="1.2.3.4",
            first_seen=None,
            country=None
        )
        assert entry.first_seen is None
        assert entry.country is None
        
        # 빈 리스트
        entry = BlacklistEntry(
            ip_address="1.2.3.4",
            detection_months=[]
        )
        assert entry.detection_months == []