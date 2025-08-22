"""
Statistics Service Mixins - Modular components for UnifiedStatisticsService

Follows shrimp-rules.md: 500-line file limit enforcement through mixin decomposition.
"""

from .database_statistics_mixin import DatabaseStatisticsMixin
from .source_statistics_mixin import SourceStatisticsMixin
from .system_health_mixin import SystemHealthMixin
from .trend_analytics_mixin import TrendAnalyticsMixin

__all__ = [
    "DatabaseStatisticsMixin",
    "TrendAnalyticsMixin",
    "SourceStatisticsMixin",
    "SystemHealthMixin",
]
