#!/usr/bin/env python3
"""
Unified Collector Tests - Core collector functionality and base implementation
Focus on unified_collector.py core classes and base collector functionality
"""

import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional

import pytest
import requests

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestUnifiedCollectorCore:
    """Test unified collector core functionality - targeting 0% coverage"""

    def test_collection_status_enum(self):
        """Test CollectionStatus enum values"""
        from src.core.collectors.unified_collector import CollectionStatus
        
        assert CollectionStatus.IDLE.value == "idle"
        assert CollectionStatus.RUNNING.value == "running"
        assert CollectionStatus.COMPLETED.value == "completed"
        assert CollectionStatus.FAILED.value == "failed"
        assert CollectionStatus.CANCELLED.value == "cancelled"

    def test_collection_result_dataclass(self):
        """Test CollectionResult data class functionality"""
        from src.core.collectors.unified_collector import CollectionResult, CollectionStatus
        
        # Test basic creation
        result = CollectionResult(
            source_name="test_source",
            status=CollectionStatus.IDLE
        )
        assert result.source_name == "test_source"
        assert result.status == CollectionStatus.IDLE
        assert result.collected_count == 0
        assert result.error_count == 0
        assert result.metadata == {}

    def test_collection_result_duration_calculation(self):
        """Test duration calculation in CollectionResult"""
        from src.core.collectors.unified_collector import CollectionResult, CollectionStatus
        
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=30)
        
        result = CollectionResult(
            source_name="test",
            status=CollectionStatus.COMPLETED,
            start_time=start_time,
            end_time=end_time
        )
        
        assert result.duration is not None
        assert abs(result.duration - 30.0) < 0.1  # Allow small float precision error

    def test_collection_result_success_rate(self):
        """Test success rate calculation in CollectionResult"""
        from src.core.collectors.unified_collector import CollectionResult, CollectionStatus
        
        # Test 100% success rate
        result = CollectionResult(
            source_name="test",
            status=CollectionStatus.COMPLETED,
            collected_count=100,
            error_count=0
        )
        assert result.success_rate == 100.0
        
        # Test 80% success rate
        result = CollectionResult(
            source_name="test",
            status=CollectionStatus.COMPLETED,
            collected_count=80,
            error_count=20
        )
        assert result.success_rate == 80.0
        
        # Test 0% when no data
        result = CollectionResult(
            source_name="test",
            status=CollectionStatus.FAILED
        )
        assert result.success_rate == 0.0

    def test_collection_result_to_dict(self):
        """Test CollectionResult.to_dict() method"""
        from src.core.collectors.unified_collector import CollectionResult, CollectionStatus
        
        start_time = datetime.now()
        result = CollectionResult(
            source_name="test_source",
            status=CollectionStatus.COMPLETED,
            collected_count=50,
            error_count=5,
            start_time=start_time,
            metadata={"test": "data"}
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["source_name"] == "test_source"
        assert result_dict["status"] == "completed"
        assert result_dict["collected_count"] == 50
        assert result_dict["error_count"] == 5
        assert result_dict["metadata"] == {"test": "data"}
        assert "start_time" in result_dict

    def test_collection_config_defaults(self):
        """Test CollectionConfig default values"""
        from src.core.collectors.unified_collector import CollectionConfig
        
        config = CollectionConfig()
        assert config.enabled is True
        assert config.interval == 3600
        assert config.max_retries == 3
        assert config.timeout == 300
        assert config.parallel_workers == 1
        assert config.settings == {}

    def test_collection_config_custom_values(self):
        """Test CollectionConfig with custom values"""
        from src.core.collectors.unified_collector import CollectionConfig
        
        config = CollectionConfig(
            enabled=False,
            interval=1800,
            max_retries=5,
            timeout=600,
            parallel_workers=2,
            settings={"custom": "value"}
        )
        
        assert config.enabled is False
        assert config.interval == 1800
        assert config.max_retries == 5
        assert config.timeout == 600
        assert config.parallel_workers == 2
        assert config.settings == {"custom": "value"}


class TestBaseCollectorImplementation:
    """Test BaseCollector abstract class functionality"""

    def test_base_collector_initialization(self):
        """Test BaseCollector initialization"""
        from src.core.collectors.unified_collector import BaseCollector, CollectionConfig
        
        # Create a concrete implementation for testing
        class TestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "TEST"
            
            async def _collect_data(self):
                return ["test_data"]
        
        config = CollectionConfig()
        collector = TestCollector("test_collector", config)
        
        assert collector.name == "test_collector"
        assert collector.config == config
        assert collector.source_type == "TEST"
        assert collector.is_running is False
        assert collector.current_result is None

    def test_base_collector_cancel_functionality(self):
        """Test BaseCollector cancel functionality"""
        from src.core.collectors.unified_collector import BaseCollector, CollectionConfig
        
        class TestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "TEST"
            
            async def _collect_data(self):
                return ["test_data"]
        
        config = CollectionConfig()
        collector = TestCollector("test_collector", config)
        
        assert collector._cancel_requested is False
        collector.cancel()
        assert collector._cancel_requested is True

    def test_base_collector_health_check(self):
        """Test BaseCollector health_check method"""
        from src.core.collectors.unified_collector import BaseCollector, CollectionConfig
        
        class TestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "TEST"
            
            async def _collect_data(self):
                return ["test_data"]
        
        config = CollectionConfig()
        collector = TestCollector("test_collector", config)
        
        health = collector.health_check()
        
        assert health["name"] == "test_collector"
        assert health["type"] == "TEST"
        assert health["enabled"] is True
        assert health["is_running"] is False
        assert health["last_result"] is None

    @pytest.mark.asyncio
    async def test_base_collector_collect_disabled(self):
        """Test BaseCollector collect when disabled"""
        from src.core.collectors.unified_collector import BaseCollector, CollectionConfig, CollectionStatus
        
        class TestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "TEST"
            
            async def _collect_data(self):
                return ["test_data"]
        
        config = CollectionConfig(enabled=False)
        collector = TestCollector("test_collector", config)
        
        result = await collector.collect()
        
        assert result.status == CollectionStatus.CANCELLED
        assert result.error_message == "수집기가 비활성화되어 있습니다."

    @pytest.mark.asyncio
    async def test_base_collector_collect_already_running(self):
        """Test BaseCollector collect when already running"""
        from src.core.collectors.unified_collector import BaseCollector, CollectionConfig, CollectionStatus
        
        class TestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "TEST"
            
            async def _collect_data(self):
                return ["test_data"]
        
        config = CollectionConfig()
        collector = TestCollector("test_collector", config)
        
        # Simulate already running
        collector._is_running = True
        
        result = await collector.collect()
        
        assert result.status == CollectionStatus.FAILED
        assert result.error_message == "수집기가 이미 실행 중입니다."

    @pytest.mark.asyncio
    async def test_base_collector_collect_success(self):
        """Test BaseCollector successful collection"""
        from src.core.collectors.unified_collector import BaseCollector, CollectionConfig, CollectionStatus
        
        class TestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "TEST"
            
            async def _collect_data(self):
                return ["data1", "data2", "data3"]
        
        config = CollectionConfig(timeout=5)
        collector = TestCollector("test_collector", config)
        
        result = await collector.collect()
        
        assert result.status == CollectionStatus.COMPLETED
        assert result.collected_count == 3
        assert result.error_count == 0
        assert result.start_time is not None
        assert result.end_time is not None

    @pytest.mark.asyncio
    async def test_base_collector_collect_timeout(self):
        """Test BaseCollector collection timeout"""
        from src.core.collectors.unified_collector import BaseCollector, CollectionConfig, CollectionStatus
        
        class SlowTestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "SLOW_TEST"
            
            async def _collect_data(self):
                await asyncio.sleep(2)  # Longer than timeout
                return ["data"]
        
        config = CollectionConfig(timeout=0.1, max_retries=0)  # Very short timeout
        collector = SlowTestCollector("slow_collector", config)
        
        result = await collector.collect()
        
        assert result.status == CollectionStatus.FAILED
        assert "타임아웃" in result.error_message

    @pytest.mark.asyncio
    async def test_base_collector_collect_with_retries(self):
        """Test BaseCollector collection with retries"""
        from src.core.collectors.unified_collector import BaseCollector, CollectionConfig, CollectionStatus
        
        class FailingTestCollector(BaseCollector):
            def __init__(self, name, config):
                super().__init__(name, config)
                self.attempt_count = 0
            
            @property
            def source_type(self) -> str:
                return "FAILING_TEST"
            
            async def _collect_data(self):
                self.attempt_count += 1
                if self.attempt_count < 3:
                    raise Exception("Simulated failure")
                return ["success_data"]
        
        config = CollectionConfig(max_retries=3)
        collector = FailingTestCollector("failing_collector", config)
        
        result = await collector.collect()
        
        assert result.status == CollectionStatus.COMPLETED
        assert result.collected_count == 1
        assert collector.attempt_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
