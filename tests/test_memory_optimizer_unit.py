#!/usr/bin/env python3
"""
Unit tests for memory core optimizer

Tests CoreMemoryOptimizer and MemoryStats components.
"""

import gc
import threading
import time
from datetime import datetime
from unittest.mock import Mock
from unittest.mock import patch

import pytest

# Test imports
from src.utils.memory.core_optimizer import CoreMemoryOptimizer
from src.utils.memory.core_optimizer import MemoryStats


class TestMemoryStats:
    """Test MemoryStats dataclass"""

    def test_memory_stats_creation(self):
        """Test MemoryStats dataclass creation"""
        timestamp = datetime.now()
        gc_collections = {0: 100, 1: 50, 2: 10}

        stats = MemoryStats(
            total_memory_mb=8192.0,
            available_memory_mb=4096.0,
            used_memory_mb=4096.0,
            memory_percent=50.0,
            process_memory_mb=256.0,
            gc_collections=gc_collections,
            timestamp=timestamp,
        )

        assert stats.total_memory_mb == 8192.0
        assert stats.available_memory_mb == 4096.0
        assert stats.used_memory_mb == 4096.0
        assert stats.memory_percent == 50.0
        assert stats.process_memory_mb == 256.0
        assert stats.gc_collections == gc_collections
        assert stats.timestamp == timestamp


