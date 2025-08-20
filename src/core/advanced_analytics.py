#!/usr/bin/env python3
"""
Advanced Analytics System - Legacy compatibility wrapper
Maintains backward compatibility while using the new modular analytics system

This module now acts as a compatibility layer, delegating to the new 
modular analytics system in src/core/analytics/
"""

import logging
from typing import Any, Dict

# Import the new modular coordinator
from .analytics.analytics_coordinator import AnalyticsCoordinator

logger = logging.getLogger(__name__)


class AdvancedAnalytics:
    """Legacy compatibility wrapper for the modular analytics system"""

    def __init__(self, db_path: str = "instance/blacklist.db"):
        """Initialize with the new modular coordinator"""
        self._coordinator = AnalyticsCoordinator(db_path)

    def get_threat_intelligence_report(self) -> Dict[str, Any]:
        """Get threat intelligence report - delegates to modular system"""
        return self._coordinator.get_threat_intelligence_report()

    def get_network_analysis(self) -> Dict[str, Any]:
        """Get network analysis - delegates to modular system"""
        return self._coordinator.get_network_analysis()

    def get_attack_correlation_analysis(self) -> Dict[str, Any]:
        """Get attack correlation analysis - delegates to modular system"""
        return self._coordinator.get_attack_correlation_analysis()

    def get_predictive_insights(self) -> Dict[str, Any]:
        """Get predictive insights - delegates to modular system"""
        return self._coordinator.get_predictive_insights()

    def generate_threat_report_export(
        self, format_type: str = "json"
    ) -> Dict[str, Any]:
        """Generate threat report export - delegates to modular system"""
        return self._coordinator.generate_threat_report_export(format_type)

    def get_comprehensive_analysis(self) -> Dict[str, Any]:
        """Get comprehensive analysis - new enhanced API"""
        return self._coordinator.get_comprehensive_analysis()

    # Legacy method aliases for backward compatibility
    def _calculate_severity_score(self, frequency: int, threat_level: str) -> float:
        """Legacy method - now handled by base analyzer"""
        return self._coordinator.threat_analyzer._calculate_severity_score(
            frequency, threat_level
        )


if __name__ == "__main__":
    # Advanced Analytics System validation using new modular architecture
    import sys

    analytics = AdvancedAnalytics()

    all_validation_failures = []
    total_tests = 0

    print("🔍 Testing Advanced Analytics (Modular Version)...")

    # Test 1: Threat Intelligence Report
    total_tests += 1
    intelligence = analytics.get_threat_intelligence_report()
    if not intelligence:
        all_validation_failures.append("Threat Intelligence: Empty result returned")
    elif not isinstance(intelligence.get("summary", {}), dict):
        all_validation_failures.append("Threat Intelligence: Invalid summary structure")
    else:
        summary = intelligence.get("summary", {})
        print(f"  - Total threats: {summary.get('total_threats', 0)}")
        print(f"  - Threat distribution: {summary.get('threat_distribution', {})}")

    # Test 2: Network Analysis
    total_tests += 1
    network = analytics.get_network_analysis()
    if not network:
        all_validation_failures.append("Network Analysis: Empty result returned")
    elif not isinstance(network.get("network_summary", {}), dict):
        all_validation_failures.append(
            "Network Analysis: Invalid network_summary structure"
        )
    else:
        net_summary = network.get("network_summary", {})
        print(f"  - Total IPs: {net_summary.get('total_ips', 0)}")
        print(f"  - High-risk subnets: {net_summary.get('unique_subnets', 0)}")

    # Test 3: Attack Correlation Analysis
    total_tests += 1
    correlations = analytics.get_attack_correlation_analysis()
    if not correlations:
        all_validation_failures.append("Correlation Analysis: Empty result returned")
    elif not isinstance(correlations.get("correlation_summary", {}), dict):
        all_validation_failures.append(
            "Correlation Analysis: Invalid correlation_summary structure"
        )
    else:
        corr_summary = correlations.get("correlation_summary", {})
        print(
            f"  - High correlation attacks: {corr_summary.get('high_correlation_attacks', 0)}"
        )
        print(f"  - Peak hours: {corr_summary.get('peak_hours', [])}")

    # Test 4: Predictive Insights
    total_tests += 1
    predictions = analytics.get_predictive_insights()
    if not predictions:
        all_validation_failures.append("Predictive Insights: Empty result returned")
    elif not isinstance(predictions.get("trend_predictions", {}), dict):
        all_validation_failures.append(
            "Predictive Insights: Invalid trend_predictions structure"
        )
    else:
        trend = predictions.get("trend_predictions", {})
        print(f"  - Trend direction: {trend.get('trend_direction', 'unknown')}")
        print(f"  - Change rate: {trend.get('change_rate', 0)*100:.1f}%")
        recs = predictions.get("recommendations", [])
        print(f"  - Recommendations: {len(recs)} items")

    # Test 5: Report Generation
    total_tests += 1
    report = analytics.generate_threat_report_export()
    if not report:
        all_validation_failures.append("Report Export: Empty result returned")
    elif not isinstance(report.get("report_metadata", {}), dict):
        all_validation_failures.append(
            "Report Export: Invalid report_metadata structure"
        )

    # Test 6: New Enhanced API
    total_tests += 1
    comprehensive = analytics.get_comprehensive_analysis()
    if not comprehensive:
        all_validation_failures.append("Comprehensive Analysis: Empty result returned")
    elif len(comprehensive.keys()) < 4:
        all_validation_failures.append(
            "Comprehensive Analysis: Missing analysis sections"
        )

    # Final validation result
    if all_validation_failures:
        print(
            f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print("Advanced Analytics (Modular) is validated and ready for production use")
        sys.exit(0)
