#!/usr/bin/env python3
"""
Report Generator - Comprehensive threat report generation
Generates exportable reports in various formats
"""

from datetime import datetime
from typing import Any, Dict

from .base_analyzer import BaseAnalyzer


class ReportGenerator(BaseAnalyzer):
    """Generates comprehensive threat reports"""

    def generate_threat_report_export(
        self, format_type: str = "json"
    ) -> Dict[str, Any]:
        """Generate comprehensive threat report for export"""
        return self._safe_execute(
            "Report Generation",
            lambda: self._generate_comprehensive_report(format_type),
        )

    def _generate_comprehensive_report(self, format_type: str) -> Dict[str, Any]:
        """Internal comprehensive report generation"""
        # Import other analyzers to gather all data
        from .correlation_analyzer import CorrelationAnalyzer
        from .network_analyzer import NetworkAnalyzer
        from .predictive_analyzer import PredictiveAnalyzer
        from .threat_intelligence import ThreatIntelligenceAnalyzer

        # Collect all analysis data
        threat_analyzer = ThreatIntelligenceAnalyzer(self.db_path)
        network_analyzer = NetworkAnalyzer(self.db_path)
        correlation_analyzer = CorrelationAnalyzer(self.db_path)
        predictive_analyzer = PredictiveAnalyzer(self.db_path)

        intelligence = threat_analyzer.get_threat_intelligence_report()
        network = network_analyzer.get_network_analysis()
        correlations = correlation_analyzer.get_attack_correlation_analysis()
        predictions = predictive_analyzer.get_predictive_insights()

        comprehensive_report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "report_type": "comprehensive_threat_analysis",
                "format": format_type,
                "version": "1.0",
            },
            "executive_summary": self._create_executive_summary(
                intelligence, network, predictions
            ),
            "threat_intelligence": intelligence,
            "network_analysis": network,
            "attack_correlations": correlations,
            "predictive_insights": predictions,
        }

        if format_type == "csv":
            return self._convert_to_csv_format(comprehensive_report)
        elif format_type == "pdf":
            return self._prepare_for_pdf(comprehensive_report)

        return comprehensive_report

    def _create_executive_summary(
        self, intelligence: Dict, network: Dict, predictions: Dict
    ) -> Dict[str, Any]:
        """Create executive summary for leadership"""
        total_threats = intelligence.get("summary", {}).get("total_threats", 0)
        risk_level = intelligence.get("risk_assessment", {}).get(
            "overall_risk_level", "UNKNOWN"
        )

        return {
            "total_threats_identified": total_threats,
            "overall_risk_level": risk_level,
            "key_findings": [
                f"총 {total_threats}개의 위협 IP 식별",
                f"전체 위험 수준: {risk_level}",
                f"고위험 서브넷 {len(network.get('subnet_analysis', {}).get('high_risk_subnets', []))}개 발견",
            ],
            "immediate_actions_required": risk_level in ["CRITICAL", "HIGH"],
        }

    def _convert_to_csv_format(self, report: Dict) -> Dict[str, Any]:
        """Convert report to CSV format structure"""
        # Simplified CSV conversion - in production would generate actual CSV
        return {"format": "csv", "data": "CSV conversion not implemented in this demo"}

    def _prepare_for_pdf(self, report: Dict) -> Dict[str, Any]:
        """Prepare report for PDF generation"""
        # Simplified PDF preparation - in production would format for PDF
        return {"format": "pdf", "data": "PDF preparation not implemented in this demo"}


if __name__ == "__main__":
    # Validation function
    generator = ReportGenerator()
    print("📊 Testing Report Generator...")

    result = generator.generate_threat_report_export()
    if result:
        metadata = result.get("report_metadata", {})
        print(f"  - Report type: {metadata.get('report_type', 'unknown')}")
        print(f"  - Generated at: {metadata.get('generated_at', 'unknown')}")
        summary = result.get("executive_summary", {})
        print(f"  - Total threats: {summary.get('total_threats_identified', 0)}")
        print("✅ Report Generator validation successful")
    else:
        print("❌ Report Generator validation failed")
