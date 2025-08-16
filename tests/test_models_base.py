#!/usr/bin/env python3
"""
Base model tests for src/core/models.py
Core enums and basic model tests
"""

import pytest
from datetime import datetime, timedelta

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


class TestHealthStatus:
    """HealthStatus enum 테스트"""

    def test_enum_values(self):
        """엠롔 값들이 올바른지 확인"""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"

    def test_enum_iteration(self):
        """모든 엠뉔 값을 순회할 수 있는지 확인"""
        statuses = list(HealthStatus)
        assert len(statuses) == 4
        assert HealthStatus.HEALTHY in statuses


class TestIPAddressType:
    """IPAddressType enum 테스트"""

    def test_enum_values(self):
        """엠뉔 값들이 올바른지 확인"""
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
