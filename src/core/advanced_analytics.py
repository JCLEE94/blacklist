#!/usr/bin/env python3
"""
고급 분석 시스템 - 수집된 데이터 활용
Advanced Analytics System - Utilizing Collected Data
"""

import ipaddress
import json
import logging
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AdvancedAnalytics:
    """수집된 데이터 기반 고급 분석"""

    def __init__(self, db_path: str = "instance/blacklist.db"):
        self.db_path = db_path

    def get_threat_intelligence_report(self) -> Dict[str, Any]:
        """위협 인텔리전스 보고서"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 기본 통계
            cursor.execute("SELECT COUNT(*) FROM blacklist_entries")
            total_threats = cursor.fetchone()[0]

            # 위험도별 분포
            cursor.execute(
                """
                SELECT threat_level, COUNT(*) 
                FROM blacklist_entries 
                GROUP BY threat_level 
                ORDER BY COUNT(*) DESC
            """
            )
            threat_distribution = dict(cursor.fetchall())

            # 국가별 위협 분포 (상위 15개)
            cursor.execute(
                """
                SELECT country, COUNT(*) as count,
                       threat_level,
                       GROUP_CONCAT(DISTINCT reason) as attack_types
                FROM blacklist_entries 
                WHERE country != 'UNKNOWN'
                GROUP BY country, threat_level
                ORDER BY count DESC
                LIMIT 15
            """
            )
            geo_threats = []
            for row in cursor.fetchall():
                country, count, threat_level, attack_types = row
                geo_threats.append(
                    {
                        "country": country,
                        "threat_count": count,
                        "threat_level": threat_level,
                        "attack_types": attack_types.split(",") if attack_types else [],
                    }
                )

            # 공격 패턴 분석
            cursor.execute(
                """
                SELECT reason, COUNT(*) as frequency,
                       threat_level,
                       GROUP_CONCAT(DISTINCT country) as affected_countries
                FROM blacklist_entries 
                GROUP BY reason, threat_level
                ORDER BY frequency DESC
                LIMIT 20
            """
            )
            attack_patterns = []
            for row in cursor.fetchall():
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

            # 시간별 트렌드 (최근 30일)
            cursor.execute(
                """
                SELECT collection_date, COUNT(*) as daily_count,
                       threat_level,
                       AVG(confidence_level) as avg_confidence
                FROM blacklist_entries 
                WHERE collection_date >= date('now', '-30 days')
                GROUP BY collection_date, threat_level
                ORDER BY collection_date DESC
            """
            )
            time_trends = []
            for row in cursor.fetchall():
                date, count, level, confidence = row
                time_trends.append(
                    {
                        "date": date,
                        "count": count,
                        "threat_level": level,
                        "confidence": round(confidence or 0, 2),
                    }
                )

            conn.close()

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

        except Exception as e:
            logger.error(f"위협 인텔리전스 보고서 생성 오류: {e}")
            return {}

    def get_network_analysis(self) -> Dict[str, Any]:
        """네트워크 분석 (IP 범위, 서브넷 등)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # IP 주소 데이터 가져오기
            cursor.execute(
                "SELECT ip_address, country, threat_level FROM blacklist_entries"
            )
            ip_data = cursor.fetchall()

            # 서브넷 분석
            subnet_analysis = self._analyze_subnets(ip_data)

            # 지리적 클러스터 분석
            geo_clusters = self._analyze_geographic_clusters(ip_data)

            # ASN 분석 (가능한 경우)
            asn_analysis = self._analyze_asn_patterns(ip_data)

            conn.close()

            return {
                "subnet_analysis": subnet_analysis,
                "geographic_clusters": geo_clusters,
                "asn_analysis": asn_analysis,
                "network_summary": {
                    "total_ips": len(ip_data),
                    "unique_subnets": len(subnet_analysis.get("high_risk_subnets", [])),
                    "high_risk_countries": len(
                        [c for c in geo_clusters if c.get("risk_level") == "HIGH"]
                    ),
                },
            }

        except Exception as e:
            logger.error(f"네트워크 분석 오류: {e}")
            return {}

    def get_attack_correlation_analysis(self) -> Dict[str, Any]:
        """공격 상관관계 분석"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 공격 유형별 상관관계
            cursor.execute(
                """
                SELECT reason, country, threat_level, 
                       collection_date, COUNT(*) as frequency
                FROM blacklist_entries 
                GROUP BY reason, country, threat_level, collection_date
                HAVING frequency > 1
                ORDER BY frequency DESC
                LIMIT 50
            """
            )

            correlations = []
            for row in cursor.fetchall():
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

            # 시간적 패턴 분석
            cursor.execute(
                """
                SELECT strftime('%H', created_at) as hour,
                       COUNT(*) as count,
                       threat_level
                FROM blacklist_entries 
                WHERE created_at IS NOT NULL
                GROUP BY hour, threat_level
                ORDER BY hour
            """
            )

            temporal_patterns = defaultdict(list)
            for row in cursor.fetchall():
                hour, count, level = row
                temporal_patterns[hour].append({"threat_level": level, "count": count})

            conn.close()

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

        except Exception as e:
            logger.error(f"공격 상관관계 분석 오류: {e}")
            return {}

    def get_predictive_insights(self) -> Dict[str, Any]:
        """예측 인사이트"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 트렌드 기반 예측
            cursor.execute(
                """
                SELECT collection_date, COUNT(*) as daily_count
                FROM blacklist_entries 
                WHERE collection_date >= date('now', '-14 days')
                GROUP BY collection_date
                ORDER BY collection_date
            """
            )

            trend_data = cursor.fetchall()
            trend_prediction = self._predict_trends(trend_data)

            # 위험 지역 예측
            cursor.execute(
                """
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
            )

            risk_regions = []
            for row in cursor.fetchall():
                country, count, severity = row
                risk_regions.append(
                    {
                        "country": country,
                        "threat_count": count,
                        "avg_severity": round(severity, 2),
                        "risk_prediction": self._predict_country_risk(count, severity),
                    }
                )

            # 공격 패턴 예측
            attack_predictions = self._predict_attack_patterns()

            conn.close()

            return {
                "trend_predictions": trend_prediction,
                "risk_regions": risk_regions,
                "attack_predictions": attack_predictions,
                "recommendations": self._generate_security_recommendations(
                    risk_regions, attack_predictions
                ),
            }

        except Exception as e:
            logger.error(f"예측 인사이트 생성 오류: {e}")
            return {}

    def generate_threat_report_export(
        self, format_type: str = "json"
    ) -> Dict[str, Any]:
        """위협 보고서 내보내기"""
        try:
            # 모든 분석 데이터 수집
            intelligence = self.get_threat_intelligence_report()
            network = self.get_network_analysis()
            correlations = self.get_attack_correlation_analysis()
            predictions = self.get_predictive_insights()

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
                # CSV 형태로 변환 (간소화된 데이터)
                return self._convert_to_csv_format(comprehensive_report)
            elif format_type == "pdf":
                # PDF 생성을 위한 구조화된 데이터
                return self._prepare_for_pdf(comprehensive_report)

            return comprehensive_report

        except Exception as e:
            logger.error(f"위협 보고서 내보내기 오류: {e}")
            return {}

    def _calculate_severity_score(self, frequency: int, threat_level: str) -> float:
        """심각도 점수 계산"""
        level_weights = {"CRITICAL": 1.0, "HIGH": 0.8, "MEDIUM": 0.6, "LOW": 0.4}

        base_score = level_weights.get(threat_level, 0.5)
        frequency_factor = min(frequency / 100, 1.0)  # 정규화

        return round(base_score * (0.7 + frequency_factor * 0.3), 2)

    def _analyze_subnets(self, ip_data: List[Tuple]) -> Dict[str, Any]:
        """서브넷 분석"""
        subnet_counter = Counter()

        for ip, country, threat_level in ip_data:
            try:
                network = ipaddress.ip_network(f"{ip}/24", strict=False)
                subnet_counter[str(network)] += 1
            except:
                continue

        high_risk_subnets = [
            {"subnet": subnet, "threat_count": count}
            for subnet, count in subnet_counter.most_common(20)
            if count > 5
        ]

        return {
            "high_risk_subnets": high_risk_subnets,
            "total_subnets": len(subnet_counter),
            "avg_threats_per_subnet": (
                sum(subnet_counter.values()) / len(subnet_counter)
                if subnet_counter
                else 0
            ),
        }

    def _analyze_geographic_clusters(
        self, ip_data: List[Tuple]
    ) -> List[Dict[str, Any]]:
        """지리적 클러스터 분석"""
        country_stats = defaultdict(lambda: {"count": 0, "threat_levels": Counter()})

        for ip, country, threat_level in ip_data:
            if country and country != "UNKNOWN":
                country_stats[country]["count"] += 1
                country_stats[country]["threat_levels"][threat_level] += 1

        clusters = []
        for country, stats in country_stats.items():
            critical_ratio = stats["threat_levels"].get("CRITICAL", 0) / stats["count"]
            high_ratio = stats["threat_levels"].get("HIGH", 0) / stats["count"]

            risk_level = "LOW"
            if critical_ratio > 0.3 or high_ratio > 0.5:
                risk_level = "HIGH"
            elif critical_ratio > 0.1 or high_ratio > 0.3:
                risk_level = "MEDIUM"

            clusters.append(
                {
                    "country": country,
                    "threat_count": stats["count"],
                    "risk_level": risk_level,
                    "threat_distribution": dict(stats["threat_levels"]),
                }
            )

        return sorted(clusters, key=lambda x: x["threat_count"], reverse=True)

    def _analyze_asn_patterns(self, ip_data: List[Tuple]) -> Dict[str, Any]:
        """ASN 패턴 분석 (기본적인 분석)"""
        # 실제 ASN 데이터베이스가 없으므로 IP 범위 기반 추정
        private_ranges = 0
        public_ranges = 0

        for ip, _, _ in ip_data:
            try:
                ip_obj = ipaddress.ip_address(ip)
                if ip_obj.is_private:
                    private_ranges += 1
                else:
                    public_ranges += 1
            except:
                continue

        return {
            "private_ip_count": private_ranges,
            "public_ip_count": public_ranges,
            "private_ratio": (
                private_ranges / (private_ranges + public_ranges)
                if (private_ranges + public_ranges) > 0
                else 0
            ),
        }

    def _generate_risk_assessment(
        self, threat_dist: Dict, geo_threats: List
    ) -> Dict[str, Any]:
        """위험 평가 생성"""
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
        """위험 수준별 권장사항"""
        recommendations = {
            "CRITICAL": "즉시 보안 대응팀 알림 및 긴급 방화벽 규칙 업데이트 필요",
            "HIGH": "24시간 내 보안 정책 검토 및 추가 모니터링 설정 권장",
            "MEDIUM": "주간 보안 검토 시 고려사항으로 포함",
            "LOW": "정기 모니터링 유지",
        }
        return recommendations.get(risk_level, "추가 분석 필요")

    def _calculate_correlation_score(
        self, frequency: int, threat_level: str, country: str
    ) -> float:
        """상관관계 점수 계산"""
        base_score = 0.5

        # 빈도 가중치
        if frequency > 10:
            base_score += 0.3
        elif frequency > 5:
            base_score += 0.2

        # 위협 수준 가중치
        level_weights = {"CRITICAL": 0.3, "HIGH": 0.2, "MEDIUM": 0.1}
        base_score += level_weights.get(threat_level, 0)

        return min(base_score, 1.0)

    def _identify_peak_hours(self, temporal_patterns: Dict) -> List[str]:
        """피크 시간대 식별"""
        hour_totals = {}
        for hour, patterns in temporal_patterns.items():
            total = sum(p["count"] for p in patterns)
            hour_totals[hour] = total

        avg_total = sum(hour_totals.values()) / len(hour_totals) if hour_totals else 0
        peak_hours = [
            hour for hour, total in hour_totals.items() if total > avg_total * 1.5
        ]

        return sorted(peak_hours)

    def _predict_trends(self, trend_data: List[Tuple]) -> Dict[str, Any]:
        """트렌드 예측 (간단한 선형 추세)"""
        if len(trend_data) < 3:
            return {"prediction": "insufficient_data"}

        # 최근 7일 평균과 이전 7일 평균 비교
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

    def _predict_country_risk(self, threat_count: int, avg_severity: float) -> str:
        """국가별 위험도 예측"""
        risk_score = (threat_count / 100) * 0.6 + (avg_severity / 4) * 0.4

        if risk_score > 0.7:
            return "HIGH"
        elif risk_score > 0.4:
            return "MEDIUM"
        else:
            return "LOW"

    def _predict_attack_patterns(self) -> Dict[str, Any]:
        """공격 패턴 예측"""
        # 간단한 패턴 예측 (실제로는 더 복잡한 ML 모델 사용)
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
        """보안 권장사항 생성"""
        recommendations = []

        high_risk_countries = [
            r["country"] for r in risk_regions if r.get("risk_prediction") == "HIGH"
        ]
        if high_risk_countries:
            recommendations.append(
                f"고위험 국가({', '.join(high_risk_countries[:3])}) IP 범위에 대한 추가 모니터링 설정"
            )

        if attack_predictions.get("confidence", 0) > 0.7:
            recommendations.append("WordPress 및 Apache 서버 보안 패치 상태 점검")

        recommendations.extend(
            [
                "방화벽 규칙 정기 업데이트 (주 1회)",
                "침입 탐지 시스템(IDS) 시그니처 최신화",
                "보안 로그 분석 자동화 도구 활용",
            ]
        )

        return recommendations

    def _create_executive_summary(
        self, intelligence: Dict, network: Dict, predictions: Dict
    ) -> Dict[str, Any]:
        """경영진 요약 생성"""
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
        """CSV 형식으로 변환"""
        # CSV 변환 로직 (간소화)
        return {"format": "csv", "data": "CSV conversion not implemented in this demo"}

    def _prepare_for_pdf(self, report: Dict) -> Dict[str, Any]:
        """PDF 준비"""
        # PDF 준비 로직 (간소화)
        return {"format": "pdf", "data": "PDF preparation not implemented in this demo"}


if __name__ == "__main__":
    # 고급 분석 시스템 테스트
    analytics = AdvancedAnalytics()

    print("🔍 위협 인텔리전스 보고서 생성...")
    intelligence = analytics.get_threat_intelligence_report()
    if intelligence:
        summary = intelligence.get("summary", {})
        print(f"  - 총 위협: {summary.get('total_threats', 0)}개")
        print(f"  - 위험도 분포: {summary.get('threat_distribution', {})}")

    print("\n🌐 네트워크 분석...")
    network = analytics.get_network_analysis()
    if network:
        net_summary = network.get("network_summary", {})
        print(f"  - 총 IP: {net_summary.get('total_ips', 0)}개")
        print(f"  - 고위험 서브넷: {net_summary.get('unique_subnets', 0)}개")

    print("\n🔗 공격 상관관계 분석...")
    correlations = analytics.get_attack_correlation_analysis()
    if correlations:
        corr_summary = correlations.get("correlation_summary", {})
        print(
            f"  - 고상관관계 공격: {corr_summary.get('high_correlation_attacks', 0)}개"
        )
        print(f"  - 피크 시간대: {corr_summary.get('peak_hours', [])}")

    print("\n🔮 예측 인사이트...")
    predictions = analytics.get_predictive_insights()
    if predictions:
        trend = predictions.get("trend_predictions", {})
        print(f"  - 트렌드 방향: {trend.get('trend_direction', 'unknown')}")
        print(f"  - 변화율: {trend.get('change_rate', 0)*100:.1f}%")

        recs = predictions.get("recommendations", [])
        print(f"  - 권장사항: {len(recs)}개")