class TestCoreMemoryOptimizer:
    """Test CoreMemoryOptimizer class"""

    def setup_method(self):
        """Setup test environment"""
        self.optimizer = CoreMemoryOptimizer(
            max_memory_percent=80.0, gc_threshold_mb=100.0, monitoring_interval=1.0
        )

    def teardown_method(self):
        """Cleanup test environment"""
        # Stop monitoring if active
        if self.optimizer.monitoring_active:
            self.optimizer.stop_memory_monitoring()

    def test_initialization(self):
        """Test CoreMemoryOptimizer initialization"""
        assert self.optimizer.max_memory_percent == 80.0
        assert self.optimizer.gc_threshold_mb == 100.0
        assert self.optimizer.monitoring_interval == 1.0

        assert hasattr(self.optimizer, "object_pools")
        assert hasattr(self.optimizer, "pool_locks")
        assert hasattr(self.optimizer, "memory_history")
        assert hasattr(self.optimizer, "optimization_stats")

        # Check initial stats
        expected_stats = {
            "pool_hits": 0,
            "pool_misses": 0,
            "gc_forced": 0,
            "memory_warnings": 0,
            "chunked_operations": 0,
        }
        assert self.optimizer.optimization_stats == expected_stats

    @patch("src.utils.memory.core_optimizer.psutil.virtual_memory")
    @patch("src.utils.memory.core_optimizer.psutil.Process")
    @patch("src.utils.memory.core_optimizer.gc.get_count")
    def test_get_memory_stats(
        self, mock_gc_count, mock_process_class, mock_virtual_memory
    ):
        """Test memory statistics collection"""
        # Setup mocks
        mock_memory = Mock()
        mock_memory.total = 8 * 1024 * 1024 * 1024  # 8GB in bytes
        mock_memory.available = 4 * 1024 * 1024 * 1024  # 4GB
        mock_memory.used = 4 * 1024 * 1024 * 1024  # 4GB
        mock_memory.percent = 50.0
        mock_virtual_memory.return_value = mock_memory

        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 256 * 1024 * 1024  # 256MB in bytes
        mock_process.memory_info.return_value = mock_memory_info
        mock_process_class.return_value = mock_process

        mock_gc_count.return_value = [100, 50, 10]

        # Get stats
        stats = self.optimizer.get_memory_stats()

        # Verify stats
        assert stats.total_memory_mb == 8192.0  # 8GB
        assert stats.available_memory_mb == 4096.0  # 4GB
        assert stats.used_memory_mb == 4096.0  # 4GB
        assert stats.memory_percent == 50.0
        assert stats.process_memory_mb == 256.0  # 256MB
        assert stats.gc_collections == {0: 100, 1: 50, 2: 10}
        assert isinstance(stats.timestamp, datetime)

    def test_check_memory_pressure_low_usage(self):
        """Test memory pressure check with low usage"""
        with patch.object(self.optimizer, "get_memory_stats") as mock_get_stats:
            # Mock low memory usage
            mock_stats = Mock()
            mock_stats.memory_percent = 50.0  # Below 80% threshold
            mock_stats.process_memory_mb = 64.0
            mock_get_stats.return_value = mock_stats

            result = self.optimizer.check_memory_pressure()

            assert result is False
            assert self.optimizer.optimization_stats["memory_warnings"] == 0

    def test_check_memory_pressure_high_usage(self):
        """Test memory pressure check with high usage"""
        with patch.object(self.optimizer, "get_memory_stats") as mock_get_stats:
            # Mock high memory usage
            mock_stats = Mock()
            mock_stats.memory_percent = 90.0  # Above 80% threshold
            mock_stats.process_memory_mb = 512.0
            mock_get_stats.return_value = mock_stats

            result = self.optimizer.check_memory_pressure()

            assert result is True
            assert self.optimizer.optimization_stats["memory_warnings"] == 1

    @patch("src.utils.memory.core_optimizer.gc.collect")
    def test_force_gc_if_needed_low_memory(self, mock_gc_collect):
        """Test garbage collection with low memory usage"""
        with patch.object(self.optimizer, "get_memory_stats") as mock_get_stats:
            # Mock low memory usage
            mock_stats = Mock()
            mock_stats.memory_percent = 50.0  # Below threshold
            mock_stats.process_memory_mb = 50.0  # Below threshold
            mock_get_stats.return_value = mock_stats

            result = self.optimizer.force_gc_if_needed()

            assert result is False
            mock_gc_collect.assert_not_called()
            assert self.optimizer.optimization_stats["gc_forced"] == 0

    @patch("src.utils.memory.core_optimizer.gc.collect")
    def test_force_gc_if_needed_high_memory_percent(self, mock_gc_collect):
        """Test garbage collection with high memory percentage"""
        with patch.object(self.optimizer, "get_memory_stats") as mock_get_stats:
            # First call (before GC) - high memory
            # Second call (after GC) - lower memory
            mock_stats_before = Mock()
            mock_stats_before.memory_percent = 85.0  # Above threshold (80% * 0.8 = 64%)
            mock_stats_before.process_memory_mb = 200.0

            mock_stats_after = Mock()
            mock_stats_after.memory_percent = 70.0
            mock_stats_after.process_memory_mb = 150.0  # 50MB freed

            mock_get_stats.side_effect = [mock_stats_before, mock_stats_after]

            result = self.optimizer.force_gc_if_needed()

            assert result is True
            mock_gc_collect.assert_called_once()
            assert self.optimizer.optimization_stats["gc_forced"] == 1

    def test_chunked_processing_small_data(self):
        """Test chunked processing with small dataset"""
        data = list(range(50))  # Small dataset
        chunk_size = 100

        chunks_processed = []

        try:
            for chunk_info in self.optimizer.chunked_processing(data, chunk_size):
                chunk_num, chunk, total_chunks = chunk_info
                chunks_processed.append((chunk_num, len(chunk), total_chunks))
        except TypeError:
            # If the context manager pattern doesn't work as iterator
            with self.optimizer.chunked_processing(data, chunk_size):
                pass  # The yields happen inside the context manager

        # The optimization stats should still be updated
        assert self.optimizer.optimization_stats["chunked_operations"] == 1

    def test_chunked_processing_large_data(self):
        """Test chunked processing with large dataset"""
        data = list(range(2500))  # Large dataset
        chunk_size = 1000

        chunks_processed = []

        for chunk_info in self.optimizer.chunked_processing(data, chunk_size):
            chunk_num, chunk, total_chunks = chunk_info
            chunks_processed.append((chunk_num, len(chunk), total_chunks))

        # Should have 3 chunks: 1000, 1000, 500
        assert len(chunks_processed) == 3
        assert chunks_processed[0] == (1, 1000, 3)
        assert chunks_processed[1] == (2, 1000, 3)
        assert chunks_processed[2] == (3, 500, 3)
        assert self.optimizer.optimization_stats["chunked_operations"] == 1

    def test_start_memory_monitoring(self):
        """Test starting memory monitoring"""
        assert not self.optimizer.monitoring_active
        assert self.optimizer.monitoring_thread is None

        self.optimizer.start_memory_monitoring()

        assert self.optimizer.monitoring_active
        assert self.optimizer.monitoring_thread is not None
        assert self.optimizer.monitoring_thread.is_alive()

    def test_stop_memory_monitoring(self):
        """Test stopping memory monitoring"""
        # Start monitoring first
        self.optimizer.start_memory_monitoring()

        # Verify it's running
        assert self.optimizer.monitoring_active
        assert self.optimizer.monitoring_thread.is_alive()

        # Stop monitoring
        self.optimizer.stop_memory_monitoring()

        assert not self.optimizer.monitoring_active
        # Thread should stop (give it a moment)
        time.sleep(0.1)

    def test_get_object_from_pool_hit(self):
        """Test getting object from pool with hit"""
        object_type = "test_objects"
        test_object = {"data": "test"}

        # Pre-populate pool
        self.optimizer.object_pools[object_type].append(test_object)

        # Get object
        result = self.optimizer.get_object_from_pool(object_type)

        assert result is test_object
        assert len(self.optimizer.object_pools[object_type]) == 0
        assert self.optimizer.optimization_stats["pool_hits"] == 1
        assert self.optimizer.optimization_stats["pool_misses"] == 0

    def test_get_object_from_pool_miss_with_factory(self):
        """Test getting object from empty pool with factory"""
        object_type = "test_objects"

        def factory():
            return {"data": "new"}

        # Pool is empty
        result = self.optimizer.get_object_from_pool(object_type, factory)

        assert result == {"data": "new"}
        assert self.optimizer.optimization_stats["pool_hits"] == 0
        assert self.optimizer.optimization_stats["pool_misses"] == 1

    def test_return_object_to_pool_basic(self):
        """Test returning object to pool"""
        object_type = "test_objects"
        test_object = {"data": "test"}

        # Return object to pool
        self.optimizer.return_object_to_pool(object_type, test_object)

        assert len(self.optimizer.object_pools[object_type]) == 1
        assert self.optimizer.object_pools[object_type][0] is test_object

    def test_thread_safety_object_pools(self):
        """Test thread safety of object pool operations"""
        object_type = "thread_test_objects"

        def pool_operations():
            for i in range(100):
                # Return object
                self.optimizer.return_object_to_pool(object_type, f"object_{i}")

                # Get object
                obj = self.optimizer.get_object_from_pool(object_type)

                # Small delay to increase contention
                time.sleep(0.001)

        # Run concurrent threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=pool_operations)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should handle concurrent access without errors
        total_hits = self.optimizer.optimization_stats["pool_hits"]
        total_misses = self.optimizer.optimization_stats["pool_misses"]
        assert total_hits + total_misses == 500  # 5 threads * 100 operations


if __name__ == "__main__":
    pytest.main([__file__])
