#!/usr/bin/env python3
"""
Analytics Coordinator - Main interface for the modularized analytics system
Provides backward compatibility with the original AdvancedAnalytics interface
"""

from typing import Any
from typing import Dict

from .base_analyzer import BaseAnalyzer
from .correlation_analyzer import CorrelationAnalyzer
from .network_analyzer import NetworkAnalyzer
from .predictive_analyzer import PredictiveAnalyzer
from .report_generator import ReportGenerator
from .threat_intelligence import ThreatIntelligenceAnalyzer


class AnalyticsCoordinator(BaseAnalyzer):
    """Coordinated analytics system maintaining original API compatibility"""

    def __init__(self, db_path: str = "instance/blacklist.db"):
        super().__init__(db_path)

        # Initialize all analyzers
        self.threat_analyzer = ThreatIntelligenceAnalyzer(db_path)
        self.network_analyzer = NetworkAnalyzer(db_path)
        self.correlation_analyzer = CorrelationAnalyzer(db_path)
        self.predictive_analyzer = PredictiveAnalyzer(db_path)
        self.report_generator = ReportGenerator(db_path)

    def get_threat_intelligence_report(self) -> Dict[str, Any]:
        """Get threat intelligence report - original API compatibility"""
        return self.threat_analyzer.get_threat_intelligence_report()

    def get_network_analysis(self) -> Dict[str, Any]:
        """Get network analysis - original API compatibility"""
        return self.network_analyzer.get_network_analysis()

    def get_attack_correlation_analysis(self) -> Dict[str, Any]:
        """Get attack correlation analysis - original API compatibility"""
        return self.correlation_analyzer.get_attack_correlation_analysis()

    def get_predictive_insights(self) -> Dict[str, Any]:
        """Get predictive insights - original API compatibility"""
        return self.predictive_analyzer.get_predictive_insights()

    def generate_threat_report_export(
        self, format_type: str = "json"
    ) -> Dict[str, Any]:
        """Generate threat report export - original API compatibility"""
        return self.report_generator.generate_threat_report_export(format_type)

    def get_comprehensive_analysis(self) -> Dict[str, Any]:
        """Get all analysis data in a single call - new enhanced API"""
        return {
            "threat_intelligence": self.get_threat_intelligence_report(),
            "network_analysis": self.get_network_analysis(),
            "attack_correlations": self.get_attack_correlation_analysis(),
            "predictive_insights": self.get_predictive_insights(),
            "generated_at": self._safe_execute(
                "timestamp", lambda: __import__("datetime").datetime.now().isoformat()
            ),
        }


# Maintain backward compatibility - alias for the original class name
AdvancedAnalytics = AnalyticsCoordinator


if __name__ == "__main__":
    # Comprehensive validation of the coordinated system
    import sys

    coordinator = AnalyticsCoordinator()

    all_validation_failures = []
    total_tests = 0

    print("🔍 Testing Analytics Coordinator...")

    # Test 1: Threat Intelligence
    total_tests += 1
    intelligence = coordinator.get_threat_intelligence_report()
    if not intelligence:
        all_validation_failures.append("Threat Intelligence: Empty result returned")
    elif "summary" not in intelligence:
        all_validation_failures.append("Threat Intelligence: Missing summary section")

    # Test 2: Network Analysis
    total_tests += 1
    network = coordinator.get_network_analysis()
    if not network:
        all_validation_failures.append("Network Analysis: Empty result returned")
    elif "network_summary" not in network:
        all_validation_failures.append(
            "Network Analysis: Missing network_summary section"
        )

    # Test 3: Correlation Analysis
    total_tests += 1
    correlations = coordinator.get_attack_correlation_analysis()
    if not correlations:
        all_validation_failures.append("Correlation Analysis: Empty result returned")
    elif "correlation_summary" not in correlations:
        all_validation_failures.append(
            "Correlation Analysis: Missing correlation_summary section"
        )

    # Test 4: Predictive Analysis
    total_tests += 1
    predictions = coordinator.get_predictive_insights()
    if not predictions:
        all_validation_failures.append("Predictive Analysis: Empty result returned")
    elif "trend_predictions" not in predictions:
        all_validation_failures.append(
            "Predictive Analysis: Missing trend_predictions section"
        )

    # Test 5: Report Generation
    total_tests += 1
    report = coordinator.generate_threat_report_export()
    if not report:
        all_validation_failures.append("Report Generation: Empty result returned")
    elif "report_metadata" not in report:
        all_validation_failures.append(
            "Report Generation: Missing report_metadata section"
        )

    # Test 6: Comprehensive Analysis (new API)
    total_tests += 1
    comprehensive = coordinator.get_comprehensive_analysis()
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
        print("Analytics Coordinator is validated and ready for use")
        sys.exit(0)
