#!/usr/bin/env python3
"""
Predictive Analyzer - Trend prediction and risk forecasting
Provides predictive insights based on historical threat data
"""

from typing import Any, Dict, List, Tuple

from .base_analyzer import BaseAnalyzer


class PredictiveAnalyzer(BaseAnalyzer):
    """Analyzes trends and provides predictive insights"""
    
    def get_predictive_insights(self) -> Dict[str, Any]:
        """Generate predictive insights and forecasts"""
        return self._safe_execute(
            "Predictive Analysis",
            self._generate_predictions
        )
        
    def _generate_predictions(self) -> Dict[str, Any]:
        """Internal prediction generation logic"""
        # Trend predictions
        trend_data = self._get_trend_data()
        trend_prediction = self._predict_trends(trend_data)
        
        # Risk region predictions
        risk_regions = self._predict_risk_regions()
        
        # Attack pattern predictions
        attack_predictions = self._predict_attack_patterns()
        
        return {
            "trend_predictions": trend_prediction,
            "risk_regions": risk_regions,
            "attack_predictions": attack_predictions,
            "recommendations": self._generate_security_recommendations(
                risk_regions, attack_predictions
            ),
        }
        
    def _get_trend_data(self) -> List[Tuple]:
        """Get trend data for the last 14 days"""
        query = """
            SELECT collection_date, COUNT(*) as daily_count
            FROM blacklist_entries 
            WHERE collection_date >= date('now', '-14 days')
            GROUP BY collection_date
            ORDER BY collection_date
        """
        return self._execute_query(query)
        
    def _predict_trends(self, trend_data: List[Tuple]) -> Dict[str, Any]:
        """Predict future trends based on recent data"""
        if len(trend_data) < 3:
            return {"prediction": "insufficient_data"}
            
        # Compare recent 7 days with previous 7 days
        recent_avg = sum(row[1] for row in trend_data[-7:]) / min(7, len(trend_data))
        previous_avg = (
            sum(row[1] for row in trend_data[-14:-7]) / min(7, len(trend_data) - 7)
            if len(trend_data) > 7
            else recent_avg
        )
        
        trend_direction = "stable"
        change_rate = 0
        
        if previous_avg > 0:
            change_rate = (recent_avg - previous_avg) / previous_avg
            if change_rate > 0.1:
                trend_direction = "increasing"
            elif change_rate < -0.1:
                trend_direction = "decreasing"
                
        return {
            "trend_direction": trend_direction,
            "change_rate": round(change_rate, 3),
            "recent_avg": round(recent_avg, 1),
            "prediction_confidence": 0.7 if len(trend_data) > 10 else 0.5,
        }
        
    def _predict_risk_regions(self) -> List[Dict[str, Any]]:
        """Predict high-risk regions based on recent activity"""
        query = """
            SELECT country, COUNT(*) as threat_count,
                   AVG(CASE 
                       WHEN threat_level = 'CRITICAL' THEN 4
                       WHEN threat_level = 'HIGH' THEN 3
                       WHEN threat_level = 'MEDIUM' THEN 2
                       ELSE 1 END) as avg_severity
            FROM blacklist_entries 
            WHERE collection_date >= date('now', '-7 days')
            GROUP BY country
            HAVING threat_count > 5
            ORDER BY avg_severity DESC, threat_count DESC
        """
        result = self._execute_query(query)
        
        risk_regions = []
        for row in result:
            country, count, severity = row
            risk_regions.append({
                "country": country,
                "threat_count": count,
                "avg_severity": round(severity, 2),
                "risk_prediction": self._predict_country_risk(count, severity),
            })
            
        return risk_regions
        
    def _predict_country_risk(self, threat_count: int, avg_severity: float) -> str:
        """Predict country risk level"""
        risk_score = (threat_count / 100) * 0.6 + (avg_severity / 4) * 0.4
        
        if risk_score > 0.7:
            return "HIGH"
        elif risk_score > 0.4:
            return "MEDIUM"
        else:
            return "LOW"
            
    def _predict_attack_patterns(self) -> Dict[str, Any]:
        """Predict likely attack patterns"""
        # Simplified pattern prediction - in production would use ML models
        return {
            "predicted_attack_types": [
                "WordPress 인증우회 공격",
                "Apache HTTP Server 경로우회 공격",
            ],
            "confidence": 0.75,
            "time_horizon": "7_days",
        }
        
    def _generate_security_recommendations(
        self, risk_regions: List, attack_predictions: Dict
    ) -> List[str]:
        """Generate security recommendations based on predictions"""
        recommendations = []
        
        high_risk_countries = [
            r["country"] for r in risk_regions 
            if r.get("risk_prediction") == "HIGH"
        ]
        
        if high_risk_countries:
            recommendations.append(
                f"고위험 국가({', '.join(high_risk_countries[:3])}) IP 범위에 대한 추가 모니터링 설정"
            )
            
        if attack_predictions.get("confidence", 0) > 0.7:
            recommendations.append("WordPress 및 Apache 서버 보안 패치 상태 점검")
            
        recommendations.extend([
            "방화벽 규칙 정기 업데이트 (주 1회)",
            "침입 탐지 시스템(IDS) 시그니처 최신화",
            "보안 로그 분석 자동화 도구 활용",
        ])
        
        return recommendations


if __name__ == "__main__":
    # Validation function
    analyzer = PredictiveAnalyzer()
    print("🔮 Testing Predictive Analyzer...")
    
    result = analyzer.get_predictive_insights()
    if result:
        trend = result.get("trend_predictions", {})
        print(f"  - Trend direction: {trend.get('trend_direction', 'unknown')}")
        print(f"  - Change rate: {trend.get('change_rate', 0)*100:.1f}%")
        recs = result.get("recommendations", [])
        print(f"  - Recommendations: {len(recs)} items")
        print("✅ Predictive Analyzer validation successful")
    else:
        print("❌ Predictive Analyzer validation failed")