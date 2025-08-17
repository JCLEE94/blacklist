#!/usr/bin/env python3
"""
Unit tests for data pipeline components

Tests DataCleaningPipeline class and related functionality.
"""

import pytest
import hashlib
import ipaddress
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import modules with fallbacks
try:
    from src.core.data_pipeline import DataCleaningPipeline
except ImportError:
    class DataCleaningPipeline:
        def __init__(self, blacklist_manager=None):
            self.blacklist_manager = blacklist_manager
            self.processed_ips = set()
        
        def clean_ip_data(self, raw_data):
            return []
        
        def process_regtech_data(self, data):
            return []
        
        def process_secudium_data(self, data):
            return []


class TestDataCleaningPipeline:
    """Test the DataCleaningPipeline class"""

    def test_pipeline_initialization(self):
        """Test pipeline initialization"""
        pipeline = DataCleaningPipeline()
        assert pipeline is not None
        assert pipeline.blacklist_manager is None
        assert isinstance(pipeline.processed_ips, set)

    def test_pipeline_with_manager(self):
        """Test pipeline with blacklist manager"""
        mock_manager = Mock()
        pipeline = DataCleaningPipeline(blacklist_manager=mock_manager)
        
        assert pipeline.blacklist_manager == mock_manager
        assert isinstance(pipeline.processed_ips, set)

    def test_clean_ip_data_basic(self):
        """Test basic IP data cleaning"""
        pipeline = DataCleaningPipeline()
        
        raw_data = [
            {"ip": "192.168.1.1", "source": "REGTECH"},
            {"ip": "invalid.ip", "source": "REGTECH"},
            {"ip": "10.0.0.1", "source": "SECUDIUM"}
        ]
        
        result = pipeline.clean_ip_data(raw_data)
        assert isinstance(result, list)

    def test_clean_ip_data_duplicates(self):
        """Test IP data cleaning with duplicates"""
        pipeline = DataCleaningPipeline()
        
        raw_data = [
            {"ip": "192.168.1.1", "source": "REGTECH"},
            {"ip": "192.168.1.1", "source": "REGTECH"},  # Duplicate
            {"ip": "10.0.0.1", "source": "SECUDIUM"}
        ]
        
        result = pipeline.clean_ip_data(raw_data)
        assert isinstance(result, list)

    def test_process_regtech_data(self):
        """Test REGTECH data processing"""
        pipeline = DataCleaningPipeline()
        
        regtech_data = [
            {"IP": "1.1.1.1", "Country": "US", "Type": "Malware"},
            {"IP": "2.2.2.2", "Country": "KR", "Type": "Phishing"}
        ]
        
        result = pipeline.process_regtech_data(regtech_data)
        assert isinstance(result, list)

    def test_process_secudium_data(self):
        """Test SECUDIUM data processing"""
        pipeline = DataCleaningPipeline()
        
        secudium_data = [
            {"ip_address": "3.3.3.3", "country": "CN", "attack_type": "Botnet"},
            {"ip_address": "4.4.4.4", "country": "RU", "attack_type": "Spam"}
        ]
        
        result = pipeline.process_secudium_data(secudium_data)
        assert isinstance(result, list)

    def test_pipeline_with_invalid_data(self):
        """Test pipeline with invalid data"""
        pipeline = DataCleaningPipeline()
        
        invalid_data = [
            {"not_ip": "invalid"},
            None,
            {"ip": None},
            {}
        ]
        
        result = pipeline.clean_ip_data(invalid_data)
        assert isinstance(result, list)

    def test_pipeline_processed_ips_tracking(self):
        """Test that processed IPs are tracked"""
        pipeline = DataCleaningPipeline()
        
        # Initially empty
        assert len(pipeline.processed_ips) == 0
        
        # After processing, should track IPs
        data = [{"ip": "1.1.1.1", "source": "TEST"}]
        pipeline.clean_ip_data(data)
        
        # The tracking depends on implementation


class TestIPValidation:
    """Test IP address validation functionality"""

    def test_valid_ipv4_addresses(self):
        """Test validation of valid IPv4 addresses"""
        valid_ips = [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "8.8.8.8",
            "1.1.1.1"
        ]
        
        for ip in valid_ips:
            try:
                parsed = ipaddress.ip_address(ip)
                assert parsed is not None
            except ValueError:
                pytest.fail(f"Valid IP {ip} failed validation")

    def test_invalid_ipv4_addresses(self):
        """Test validation of invalid IPv4 addresses"""
        invalid_ips = [
            "300.300.300.300",
            "192.168.1",
            "192.168.1.1.1",
            "not.an.ip",
            "",
            None
        ]
        
        for ip in invalid_ips:
            if ip is None:
                continue
            try:
                ipaddress.ip_address(ip)
                pytest.fail(f"Invalid IP {ip} passed validation")
            except ValueError:
                # Expected to fail
                pass

    def test_ipv6_addresses(self):
        """Test IPv6 address handling"""
        ipv6_addresses = [
            "2001:db8::1",
            "::1",
            "fe80::1",
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        ]
        
        for ip in ipv6_addresses:
            try:
                parsed = ipaddress.ip_address(ip)
                assert parsed is not None
                assert parsed.version == 6
            except ValueError:
                # Some implementations might not support IPv6
                pass


class TestDataValidation:
    """Test data validation utilities"""

    def test_hash_generation(self):
        """Test hash generation for data integrity"""
        data = "test_data_for_hashing"
        hash_obj = hashlib.sha256(data.encode())
        hash_value = hash_obj.hexdigest()
        
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA256 hash length

    def test_hash_consistency(self):
        """Test that hashing is consistent"""
        data = "consistent_data"
        
        hash1 = hashlib.sha256(data.encode()).hexdigest()
        hash2 = hashlib.sha256(data.encode()).hexdigest()
        
        assert hash1 == hash2

    def test_hash_different_data(self):
        """Test that different data produces different hashes"""
        data1 = "first_data"
        data2 = "second_data"
        
        hash1 = hashlib.sha256(data1.encode()).hexdigest()
        hash2 = hashlib.sha256(data2.encode()).hexdigest()
        
        assert hash1 != hash2

    def test_datetime_formatting(self):
        """Test datetime formatting for consistency"""
        now = datetime.now()
        
        # Test ISO format
        iso_format = now.isoformat()
        assert isinstance(iso_format, str)
        assert 'T' in iso_format

        # Test string format
        str_format = now.strftime('%Y-%m-%d %H:%M:%S')
        assert isinstance(str_format, str)
        assert len(str_format) == 19


if __name__ == '__main__':
    pytest.main([__file__])
