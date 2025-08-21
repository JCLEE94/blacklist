#!/usr/bin/env python3
"""
Collection Manager Tests - UnifiedCollectionManager functionality
Focus on collection management, registration, and orchestration
"""

import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestUnifiedCollectionManager:
    """Test UnifiedCollectionManager functionality"""

    def test_unified_collection_manager_initialization(self):
        """Test UnifiedCollectionManager initialization"""
        from src.core.collectors.unified_collector import \
            UnifiedCollectionManager

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = UnifiedCollectionManager(str(config_path))

            assert manager.config_path == config_path
            assert manager.collectors == {}
            assert isinstance(manager.collection_history, list)
            assert manager.max_history_size == 100

    def test_unified_collection_manager_load_default_config(self):
        """Test loading default configuration"""
        from src.core.collectors.unified_collector import \
            UnifiedCollectionManager

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "nonexistent_config.json"
            manager = UnifiedCollectionManager(str(config_path))

            assert manager.global_config["global_enabled"] is True
            assert "concurrent_collections" in manager.global_config
            assert "collectors" in manager.global_config

    def test_unified_collection_manager_register_collector(self):
        """Test collector registration"""
        from src.core.collectors.unified_collector import (
            BaseCollector, CollectionConfig, UnifiedCollectionManager)

        # Create test collector
        class TestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "TEST"

            async def _collect_data(self):
                return ["test_data"]

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = UnifiedCollectionManager(str(config_path))

            config = CollectionConfig()
            collector = TestCollector("test_collector", config)

            manager.register_collector(collector)

            assert "test_collector" in manager.collectors
            assert manager.get_collector("test_collector") == collector
            assert "test_collector" in manager.list_collectors()

    def test_unified_collection_manager_unregister_collector(self):
        """Test collector unregistration"""
        from src.core.collectors.unified_collector import (
            BaseCollector, CollectionConfig, UnifiedCollectionManager)

        class TestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "TEST"

            async def _collect_data(self):
                return ["test_data"]

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = UnifiedCollectionManager(str(config_path))

            config = CollectionConfig()
            collector = TestCollector("test_collector", config)

            manager.register_collector(collector)
            assert "test_collector" in manager.collectors

            manager.unregister_collector("test_collector")
            assert "test_collector" not in manager.collectors

    def test_unified_collection_manager_get_status(self):
        """Test get_status method"""
        from src.core.collectors.unified_collector import (
            BaseCollector, CollectionConfig, UnifiedCollectionManager)

        class TestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "TEST"

            async def _collect_data(self):
                return ["test_data"]

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = UnifiedCollectionManager(str(config_path))

            config = CollectionConfig()
            collector = TestCollector("test_collector", config)
            manager.register_collector(collector)

            status = manager.get_status()

            assert "global_enabled" in status
            assert "collectors" in status
            assert "running_collectors" in status
            assert "total_collectors" in status
            assert status["total_collectors"] == 1
            assert "test_collector" in status["collectors"]

    def test_unified_collection_manager_enable_disable_global(self):
        """Test global collection enable/disable"""
        from src.core.collectors.unified_collector import \
            UnifiedCollectionManager

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = UnifiedCollectionManager(str(config_path))

            # Test enable
            manager.enable_global_collection()
            assert manager.global_config["global_enabled"] is True

            # Test disable
            manager.disable_global_collection()
            assert manager.global_config["global_enabled"] is False

    def test_unified_collection_manager_enable_disable_collector(self):
        """Test collector enable/disable"""
        from src.core.collectors.unified_collector import (
            BaseCollector, CollectionConfig, UnifiedCollectionManager)

        class TestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "TEST"

            async def _collect_data(self):
                return ["test_data"]

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = UnifiedCollectionManager(str(config_path))

            config = CollectionConfig()
            collector = TestCollector("test_collector", config)
            manager.register_collector(collector)

            # Test disable
            manager.disable_collector("test_collector")
            assert collector.config.enabled is False

            # Test enable
            manager.enable_collector("test_collector")
            assert collector.config.enabled is True

    @pytest.mark.asyncio
    async def test_unified_collection_manager_collect_single(self):
        """Test single collector collection"""
        from src.core.collectors.unified_collector import (
            BaseCollector, CollectionConfig, CollectionStatus,
            UnifiedCollectionManager)

        class TestCollector(BaseCollector):
            @property
            def source_type(self) -> str:
                return "TEST"

            async def _collect_data(self):
                return ["test_data1", "test_data2"]

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = UnifiedCollectionManager(str(config_path))

            config = CollectionConfig()
            collector = TestCollector("test_collector", config)
            manager.register_collector(collector)

            result = await manager.collect_single("test_collector")

            assert result is not None
            assert result.status == CollectionStatus.COMPLETED
            assert result.collected_count == 2
            assert len(manager.collection_history) == 1

    @pytest.mark.asyncio
    async def test_unified_collection_manager_collect_single_nonexistent(self):
        """Test single collector collection with nonexistent collector"""
        from src.core.collectors.unified_collector import \
            UnifiedCollectionManager

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = UnifiedCollectionManager(str(config_path))

            result = await manager.collect_single("nonexistent_collector")

            assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
