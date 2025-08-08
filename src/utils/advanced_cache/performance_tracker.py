#!/usr/bin/env python3
"""
Performance Tracker for Advanced Cache
"""

import logging
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """Tracks and analyzes cache performance metrics"""

    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self.lock = threading.RLock()

        # Operation metrics
        self.operations = defaultdict(int)
        self.operation_times = deque(maxlen=max_history)
        self.hit_rates = deque(maxlen=1000)  # Track hit rate over time

        # Performance metrics
        self.total_operations = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_time = 0.0

        # Error tracking
        self.errors = defaultdict(int)
        self.last_errors = deque(maxlen=100)

        # Memory usage tracking
        self.memory_usage_history = deque(maxlen=1000)

        self.start_time = time.time()

    def record_operation(
        self, operation: str, execution_time: float, success: bool = True
    ):
        """Record a cache operation"""
        with self.lock:
            self.operations[operation] += 1
            self.total_operations += 1
            self.total_time += execution_time

            # Record timing
            self.operation_times.append(
                {
                    "operation": operation,
                    "time": execution_time,
                    "timestamp": time.time(),
                    "success": success,
                }
            )

            if not success:
                self.errors[operation] += 1
                self.last_errors.append(
                    {
                        "operation": operation,
                        "timestamp": time.time(),
                        "execution_time": execution_time,
                    }
                )

    def record_cache_result(self, hit: bool):
        """Record cache hit or miss"""
        with self.lock:
            if hit:
                self.cache_hits += 1
            else:
                self.cache_misses += 1

            # Update hit rate history
            current_hit_rate = self.get_hit_rate()
            self.hit_rates.append({"rate": current_hit_rate, "timestamp": time.time()})

    def record_memory_usage(self, bytes_used: int):
        """Record memory usage snapshot"""
        with self.lock:
            self.memory_usage_history.append(
                {"bytes": bytes_used, "timestamp": time.time()}
            )

    def get_hit_rate(self) -> float:
        """Calculate current hit rate"""
        total_requests = self.cache_hits + self.cache_misses
        return (self.cache_hits / total_requests * 100) if total_requests > 0 else 0.0

    def get_average_operation_time(self, operation: str = None) -> float:
        """Get average operation time"""
        with self.lock:
            if operation:
                operation_times = [
                    op["time"]
                    for op in self.operation_times
                    if op["operation"] == operation and op["success"]
                ]
                return (
                    sum(operation_times) / len(operation_times)
                    if operation_times
                    else 0.0
                )
            else:
                return (
                    self.total_time / self.total_operations
                    if self.total_operations > 0
                    else 0.0
                )

    def get_operations_per_second(self, window_seconds: int = 60) -> float:
        """Calculate operations per second in the given time window"""
        with self.lock:
            now = time.time()
            cutoff_time = now - window_seconds

            recent_ops = [
                op for op in self.operation_times if op["timestamp"] >= cutoff_time
            ]

            return len(recent_ops) / window_seconds if window_seconds > 0 else 0.0

    def get_error_rate(self, operation: str = None) -> float:
        """Calculate error rate for operations"""
        with self.lock:
            if operation:
                total_ops = self.operations[operation]
                errors = self.errors[operation]
                return (errors / total_ops * 100) if total_ops > 0 else 0.0
            else:
                total_errors = sum(self.errors.values())
                return (
                    (total_errors / self.total_operations * 100)
                    if self.total_operations > 0
                    else 0.0
                )

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        with self.lock:
            uptime_seconds = time.time() - self.start_time

            # Calculate percentiles for operation times
            times = [op["time"] for op in self.operation_times if op["success"]]
            times.sort()

            def percentile(data, p):
                if not data:
                    return 0.0
                k = (len(data) - 1) * p / 100
                floor_k = int(k)
                ceil_k = min(floor_k + 1, len(data) - 1)
                if floor_k == ceil_k:
                    return data[floor_k]
                return data[floor_k] * (ceil_k - k) + data[ceil_k] * (k - floor_k)

            return {
                "uptime_seconds": uptime_seconds,
                "total_operations": self.total_operations,
                "operations_per_second": self.total_operations / uptime_seconds
                if uptime_seconds > 0
                else 0,
                "hit_rate_percent": self.get_hit_rate(),
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "average_operation_time_ms": self.get_average_operation_time() * 1000,
                "operation_time_percentiles": {
                    "p50_ms": percentile(times, 50) * 1000,
                    "p90_ms": percentile(times, 90) * 1000,
                    "p95_ms": percentile(times, 95) * 1000,
                    "p99_ms": percentile(times, 99) * 1000,
                },
                "operations_by_type": dict(self.operations),
                "error_rate_percent": self.get_error_rate(),
                "errors_by_operation": dict(self.errors),
                "recent_ops_per_second": self.get_operations_per_second(60),
                "memory_tracking_enabled": len(self.memory_usage_history) > 0,
            }

    def get_trend_analysis(self, window_minutes: int = 30) -> Dict[str, Any]:
        """Analyze performance trends over time"""
        with self.lock:
            now = time.time()
            cutoff_time = now - (window_minutes * 60)

            # Recent operations
            recent_ops = [
                op for op in self.operation_times if op["timestamp"] >= cutoff_time
            ]

            # Recent hit rates
            recent_hits = [
                hr for hr in self.hit_rates if hr["timestamp"] >= cutoff_time
            ]

            # Calculate trends
            hit_rate_trend = "stable"
            if len(recent_hits) >= 10:
                early_avg = sum(hr["rate"] for hr in recent_hits[:5]) / 5
                late_avg = sum(hr["rate"] for hr in recent_hits[-5:]) / 5
                if late_avg > early_avg + 5:
                    hit_rate_trend = "improving"
                elif late_avg < early_avg - 5:
                    hit_rate_trend = "degrading"

            # Memory usage trend
            memory_trend = "unknown"
            if len(self.memory_usage_history) >= 10:
                recent_memory = [
                    mem
                    for mem in self.memory_usage_history
                    if mem["timestamp"] >= cutoff_time
                ]
                if len(recent_memory) >= 10:
                    early_avg = sum(mem["bytes"] for mem in recent_memory[:5]) / 5
                    late_avg = sum(mem["bytes"] for mem in recent_memory[-5:]) / 5
                    change_percent = (
                        ((late_avg - early_avg) / early_avg * 100)
                        if early_avg > 0
                        else 0
                    )
                    if abs(change_percent) < 5:
                        memory_trend = "stable"
                    elif change_percent > 0:
                        memory_trend = "increasing"
                    else:
                        memory_trend = "decreasing"

            return {
                "analysis_window_minutes": window_minutes,
                "recent_operations_count": len(recent_ops),
                "hit_rate_trend": hit_rate_trend,
                "memory_trend": memory_trend,
                "recent_average_response_time_ms": (
                    sum(op["time"] for op in recent_ops if op["success"])
                    / len(recent_ops)
                    * 1000
                    if recent_ops
                    else 0
                ),
                "recent_error_count": len(
                    [op for op in recent_ops if not op["success"]]
                ),
                "timestamp": datetime.now().isoformat(),
            }

    def reset_metrics(self):
        """Reset all performance metrics"""
        with self.lock:
            self.operations.clear()
            self.operation_times.clear()
            self.hit_rates.clear()
            self.errors.clear()
            self.last_errors.clear()
            self.memory_usage_history.clear()

            self.total_operations = 0
            self.cache_hits = 0
            self.cache_misses = 0
            self.total_time = 0.0
            self.start_time = time.time()

            logger.info("Performance metrics reset")
