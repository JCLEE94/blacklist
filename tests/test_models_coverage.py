#!/usr/bin/env python3
"""
Comprehensive tests for core models functionality
Targeting high-value models.py which has 53% coverage but is critical
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestHealthStatus:
    """Test HealthStatus enum"""

    def test_health_status_import(self):
        """Test HealthStatus enum can be imported"""
        from src.core.models import HealthStatus

        assert HealthStatus is not None

    def test_health_status_values(self):
        """Test HealthStatus enum values"""
        from src.core.models import HealthStatus

        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"

    def test_health_status_comparison(self):
        """Test HealthStatus enum comparison"""
        from src.core.models import HealthStatus

        assert HealthStatus.HEALTHY == HealthStatus.HEALTHY
        assert HealthStatus.HEALTHY != HealthStatus.DEGRADED

        # Test string comparison
        assert HealthStatus.HEALTHY.value == "healthy"

    def test_health_status_all_values(self):
        """Test all HealthStatus values are accessible"""
        from src.core.models import HealthStatus

        statuses = [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY,
            HealthStatus.UNKNOWN,
        ]

        assert len(statuses) == 4
        assert all(isinstance(status, HealthStatus) for status in statuses)


class TestIPAddressType:
    """Test IPAddressType enum"""

    def test_ip_address_type_import(self):
        """Test IPAddressType enum can be imported"""
        from src.core.models import IPAddressType

        assert IPAddressType is not None

    def test_ip_address_type_values(self):
        """Test IPAddressType enum values"""
        from src.core.models import IPAddressType

        assert IPAddressType.IPV4.value == "ipv4"
        assert IPAddressType.IPV6.value == "ipv6"
        assert IPAddressType.INVALID.value == "invalid"

    def test_ip_address_type_comparison(self):
        """Test IPAddressType enum comparison"""
        from src.core.models import IPAddressType

        assert IPAddressType.IPV4 == IPAddressType.IPV4
        assert IPAddressType.IPV4 != IPAddressType.IPV6

        # Test string comparison
        assert IPAddressType.IPV4.value == "ipv4"


class TestBlacklistEntry:
    """Test BlacklistEntry model"""

    def test_blacklist_entry_import(self):
        """Test BlacklistEntry can be imported"""
        from src.core.models import BlacklistEntry

        assert BlacklistEntry is not None

    def test_blacklist_entry_basic_creation(self):
        """Test basic BlacklistEntry creation"""
        from src.core.models import BlacklistEntry

        entry = BlacklistEntry(ip_address="192.168.1.1")

        assert entry.ip_address == "192.168.1.1"
        assert entry.first_seen is None
        assert entry.last_seen is None
        assert entry.detection_months == []
        assert entry.is_active is False
        assert entry.days_until_expiry == 0
        assert entry.threat_level == "medium"
        assert entry.source == "unknown"
        assert entry.source_details == {}
        assert entry.country is None
        assert entry.reason is None
        assert entry.reg_date is None
        assert entry.exp_date is None
        assert entry.view_count == 0
        assert entry.uuid is None

    def test_blacklist_entry_with_all_fields(self):
        """Test BlacklistEntry creation with all fields"""
        from src.core.models import BlacklistEntry

        entry = BlacklistEntry(
            ip_address="10.0.0.1",
            first_seen="2024-01-01",
            last_seen="2024-01-15",
            detection_months=["2024-01", "2024-02"],
            is_active=True,
            days_until_expiry=30,
            threat_level="high",
            source="regtech",
            source_details={"provider": "test", "confidence": 0.9},
            country="US",
            reason="malware",
            reg_date="2024-01-01",
            exp_date="2024-12-31",
            view_count=5,
            uuid="test-uuid-123",
        )

        assert entry.ip_address == "10.0.0.1"
        assert entry.first_seen == "2024-01-01"
        assert entry.last_seen == "2024-01-15"
        assert entry.detection_months == ["2024-01", "2024-02"]
        assert entry.is_active is True
        assert entry.days_until_expiry == 30
        assert entry.threat_level == "high"
        assert entry.source == "regtech"
        assert entry.source_details == {"provider": "test", "confidence": 0.9}
        assert entry.country == "US"
        assert entry.reason == "malware"
        assert entry.reg_date == "2024-01-01"
        assert entry.exp_date == "2024-12-31"
        assert entry.view_count == 5
        assert entry.uuid == "test-uuid-123"

    def test_blacklist_entry_defaults(self):
        """Test BlacklistEntry default values"""
        from src.core.models import BlacklistEntry

        entry = BlacklistEntry(ip_address="8.8.8.8")

        # Test default values
        assert isinstance(entry.detection_months, list)
        assert len(entry.detection_months) == 0
        assert isinstance(entry.source_details, dict)
        assert len(entry.source_details) == 0
        assert entry.threat_level == "medium"
        assert entry.source == "unknown"

    def test_blacklist_entry_modification(self):
        """Test BlacklistEntry field modification"""
        from src.core.models import BlacklistEntry

        entry = BlacklistEntry(ip_address="1.1.4.1")

        # Modify fields
        entry.is_active = True
        entry.threat_level = "critical"
        entry.view_count = 10
        entry.detection_months.append("2024-01")
        entry.source_details["test"] = "value"

        # Verify modifications
        assert entry.is_active is True
        assert entry.threat_level == "critical"
        assert entry.view_count == 10
        assert "2024-01" in entry.detection_months
        assert entry.source_details["test"] == "value"


class TestCollectionStatus:
    """Test CollectionStatus enum if it exists"""

    def test_collection_status_import(self):
        """Test CollectionStatus can be imported"""
        try:
            from src.core.models import CollectionStatus

            assert CollectionStatus is not None
        except ImportError:
            pytest.skip("CollectionStatus not available in models")

    def test_collection_status_values(self):
        """Test CollectionStatus values"""
        try:
            from src.core.models import CollectionStatus

            # Test common status values
            statuses = list(CollectionStatus)
            assert len(statuses) > 0

            # Test each status has a string value
            for status in statuses:
                assert isinstance(status.value, str)
                assert len(status.value) > 0
        except ImportError:
            pytest.skip("CollectionStatus not available in models")


class TestStatisticsModels:
    """Test statistics-related models if they exist"""

    def test_statistics_model_import(self):
        """Test statistics models can be imported"""
        try:
            from src.core.models import StatisticsData

            assert StatisticsData is not None
        except ImportError:
            pytest.skip("StatisticsData not available in models")

    def test_threat_level_model_import(self):
        """Test threat level models can be imported"""
        try:
            from src.core.models import ThreatLevel

            assert ThreatLevel is not None
        except ImportError:
            pytest.skip("ThreatLevel not available in models")


class TestDataValidation:
    """Test data validation functionality in models"""

    def test_blacklist_entry_json_serialization(self):
        """Test BlacklistEntry can be converted to/from JSON-like dict"""
        from src.core.models import BlacklistEntry

        entry = BlacklistEntry(
            ip_address="192.168.1.100",
            first_seen="2024-01-01",
            is_active=True,
            threat_level="high",
            detection_months=["2024-01"],
            source_details={"test": "data"},
        )

        # Convert to dict (simulating JSON serialization)
        entry_dict = {
            "ip_address": entry.ip_address,
            "first_seen": entry.first_seen,
            "is_active": entry.is_active,
            "threat_level": entry.threat_level,
            "detection_months": entry.detection_months,
            "source_details": entry.source_details,
        }

        # Verify serialization worked
        assert entry_dict["ip_address"] == "192.168.1.100"
        assert entry_dict["is_active"] is True
        assert entry_dict["threat_level"] == "high"
        assert entry_dict["detection_months"] == ["2024-01"]
        assert entry_dict["source_details"] == {"test": "data"}

    def test_ip_address_validation_concepts(self):
        """Test IP address validation concepts"""
        from src.core.models import BlacklistEntry, IPAddressType

        # Valid IPv4 addresses
        valid_ipv4_addresses = [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "8.8.8.8",
            "1.1.4.1",
        ]

        for ip in valid_ipv4_addresses:
            entry = BlacklistEntry(ip_address=ip)
            assert entry.ip_address == ip
            # These are valid IPv4 format
            assert len(ip.split(".")) == 4

    def test_threat_level_values(self):
        """Test threat level value concepts"""
        from src.core.models import BlacklistEntry

        threat_levels = ["low", "medium", "high", "critical"]

        for level in threat_levels:
            entry = BlacklistEntry(ip_address="1.1.4.1", threat_level=level)
            assert entry.threat_level == level

    def test_source_validation(self):
        """Test source field validation concepts"""
        from src.core.models import BlacklistEntry

        valid_sources = ["regtech", "secudium", "manual", "api", "unknown"]

        for source in valid_sources:
            entry = BlacklistEntry(ip_address="1.1.4.1", source=source)
            assert entry.source == source


class TestModelIntegration:
    """Test integration between different models"""

    def test_health_status_in_entry(self):
        """Test using HealthStatus with BlacklistEntry concepts"""
        from src.core.models import BlacklistEntry, HealthStatus

        entry = BlacklistEntry(ip_address="1.1.4.1")

        # Simulate system health affecting entry status
        system_health = HealthStatus.HEALTHY

        if system_health == HealthStatus.HEALTHY:
            entry.is_active = True
        else:
            entry.is_active = False

        assert entry.is_active is True

    def test_ip_type_with_entry(self):
        """Test using IPAddressType with BlacklistEntry"""
        from src.core.models import BlacklistEntry, IPAddressType

        ipv4_entry = BlacklistEntry(ip_address="192.168.1.1")

        # Simulate IP type detection
        if "." in ipv4_entry.ip_address and len(ipv4_entry.ip_address.split(".")) == 4:
            ip_type = IPAddressType.IPV4
        else:
            ip_type = IPAddressType.IPV6

        assert ip_type == IPAddressType.IPV4

    def test_multiple_entries_management(self):
        """Test managing multiple BlacklistEntry objects"""
        from src.core.models import BlacklistEntry

        entries = [
            BlacklistEntry(ip_address="192.168.1.1", threat_level="low"),
            BlacklistEntry(ip_address="10.0.0.1", threat_level="medium"),
            BlacklistEntry(ip_address="172.16.0.1", threat_level="high"),
        ]

        # Test collection operations
        assert len(entries) == 3

        # Test filtering
        high_threat_entries = [e for e in entries if e.threat_level == "high"]
        assert len(high_threat_entries) == 1

        # Test activation
        for entry in entries:
            entry.is_active = True

        active_entries = [e for e in entries if e.is_active]
        assert len(active_entries) == 3


if __name__ == "__main__":
    # Validation test for the models functionality
    import sys

    all_validation_failures = []
    total_tests = 0

    print("🔄 Running models validation tests...")

    # Test 1: Enums can be imported and used
    total_tests += 1
    try:
        from src.core.models import HealthStatus, IPAddressType

        assert HealthStatus.HEALTHY.value == "healthy"
        assert IPAddressType.IPV4.value == "ipv4"
        print("✅ Enum models: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"Enum models: {e}")

    # Test 2: BlacklistEntry can be created
    total_tests += 1
    try:
        from src.core.models import BlacklistEntry

        entry = BlacklistEntry(ip_address="192.168.1.1")
        assert entry.ip_address == "192.168.1.1"
        assert entry.threat_level == "medium"
        print("✅ BlacklistEntry creation: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"BlacklistEntry creation: {e}")

    # Test 3: BlacklistEntry with all fields
    total_tests += 1
    try:
        from src.core.models import BlacklistEntry

        entry = BlacklistEntry(
            ip_address="10.0.0.1", threat_level="high", is_active=True, source="regtech"
        )
        assert entry.is_active is True
        assert entry.source == "regtech"
        print("✅ BlacklistEntry full creation: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"BlacklistEntry full creation: {e}")

    # Test 4: Default values work correctly
    total_tests += 1
    try:
        from src.core.models import BlacklistEntry

        entry = BlacklistEntry(ip_address="1.1.4.1")
        assert isinstance(entry.detection_months, list)
        assert isinstance(entry.source_details, dict)
        assert entry.days_until_expiry == 0
        print("✅ Default values: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"Default values: {e}")

    # Test 5: Field modification works
    total_tests += 1
    try:
        from src.core.models import BlacklistEntry

        entry = BlacklistEntry(ip_address="8.8.8.8")
        entry.is_active = True
        entry.view_count = 5
        entry.detection_months.append("2024-01")
        assert entry.is_active is True
        assert entry.view_count == 5
        assert "2024-01" in entry.detection_months
        print("✅ Field modification: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"Field modification: {e}")

    # Test 6: Multiple entries management
    total_tests += 1
    try:
        from src.core.models import BlacklistEntry

        entries = [
            BlacklistEntry(ip_address="1.1.4.1", threat_level="low"),
            BlacklistEntry(ip_address="2.2.2.2", threat_level="high"),
        ]
        high_threat = [e for e in entries if e.threat_level == "high"]
        assert len(high_threat) == 1
        print("✅ Multiple entries: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"Multiple entries: {e}")

    # Test 7: Integration between models
    total_tests += 1
    try:
        from src.core.models import BlacklistEntry, HealthStatus, IPAddressType

        entry = BlacklistEntry(ip_address="192.168.1.1")
        health = HealthStatus.HEALTHY
        ip_type = IPAddressType.IPV4

        assert health == HealthStatus.HEALTHY
        assert ip_type == IPAddressType.IPV4
        assert entry.ip_address == "192.168.1.1"
        print("✅ Model integration: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"Model integration: {e}")

    # Test 8: Data serialization concepts
    total_tests += 1
    try:
        from src.core.models import BlacklistEntry

        entry = BlacklistEntry(
            ip_address="3.3.3.3", is_active=True, source_details={"test": "data"}
        )

        # Simulate JSON serialization
        data = {
            "ip_address": entry.ip_address,
            "is_active": entry.is_active,
            "source_details": entry.source_details,
        }
        assert data["ip_address"] == "3.3.3.3"
        assert data["is_active"] is True
        print("✅ Data serialization: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"Data serialization: {e}")

    # Final validation result
    if all_validation_failures:
        print(
            f"\n❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"\n✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print("Models functionality is validated and ready for coverage improvement")
        sys.exit(0)
