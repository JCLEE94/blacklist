#!/usr/bin/env python3
"""
Correlation Analyzer - Attack correlation and temporal pattern analysis
Analyzes relationships between attacks and identifies patterns over time
"""

from collections import defaultdict
from typing import Any
from typing import Dict
from typing import List

from .base_analyzer import BaseAnalyzer


class CorrelationAnalyzer(BaseAnalyzer):
    """Analyzes attack correlations and temporal patterns"""

    def get_attack_correlation_analysis(self) -> Dict[str, Any]:
        """Comprehensive attack correlation analysis"""
        return self._safe_execute(
            "Correlation Analysis", self._perform_correlation_analysis
        )

    def _perform_correlation_analysis(self) -> Dict[str, Any]:
        """Internal correlation analysis logic"""
        # Attack type correlations
        correlations = self._get_attack_correlations()

        # Temporal patterns
        temporal_patterns = self._get_temporal_patterns()

        return {
            "attack_correlations": correlations,
            "temporal_patterns": dict(temporal_patterns),
            "correlation_summary": {
                "high_correlation_attacks": len(
                    [c for c in correlations if c["correlation_score"] > 0.7]
                ),
                "peak_hours": self._identify_peak_hours(temporal_patterns),
            },
        }

    def _get_attack_correlations(self) -> List[Dict[str, Any]]:
        """Get attack type correlations by frequency and geography"""
        query = """
            SELECT reason, country, threat_level, 
                   collection_date, COUNT(*) as frequency
            FROM blacklist_entries 
            GROUP BY reason, country, threat_level, collection_date
            HAVING frequency > 1
            ORDER BY frequency DESC
            LIMIT 50
        """
        result = self._execute_query(query)

        correlations = []
        for row in result:
            reason, country, level, date, freq = row
            correlations.append(
                {
                    "attack_type": reason,
                    "country": country,
                    "threat_level": level,
                    "date": date,
                    "frequency": freq,
                    "correlation_score": self._calculate_correlation_score(
                        freq, level, country
                    ),
                }
            )

        return correlations

    def _get_temporal_patterns(self) -> defaultdict:
        """Analyze temporal attack patterns by hour"""
        query = """
            SELECT strftime('%H', created_at) as hour,
                   COUNT(*) as count,
                   threat_level
            FROM blacklist_entries 
            WHERE created_at IS NOT NULL
            GROUP BY hour, threat_level
            ORDER BY hour
        """
        result = self._execute_query(query)

        temporal_patterns = defaultdict(list)
        for row in result:
            hour, count, level = row
            temporal_patterns[hour].append({"threat_level": level, "count": count})

        return temporal_patterns

    def _calculate_correlation_score(
        self, frequency: int, threat_level: str, country: str
    ) -> float:
        """Calculate correlation score based on multiple factors"""
        base_score = 0.5

        # Frequency weight
        if frequency > 10:
            base_score += 0.3
        elif frequency > 5:
            base_score += 0.2

        # Threat level weight
        level_weights = {"CRITICAL": 0.3, "HIGH": 0.2, "MEDIUM": 0.1}
        base_score += level_weights.get(threat_level, 0)

        return min(base_score, 1.0)

    def _identify_peak_hours(self, temporal_patterns: Dict) -> List[str]:
        """Identify peak attack hours"""
        hour_totals = {}
        for hour, patterns in temporal_patterns.items():
            total = sum(p["count"] for p in patterns)
            hour_totals[hour] = total

        avg_total = sum(hour_totals.values()) / len(hour_totals) if hour_totals else 0
        peak_hours = [
            hour for hour, total in hour_totals.items() if total > avg_total * 1.5
        ]

        return sorted(peak_hours)


if __name__ == "__main__":
    # Validation function
    analyzer = CorrelationAnalyzer()
    print("🔗 Testing Correlation Analyzer...")

    result = analyzer.get_attack_correlation_analysis()
    if result:
        corr_summary = result.get("correlation_summary", {})
        print(
            f"  - High correlation attacks: {corr_summary.get('high_correlation_attacks', 0)}"
        )
        print(f"  - Peak hours: {corr_summary.get('peak_hours', [])}")
        print("✅ Correlation Analyzer validation successful")
    else:
        print("❌ Correlation Analyzer validation failed")
