#!/usr/bin/env python3
"""
Model integration tests for src/core/models.py
Tests for model interactions, JSON serialization, and edge cases
"""

import json
from datetime import datetime, timedelta

import pytest

# Import mock classes from the metrics test file
from test_models_metrics import ComponentStatus

from src.core.models import (
    APIResponse,
    BlacklistEntry,
    HealthStatus,
    MonthData,
    SystemHealth,
)


class TestModelIntegration:
    """모델 간 통합 테스트"""

    def test_system_health_with_components(self):
        """컴포넌트가 포함된 시스템 상태 테스트"""
        db_component = ComponentStatus(
            name="database", status=HealthStatus.HEALTHY, details={"connections": "10"}
        )

        cache_component = ComponentStatus(
            name="redis", status=HealthStatus.DEGRADED, details={"memory_usage": "85%"}
        )

        health = SystemHealth(
            status=HealthStatus.DEGRADED, components=[db_component, cache_component]
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
            ip_address="10.0.0.1", threat_level="high", source="regtech"
        )

        month_data = MonthData(month="2023-12", ip_count=100, total_detections=150)

        response = APIResponse(
            success=True,
            data={
                "blacklist": blacklist_entry.to_dict(),
                "monthly_stats": month_data.to_dict(),
            },
            message="Data retrieved successfully",
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
            is_active=True,
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
        entry = BlacklistEntry(ip_address="1.2.3.4", first_seen=None, country=None)
        assert entry.first_seen is None
        assert entry.country is None

        # 빈 리스트
        entry = BlacklistEntry(ip_address="1.2.3.4", detection_months=[])
        assert entry.detection_months == []

    def test_complex_blacklist_entry_workflow(self):
        """복잡한 BlacklistEntry 워크플로우 테스트"""
        # 초기 데이터로 생성
        entry_data = {
            "ip": "203.0.113.1",
            "threat_level": "medium",
            "source": "regtech",
            "first_seen": "2023-01-15",
            "months": ["2023-01", "2023-02", "2023-03"],
            "is_active": True,
            "country": "US",
            "reason": "malware distribution",
        }

        # 딕셔너리에서 생성
        entry = BlacklistEntry.from_dict(entry_data)

        # 값 검증
        assert entry.ip_address == "203.0.113.1"
        assert entry.threat_level == "medium"
        assert len(entry.detection_months) == 3
        assert entry.is_active is True

        # 다시 딕셔너리로 변환
        converted_back = entry.to_dict()

        # 주요 데이터 일치 확인
        assert converted_back["ip"] == entry_data["ip"]
        assert converted_back["threat_level"] == entry_data["threat_level"]
        assert converted_back["source"] == entry_data["source"]
        assert converted_back["months"] == entry_data["months"]

    def test_month_data_lifecycle(self):
        """MonthData 생명주기 테스트"""
        # 초기 데이터
        month_data = MonthData(
            month="2023-06",
            ip_count=250,
            total_detections=300,
            unique_sources=2,
            detection_date="2023-06-15T10:30:00Z",
        )

        # 기본 속성 확인
        assert month_data.month == "2023-06"
        assert month_data.ip_count == 250
        assert month_data.total_detections == 300

        # 딕셔너리 변환
        month_dict = month_data.to_dict()
        assert "month" in month_dict
        assert "ip_count" in month_dict
        assert "month_date" in month_dict

        # 다시 객체로 변환
        recreated = MonthData.from_dict(month_dict)
        assert recreated.month == month_data.month
        assert recreated.ip_count == month_data.ip_count

    def test_api_response_error_scenarios(self):
        """API 응답 에러 시나리오 테스트"""
        # 성공 응답
        success_response = APIResponse(
            success=True,
            data={"count": 100, "items": []},
            message="Successfully retrieved data",
        )

        # 실패 응답
        error_response = APIResponse(
            success=False,
            message="Database connection failed",
            error_code="DB_CONNECTION_ERROR",
        )

        # 부분 실패 응답
        partial_response = APIResponse(
            success=True,
            data={"count": 50, "errors": ["Some items failed to process"]},
            message="Partially successful",
        )

        # 응답 직렬화
        success_dict = success_response.to_dict()
        error_dict = error_response.to_dict()
        partial_dict = partial_response.to_dict()

        # 각 응답의 특성 확인
        assert success_dict["success"] is True
        assert "error_code" not in success_dict or success_dict["error_code"] is None

        assert error_dict["success"] is False
        assert error_dict["error_code"] == "DB_CONNECTION_ERROR"

        assert partial_dict["success"] is True
        assert "errors" in partial_dict["data"]

    def test_nested_model_serialization(self):
        """중청 모델 직렬화 테스트"""
        # BlacklistEntry를 포함한 APIResponse
        entry = BlacklistEntry(
            ip_address="10.0.0.100",
            threat_level="critical",
            source="manual",
            detection_months=["2023-12"],
            is_active=True,
            source_details={
                "analyst": "security_team",
                "confidence": "high",
                "references": ["CVE-2023-1234", "IOC-567890"],
            },
        )

        # MonthData 리스트
        months = [
            MonthData(month="2023-10", ip_count=80),
            MonthData(month="2023-11", ip_count=120),
            MonthData(month="2023-12", ip_count=150),
        ]

        # 전체를 포함한 APIResponse
        complex_response = APIResponse(
            success=True,
            data={
                "featured_threat": entry.to_dict(),
                "monthly_trends": [month.to_dict() for month in months],
                "summary": {
                    "total_ips": sum(m.ip_count for m in months),
                    "trend": "increasing",
                    "last_updated": datetime.now().isoformat(),
                },
            },
            message="Comprehensive threat intelligence report",
        )

        # JSON 직렬화 및 떼직렬화 테스트
        response_dict = complex_response.to_dict()
        json_string = json.dumps(response_dict)
        parsed_back = json.loads(json_string)

        # 데이터 무결성 확인
        assert parsed_back["success"] is True
        assert parsed_back["data"]["featured_threat"]["ip"] == "10.0.0.100"
        assert len(parsed_back["data"]["monthly_trends"]) == 3
        assert parsed_back["data"]["summary"]["total_ips"] == 350

        # 중청 데이터 구조 확인
        featured_threat = parsed_back["data"]["featured_threat"]
        assert featured_threat["source_details"]["analyst"] == "security_team"
        assert "CVE-2023-1234" in featured_threat["source_details"]["references"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
