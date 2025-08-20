#!/usr/bin/env python3
"""
Threat Intelligence Analyzer - Core threat analysis functionality
Provides threat distribution, geographic analysis, and attack patterns
"""

from datetime import datetime
from typing import Any, Dict, List

from .base_analyzer import BaseAnalyzer


class ThreatIntelligenceAnalyzer(BaseAnalyzer):
    """Analyzes threat intelligence from collected data"""

    def get_threat_intelligence_report(self) -> Dict[str, Any]:
        """Generate comprehensive threat intelligence report"""
        return self._safe_execute("Threat Intelligence", self._generate_threat_report)

    def _generate_threat_report(self) -> Dict[str, Any]:
        """Internal threat report generation"""
        # Basic statistics
        total_threats = self._get_total_threats()
        threat_distribution = self._get_threat_distribution()

        # Geographic analysis
        geo_threats = self._get_geographic_threats()

        # Attack patterns
        attack_patterns = self._get_attack_patterns()

        # Time trends
        time_trends = self._get_time_trends()

        return {
            "summary": {
                "total_threats": total_threats,
                "threat_distribution": threat_distribution,
                "analysis_date": datetime.now().isoformat(),
            },
            "geographic_analysis": geo_threats,
            "attack_patterns": attack_patterns,
            "time_trends": time_trends,
            "risk_assessment": self._generate_risk_assessment(
                threat_distribution, geo_threats
            ),
        }

    def _get_total_threats(self) -> int:
        """Get total number of threats"""
        result = self._execute_query("SELECT COUNT(*) FROM blacklist_entries")
        return result[0][0] if result else 0

    def _get_threat_distribution(self) -> Dict[str, int]:
        """Get threat level distribution"""
        query = """
            SELECT threat_level, COUNT(*)
            FROM blacklist_entries
            GROUP BY threat_level
            ORDER BY COUNT(*) DESC
        """
        result = self._execute_query(query)
        return dict(result)

    def _get_geographic_threats(self) -> List[Dict[str, Any]]:
        """Get geographic threat analysis (top 15 countries)"""
        query = """
            SELECT country, COUNT(*) as count,
                   threat_level,
                   GROUP_CONCAT(DISTINCT reason) as attack_types
            FROM blacklist_entries
            WHERE country != 'UNKNOWN'
            GROUP BY country, threat_level
            ORDER BY count DESC
            LIMIT 15
        """
        result = self._execute_query(query)

        geo_threats = []
        for row in result:
            country, count, threat_level, attack_types = row
            geo_threats.append(
                {
                    "country": country,
                    "threat_count": count,
                    "threat_level": threat_level,
                    "attack_types": attack_types.split(",") if attack_types else [],
                }
            )
        return geo_threats

    def _get_attack_patterns(self) -> List[Dict[str, Any]]:
        """Analyze attack patterns by type and frequency"""
        query = """
            SELECT reason, COUNT(*) as frequency,
                   threat_level,
                   GROUP_CONCAT(DISTINCT country) as affected_countries
            FROM blacklist_entries
            GROUP BY reason, threat_level
            ORDER BY frequency DESC
            LIMIT 20
        """
        result = self._execute_query(query)

        attack_patterns = []
        for row in result:
            reason, freq, level, countries = row
            attack_patterns.append(
                {
                    "attack_type": reason,
                    "frequency": freq,
                    "threat_level": level,
                    "affected_countries": countries.split(",") if countries else [],
                    "severity_score": self._calculate_severity_score(freq, level),
                }
            )
        return attack_patterns

    def _get_time_trends(self) -> List[Dict[str, Any]]:
        """Get time-based threat trends (last 30 days)"""
        query = """
            SELECT collection_date, COUNT(*) as daily_count,
                   threat_level,
                   AVG(confidence_level) as avg_confidence
            FROM blacklist_entries
            WHERE collection_date >= date('now', '-30 days')
            GROUP BY collection_date, threat_level
            ORDER BY collection_date DESC
        """
        result = self._execute_query(query)

        time_trends = []
        for row in result:
            date, count, level, confidence = row
            time_trends.append(
                {
                    "date": date,
                    "count": count,
                    "threat_level": level,
                    "confidence": round(confidence or 0, 2),
                }
            )
        return time_trends

    def _generate_risk_assessment(
        self, threat_dist: Dict, geo_threats: List
    ) -> Dict[str, Any]:
        """Generate overall risk assessment"""
        total_threats = sum(threat_dist.values()) if threat_dist else 0
        critical_ratio = (
            threat_dist.get("CRITICAL", 0) / total_threats if total_threats > 0 else 0
        )

        risk_level = "LOW"
        if critical_ratio > 0.2:
            risk_level = "CRITICAL"
        elif critical_ratio > 0.1:
            risk_level = "HIGH"
        elif critical_ratio > 0.05:
            risk_level = "MEDIUM"

        return {
            "overall_risk_level": risk_level,
            "critical_threat_ratio": round(critical_ratio, 3),
            "high_risk_countries": len(
                [g for g in geo_threats if g.get("threat_count", 0) > 50]
            ),
            "recommendation": self._get_risk_recommendation(risk_level),
        }

    def _get_risk_recommendation(self, risk_level: str) -> str:
        """Get risk-based recommendations"""
        recommendations = {
            "CRITICAL": "즉시 보안 대응팀 알림 및 긴급 방화벽 규칙 업데이트 필요",
            "HIGH": "24시간 내 보안 정책 검토 및 추가 모니터링 설정 권장",
            "MEDIUM": "주간 보안 검토 시 고려사항으로 포함",
            "LOW": "정기 모니터링 유지",
        }
        return recommendations.get(risk_level, "추가 분석 필요")


if __name__ == "__main__":
    # Validation function
    analyzer = ThreatIntelligenceAnalyzer()
    print("🔍 Testing Threat Intelligence Analyzer...")

    result = analyzer.get_threat_intelligence_report()
    if result:
        summary = result.get("summary", {})
        print(f"  - Total threats: {summary.get('total_threats', 0)}")
        print(f"  - Threat distribution: {summary.get('threat_distribution', {})}")
        print("✅ Threat Intelligence Analyzer validation successful")
    else:
        print("❌ Threat Intelligence Analyzer validation failed")
