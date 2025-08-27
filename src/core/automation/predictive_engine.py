"""
예측적 문제 감지 엔진

AI 자동화 플랫폼의 고급 예측 분석 시스템
- 머신러닝 기반 패턴 인식
- 시계열 데이터 분석 및 예측
- 이상 징후 조기 감지
- 자동화 실패 위험 예측
"""

import logging
import statistics
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

try:
    from src.core.automation.korean_alert_system import get_korean_alert_system
    from src.utils.structured_logging import get_logger
except ImportError:

    def get_logger(name):
        return logging.getLogger(name)

    def get_korean_alert_system():
        return None


logger = get_logger(__name__)


class PredictionType(Enum):
    """예측 유형"""

    TREND_ANALYSIS = "trend_analysis"
    ANOMALY_DETECTION = "anomaly_detection"
    FAILURE_PREDICTION = "failure_prediction"
    RESOURCE_FORECASTING = "resource_forecasting"
    AUTOMATION_SUCCESS = "automation_success"
    MERGE_CONFLICT_RISK = "merge_conflict_risk"


class RiskLevel(Enum):
    """위험 수준"""

    VERY_LOW = "very_low"  # 0-20%
    LOW = "low"  # 20-40%
    MEDIUM = "medium"  # 40-60%
    HIGH = "high"  # 60-80%
    VERY_HIGH = "very_high"  # 80-100%


@dataclass
class PredictionResult:
    """예측 결과"""

    prediction_type: PredictionType
    timestamp: datetime
    metric_name: str
    current_value: float
    predicted_value: float
    confidence: float
    risk_level: RiskLevel
    time_horizon: timedelta
    factors: List[str]
    recommendations: List[str]
    metadata: Dict[str, Any] = None


@dataclass
class AnomalyScore:
    """이상 징후 점수"""

    metric_name: str
    timestamp: datetime
    value: float
    anomaly_score: float
    threshold: float
    is_anomaly: bool
    severity: str
    context: Dict[str, Any] = None


class TimeSeriesAnalyzer:
    """시계열 데이터 분석기"""

    def __init__(self, window_size: int = 20):
        self.window_size = window_size

    def detect_trend(self, values: List[float]) -> Tuple[str, float]:
        """트렌드 감지 (선형 회귀 기반)"""
        if len(values) < 3:
            return "stable", 0.0

        n = len(values)
        x = list(range(n))

        # 선형 회귀 계산
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stable", 0.0

        slope = numerator / denominator

        # 트렌드 분류
        if slope > 0.1:
            return "increasing", slope
        elif slope < -0.1:
            return "decreasing", slope
        else:
            return "stable", slope

    def calculate_volatility(self, values: List[float]) -> float:
        """변동성 계산 (표준편차 기반)"""
        if len(values) < 2:
            return 0.0
        return statistics.stdev(values)

    def detect_seasonality(self, values: List[float], period: int = 7) -> bool:
        """계절성 패턴 감지"""
        if len(values) < period * 2:
            return False

        # 자기상관 계산 (단순화된 버전)
        correlations = []
        for lag in range(1, min(period + 1, len(values) // 2)):
            corr = self._calculate_autocorrelation(values, lag)
            correlations.append(corr)

        # 강한 주기적 패턴이 있으면 True
        max_correlation = max(correlations) if correlations else 0
        return max_correlation > 0.6

    def _calculate_autocorrelation(self, values: List[float], lag: int) -> float:
        """자기상관 계산"""
        n = len(values)
        if lag >= n:
            return 0.0

        mean_val = statistics.mean(values)

        numerator = sum(
            (values[i] - mean_val) * (values[i - lag] - mean_val) for i in range(lag, n)
        )
        denominator = sum((values[i] - mean_val) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        return numerator / denominator

    def predict_next_values(self, values: List[float], horizon: int = 5) -> List[float]:
        """다음 값들 예측 (단순 이동평균 + 트렌드)"""
        if len(values) < 3:
            return [values[-1]] * horizon if values else [0] * horizon

        # 최근 트렌드 계산
        trend, slope = self.detect_trend(values[-min(10, len(values)) :])

        # 이동평균 계산
        window = min(5, len(values))
        moving_avg = statistics.mean(values[-window:])

        # 예측값 생성
        predictions = []
        for i in range(1, horizon + 1):
            predicted = moving_avg + (slope * i)
            predictions.append(predicted)

        return predictions


class AnomalyDetector:
    """이상 징후 탐지기"""

    def __init__(self):
        self.baseline_windows = defaultdict(deque)
        self.anomaly_thresholds = {
            "git_changes": (50, 100),  # (warning, critical)
            "test_coverage": (30, 15),  # 낮을수록 나쁨
            "api_response_time": (100, 200),
            "memory_usage": (70, 85),
            "cpu_usage": (70, 85),
            "file_violations": (3, 5),
        }

    def update_baseline(self, metric_name: str, value: float, max_size: int = 100):
        """기준선 데이터 업데이트"""
        if metric_name not in self.baseline_windows:
            self.baseline_windows[metric_name] = deque(maxlen=max_size)

        self.baseline_windows[metric_name].append(
            {"value": value, "timestamp": datetime.now()}
        )

    def detect_anomaly(self, metric_name: str, current_value: float) -> AnomalyScore:
        """이상 징후 감지"""
        baseline = self.baseline_windows.get(metric_name, deque())

        if len(baseline) < 5:
            # 데이터 부족시 임계값 기반 검사
            return self._threshold_based_detection(metric_name, current_value)

        # 통계적 이상 감지
        values = [item["value"] for item in baseline]
        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values) if len(values) > 1 else 0

        # Z-score 계산
        z_score = abs(current_value - mean_val) / std_val if std_val > 0 else 0

        # 이상 점수 계산 (0-1 범위)
        anomaly_score = min(z_score / 3.0, 1.0)  # 3-sigma 기준으로 정규화

        # 이상 여부 판단
        is_anomaly = z_score > 2.5  # 2.5-sigma 이상

        # 심각도 계산
        if z_score > 3.5:
            severity = "critical"
        elif z_score > 2.5:
            severity = "high"
        elif z_score > 2.0:
            severity = "medium"
        else:
            severity = "low"

        return AnomalyScore(
            metric_name=metric_name,
            timestamp=datetime.now(),
            value=current_value,
            anomaly_score=anomaly_score,
            threshold=mean_val + (2.5 * std_val),
            is_anomaly=is_anomaly,
            severity=severity,
            context={
                "baseline_mean": mean_val,
                "baseline_std": std_val,
                "z_score": z_score,
                "baseline_size": len(baseline),
            },
        )

    def _threshold_based_detection(
        self, metric_name: str, value: float
    ) -> AnomalyScore:
        """임계값 기반 이상 감지"""
        thresholds = self.anomaly_thresholds.get(metric_name, (50, 100))
        warning_threshold, critical_threshold = thresholds

        # 테스트 커버리지는 역방향 (낮을수록 나쁨)
        if metric_name == "test_coverage":
            if value <= critical_threshold:
                anomaly_score = 1.0
                is_anomaly = True
                severity = "critical"
            elif value <= warning_threshold:
                anomaly_score = 0.7
                is_anomaly = True
                severity = "high"
            else:
                anomaly_score = 0.0
                is_anomaly = False
                severity = "low"
        else:
            # 일반 메트릭 (높을수록 나쁨)
            if value >= critical_threshold:
                anomaly_score = 1.0
                is_anomaly = True
                severity = "critical"
            elif value >= warning_threshold:
                anomaly_score = 0.7
                is_anomaly = True
                severity = "high"
            else:
                anomaly_score = max(0, value / warning_threshold - 0.5)
                is_anomaly = False
                severity = "low"

        return AnomalyScore(
            metric_name=metric_name,
            timestamp=datetime.now(),
            value=value,
            anomaly_score=anomaly_score,
            threshold=critical_threshold,
            is_anomaly=is_anomaly,
            severity=severity,
            context={"method": "threshold_based", "thresholds": thresholds},
        )


class AutomationRiskPredictor:
    """자동화 위험 예측기"""

    def __init__(self):
        self.risk_factors = {
            "git_changes_high": 0.3,  # Git 변경사항 많음
            "test_coverage_low": 0.4,  # 테스트 커버리지 낮음
            "file_violations": 0.2,  # 파일 크기 위반
            "api_performance_bad": 0.25,  # API 성능 나쁨
            "memory_pressure": 0.2,  # 메모리 압박
            "recent_failures": 0.5,  # 최근 실패 이력
            "complex_changes": 0.35,  # 복잡한 변경사항
            "weekend_deployment": 0.15,  # 주말/야간 작업
            "dependency_conflicts": 0.4,  # 의존성 충돌
        }

        self.success_history = deque(maxlen=50)

    def predict_automation_success(
        self, current_metrics: Dict[str, float], automation_context: Dict[str, Any]
    ) -> PredictionResult:
        """자동화 성공 확률 예측"""

        risk_score = 0.0
        active_factors = []

        # 각 위험 요소 평가
        if current_metrics.get("git_changes", 0) > 100:
            risk_score += self.risk_factors["git_changes_high"]
            active_factors.append("Git 변경사항 과다 (100개 초과)")

        if current_metrics.get("test_coverage", 100) < 30:
            risk_score += self.risk_factors["test_coverage_low"]
            active_factors.append("테스트 커버리지 부족 (30% 미만)")

        if current_metrics.get("file_violations", 0) > 3:
            risk_score += self.risk_factors["file_violations"]
            active_factors.append("파일 크기 위반 존재")

        if current_metrics.get("api_response_time", 0) > 200:
            risk_score += self.risk_factors["api_performance_bad"]
            active_factors.append("API 성능 저하 (200ms 초과)")

        if current_metrics.get("memory_usage", 0) > 80:
            risk_score += self.risk_factors["memory_pressure"]
            active_factors.append("메모리 사용률 높음 (80% 초과)")

        # 최근 실패 이력 확인
        recent_failures = self._count_recent_failures()
        if recent_failures > 2:
            risk_score += self.risk_factors["recent_failures"]
            active_factors.append(f"최근 {recent_failures}회 실패 이력")

        # 시간대 위험 요소 (주말/야간)
        if self._is_risky_time():
            risk_score += self.risk_factors["weekend_deployment"]
            active_factors.append("위험 시간대 작업 (주말/야간)")

        # 복잡성 평가
        complexity_score = self._evaluate_complexity(automation_context)
        if complexity_score > 0.7:
            risk_score += self.risk_factors["complex_changes"]
            active_factors.append("높은 복잡도 변경사항")

        # 성공 확률 계산 (위험 점수를 확률로 변환)
        success_probability = max(0.1, 1.0 - min(risk_score, 0.9))

        # 위험 수준 결정
        if success_probability >= 0.8:
            risk_level = RiskLevel.VERY_LOW
        elif success_probability >= 0.6:
            risk_level = RiskLevel.LOW
        elif success_probability >= 0.4:
            risk_level = RiskLevel.MEDIUM
        elif success_probability >= 0.2:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.VERY_HIGH

        # 추천사항 생성
        recommendations = self._generate_recommendations(active_factors, risk_level)

        return PredictionResult(
            prediction_type=PredictionType.AUTOMATION_SUCCESS,
            timestamp=datetime.now(),
            metric_name="automation_success_rate",
            current_value=self._calculate_current_success_rate(),
            predicted_value=success_probability * 100,
            confidence=0.85,  # 신뢰도
            risk_level=risk_level,
            time_horizon=timedelta(hours=2),
            factors=active_factors,
            recommendations=recommendations,
            metadata={
                "risk_score": risk_score,
                "complexity_score": complexity_score,
                "recent_failures": recent_failures,
            },
        )

    def predict_merge_conflict_risk(
        self, git_changes: int, file_types: List[str], change_complexity: Dict[str, int]
    ) -> PredictionResult:
        """머지 충돌 위험 예측"""

        risk_factors = []
        risk_score = 0.0

        # 변경사항 수량 위험
        if git_changes > 150:
            risk_score += 0.4
            risk_factors.append(f"변경사항 과다 ({git_changes}개)")
        elif git_changes > 100:
            risk_score += 0.2
            risk_factors.append(f"변경사항 많음 ({git_changes}개)")

        # 파일 유형별 위험도
        high_risk_files = ["models.py", "__init__.py", "main.py", "settings.py"]
        risky_files = [
            f for f in file_types if any(risk in f for risk in high_risk_files)
        ]

        if risky_files:
            risk_score += 0.3
            risk_factors.append(f"고위험 파일 포함: {risky_files[:3]}")

        # 복잡도 기반 위험
        total_complexity = sum(change_complexity.values())
        if total_complexity > 1000:
            risk_score += 0.25
            risk_factors.append("높은 변경 복잡도")

        # 동시 작업자 수 (가상의 메트릭)
        concurrent_developers = change_complexity.get("concurrent_developers", 1)
        if concurrent_developers > 3:
            risk_score += 0.2
            risk_factors.append(f"동시 작업자 다수 ({concurrent_developers}명)")

        conflict_probability = min(risk_score, 0.9)

        # 위험 수준 결정
        if conflict_probability >= 0.7:
            risk_level = RiskLevel.VERY_HIGH
        elif conflict_probability >= 0.5:
            risk_level = RiskLevel.HIGH
        elif conflict_probability >= 0.3:
            risk_level = RiskLevel.MEDIUM
        elif conflict_probability >= 0.1:
            risk_level = RiskLevel.LOW
        else:
            risk_level = RiskLevel.VERY_LOW

        recommendations = (
            [
                "변경사항을 작은 단위로 분할하여 커밋",
                "자주 메인 브랜치와 동기화",
                "고위험 파일은 단독 작업 권장",
                "코드 리뷰 강화",
            ]
            if risk_level != RiskLevel.VERY_LOW
            else ["현재 상태 유지"]
        )

        return PredictionResult(
            prediction_type=PredictionType.MERGE_CONFLICT_RISK,
            timestamp=datetime.now(),
            metric_name="merge_conflict_probability",
            current_value=0.0,  # 현재 충돌 없음
            predicted_value=conflict_probability * 100,
            confidence=0.75,
            risk_level=risk_level,
            time_horizon=timedelta(hours=6),
            factors=risk_factors,
            recommendations=recommendations,
        )

    def _count_recent_failures(self) -> int:
        """최근 실패 횟수 계산"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        return len(
            [
                h
                for h in self.success_history
                if h.get("success", True) == False
                and h.get("timestamp", datetime.min) > cutoff_time
            ]
        )

    def _is_risky_time(self) -> bool:
        """위험 시간대 확인 (주말, 야간)"""
        now = datetime.now()

        # 주말 확인
        if now.weekday() >= 5:  # 토요일(5), 일요일(6)
            return True

        # 야간 시간 확인 (22시~6시)
        if now.hour >= 22 or now.hour <= 6:
            return True

        return False

    def _evaluate_complexity(self, context: Dict[str, Any]) -> float:
        """변경사항 복잡도 평가"""
        complexity_score = 0.0

        # 영향받는 파일 수
        files_count = context.get("affected_files", 0)
        complexity_score += min(files_count / 50, 0.3)

        # 코드 라인 수
        lines_changed = context.get("lines_changed", 0)
        complexity_score += min(lines_changed / 1000, 0.3)

        # 새 의존성 추가
        new_dependencies = context.get("new_dependencies", 0)
        complexity_score += new_dependencies * 0.1

        # 데이터베이스 변경
        if context.get("database_changes", False):
            complexity_score += 0.2

        # API 변경
        if context.get("api_changes", False):
            complexity_score += 0.15

        return min(complexity_score, 1.0)

    def _calculate_current_success_rate(self) -> float:
        """현재 성공률 계산"""
        if not self.success_history:
            return 80.0  # 기본값

        successful = len([h for h in self.success_history if h.get("success", True)])
        return (successful / len(self.success_history)) * 100

    def _generate_recommendations(
        self, risk_factors: List[str], risk_level: RiskLevel
    ) -> List[str]:
        """위험 요소 기반 추천사항 생성"""
        recommendations = []

        if risk_level == RiskLevel.VERY_HIGH:
            recommendations.extend(
                [
                    "🚨 자동화 실행 중단 권장",
                    "위험 요소 해결 후 재시도",
                    "수동 검증 단계 추가",
                ]
            )

        if "Git 변경사항" in str(risk_factors):
            recommendations.append("변경사항을 그룹별로 분할하여 단계적 처리")

        if "테스트 커버리지" in str(risk_factors):
            recommendations.append("핵심 기능에 대한 테스트 케이스 우선 추가")

        if "파일 크기" in str(risk_factors):
            recommendations.append("큰 파일을 모듈별로 분할")

        if "성능" in str(risk_factors):
            recommendations.append("성능 최적화 후 자동화 재실행")

        if "메모리" in str(risk_factors):
            recommendations.append("메모리 사용률 정리 후 진행")

        if not recommendations:
            recommendations = ["현재 상태로 안전한 진행 가능"]

        return recommendations

    def record_automation_result(self, success: bool, context: Dict[str, Any]):
        """자동화 결과 기록"""
        self.success_history.append(
            {"timestamp": datetime.now(), "success": success, "context": context}
        )


class PredictiveEngine:
    """예측적 문제 감지 엔진 메인 클래스"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.time_series_analyzer = TimeSeriesAnalyzer()
        self.anomaly_detector = AnomalyDetector()
        self.risk_predictor = AutomationRiskPredictor()
        self.alert_system = get_korean_alert_system()

        # 메트릭 히스토리 저장
        self.metrics_history = defaultdict(list)
        self.prediction_cache = {}
        self.last_prediction_time = {}

    def analyze_system_health(
        self, current_metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        """시스템 전반적 건강도 분석"""
        analysis_results = {
            "timestamp": datetime.now(),
            "overall_health": "unknown",
            "predictions": [],
            "anomalies": [],
            "recommendations": [],
            "risk_assessment": {},
        }

        try:
            # 각 메트릭별 분석
            for metric_name, value in current_metrics.items():
                # 히스토리 업데이트
                self.metrics_history[metric_name].append(
                    {"timestamp": datetime.now(), "value": value}
                )

                # 최근 100개만 유지
                if len(self.metrics_history[metric_name]) > 100:
                    self.metrics_history[metric_name] = self.metrics_history[
                        metric_name
                    ][-100:]

                # 베이스라인 업데이트
                self.anomaly_detector.update_baseline(metric_name, value)

                # 이상 징후 감지
                anomaly = self.anomaly_detector.detect_anomaly(metric_name, value)
                if anomaly.is_anomaly:
                    analysis_results["anomalies"].append(asdict(anomaly))

                    # 이상 징후 알림
                    if self.alert_system:
                        self.alert_system.send_system_status_alert(
                            metric_name,
                            value,
                            anomaly.threshold,
                            trend=self._get_metric_trend(metric_name),
                        )

            # 트렌드 예측
            trend_predictions = self._generate_trend_predictions()
            analysis_results["predictions"].extend(trend_predictions)

            # 자동화 위험 예측
            automation_prediction = self.risk_predictor.predict_automation_success(
                current_metrics, {"timestamp": datetime.now()}
            )
            analysis_results["predictions"].append(asdict(automation_prediction))

            # 전체 건강도 평가
            overall_health = self._calculate_overall_health(
                current_metrics, analysis_results["anomalies"]
            )
            analysis_results["overall_health"] = overall_health

            # 종합 추천사항
            analysis_results["recommendations"] = self._generate_system_recommendations(
                analysis_results["anomalies"], automation_prediction
            )

            self.logger.info(f"시스템 건강도 분석 완료: {overall_health}")

        except Exception as e:
            self.logger.error(f"시스템 건강도 분석 실패: {e}")
            analysis_results["overall_health"] = "error"

        return analysis_results

    def _generate_trend_predictions(self) -> List[Dict[str, Any]]:
        """트렌드 기반 예측 생성"""
        predictions = []

        for metric_name, history in self.metrics_history.items():
            if len(history) < 5:
                continue

            values = [h["value"] for h in history[-20:]]  # 최근 20개

            # 트렌드 분석
            trend, slope = self.time_series_analyzer.detect_trend(values)

            if trend != "stable":
                # 미래 값 예측
                future_values = self.time_series_analyzer.predict_next_values(values, 5)

                prediction = PredictionResult(
                    prediction_type=PredictionType.TREND_ANALYSIS,
                    timestamp=datetime.now(),
                    metric_name=metric_name,
                    current_value=values[-1],
                    predicted_value=future_values[2],  # 3단계 후 예측값
                    confidence=self._calculate_trend_confidence(values),
                    risk_level=self._assess_trend_risk(metric_name, trend, slope),
                    time_horizon=timedelta(minutes=90),  # 3단계 * 30분
                    factors=[f"트렌드: {trend}", f"기울기: {slope:.3f}"],
                    recommendations=self._get_trend_recommendations(metric_name, trend),
                )

                predictions.append(asdict(prediction))

        return predictions

    def _calculate_trend_confidence(self, values: List[float]) -> float:
        """트렌드 신뢰도 계산"""
        if len(values) < 5:
            return 0.5

        # R-squared 유사 계산 (단순화된 버전)
        trend, slope = self.time_series_analyzer.detect_trend(values)

        # 예측값과 실제값의 차이 계산
        n = len(values)
        x = list(range(n))
        y_mean = statistics.mean(values)

        predicted = [slope * i + values[0] for i in x]
        ss_res = sum((values[i] - predicted[i]) ** 2 for i in range(n))
        ss_tot = sum((values[i] - y_mean) ** 2 for i in range(n))

        if ss_tot == 0:
            return 0.5

        r_squared = 1 - (ss_res / ss_tot)
        return max(0.1, min(0.95, r_squared))

    def _assess_trend_risk(
        self, metric_name: str, trend: str, slope: float
    ) -> RiskLevel:
        """트렌드 위험도 평가"""
        # 메트릭별 위험 방향 정의
        bad_trends = {
            "git_changes": "increasing",
            "api_response_time": "increasing",
            "memory_usage": "increasing",
            "cpu_usage": "increasing",
            "file_violations": "increasing",
            "test_coverage": "decreasing",  # 테스트 커버리지는 감소가 나쁨
        }

        bad_trend = bad_trends.get(metric_name, "increasing")

        if trend == bad_trend:
            if abs(slope) > 2.0:
                return RiskLevel.VERY_HIGH
            elif abs(slope) > 1.0:
                return RiskLevel.HIGH
            elif abs(slope) > 0.5:
                return RiskLevel.MEDIUM
            else:
                return RiskLevel.LOW
        else:
            return RiskLevel.VERY_LOW

    def _get_trend_recommendations(self, metric_name: str, trend: str) -> List[str]:
        """트렌드별 추천사항"""
        recommendations_map = {
            ("git_changes", "increasing"): [
                "변경사항을 작은 단위로 분할하여 커밋",
                "우선순위가 높은 변경사항부터 처리",
            ],
            ("test_coverage", "decreasing"): [
                "새로운 테스트 케이스 추가",
                "기존 테스트 케이스 검토 및 보완",
            ],
            ("api_response_time", "increasing"): [
                "API 성능 최적화 필요",
                "데이터베이스 쿼리 최적화",
                "캐싱 전략 검토",
            ],
            ("memory_usage", "increasing"): [
                "메모리 누수 확인",
                "불필요한 객체 정리",
                "가비지 컬렉션 최적화",
            ],
        }

        return recommendations_map.get((metric_name, trend), ["추세 모니터링 계속"])

    def _calculate_overall_health(
        self, metrics: Dict[str, float], anomalies: List[Dict[str, Any]]
    ) -> str:
        """전체 시스템 건강도 계산"""

        # 이상 징후 점수 계산
        anomaly_score = 0
        for anomaly in anomalies:
            if anomaly.get("severity") == "critical":
                anomaly_score += 30
            elif anomaly.get("severity") == "high":
                anomaly_score += 20
            elif anomaly.get("severity") == "medium":
                anomaly_score += 10

        # 메트릭별 건강도 점수
        health_score = 100

        # Git 변경사항 (많을수록 위험)
        git_changes = metrics.get("git_changes", 0)
        if git_changes > 130:
            health_score -= 25
        elif git_changes > 100:
            health_score -= 15

        # 테스트 커버리지 (낮을수록 위험)
        test_coverage = metrics.get("test_coverage", 100)
        if test_coverage < 20:
            health_score -= 30
        elif test_coverage < 50:
            health_score -= 15

        # API 성능
        api_time = metrics.get("api_response_time", 0)
        if api_time > 200:
            health_score -= 20
        elif api_time > 100:
            health_score -= 10

        # 시스템 리소스
        memory_usage = metrics.get("memory_usage", 0)
        cpu_usage = metrics.get("cpu_usage", 0)
        if max(memory_usage, cpu_usage) > 85:
            health_score -= 15
        elif max(memory_usage, cpu_usage) > 70:
            health_score -= 8

        # 이상 징후 점수 반영
        health_score -= anomaly_score

        # 건강도 분류
        health_score = max(0, health_score)

        if health_score >= 90:
            return "excellent"
        elif health_score >= 75:
            return "good"
        elif health_score >= 60:
            return "fair"
        elif health_score >= 40:
            return "poor"
        else:
            return "critical"

    def _generate_system_recommendations(
        self, anomalies: List[Dict[str, Any]], automation_prediction: PredictionResult
    ) -> List[str]:
        """시스템 전체 추천사항 생성"""
        recommendations = []

        # 이상 징후 기반 추천
        critical_anomalies = [a for a in anomalies if a.get("severity") == "critical"]
        if critical_anomalies:
            recommendations.append("🚨 긴급: 심각한 시스템 이상 징후 해결 필요")

        high_anomalies = [a for a in anomalies if a.get("severity") == "high"]
        if high_anomalies:
            recommendations.append("⚠️ 주의: 시스템 성능 저하 요인 점검")

        # 자동화 위험 기반 추천
        if automation_prediction.risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]:
            recommendations.append("🤖 자동화 위험도 높음 - 단계적 접근 권장")

        # 일반 권장사항
        if not recommendations:
            recommendations.extend(
                ["✅ 시스템 상태 양호 - 현재 수준 유지", "📊 지속적인 모니터링 권장"]
            )

        return recommendations

    def _get_metric_trend(self, metric_name: str) -> Optional[str]:
        """메트릭 트렌드 조회"""
        history = self.metrics_history.get(metric_name, [])
        if len(history) < 5:
            return None

        values = [h["value"] for h in history[-10:]]
        trend, _ = self.time_series_analyzer.detect_trend(values)
        return trend

    def get_prediction_summary(self) -> Dict[str, Any]:
        """예측 요약 정보"""
        return {
            "metrics_tracked": len(self.metrics_history),
            "total_history_points": sum(len(h) for h in self.metrics_history.values()),
            "recent_anomalies": len(
                [a for a in self.anomaly_detector.baseline_windows.values()]
            ),
            "automation_success_rate": self.risk_predictor._calculate_current_success_rate(),
            "system_uptime": datetime.now().isoformat(),
            "prediction_capabilities": [pt.value for pt in PredictionType],
            "risk_levels": [rl.value for rl in RiskLevel],
        }


# 싱글톤 인스턴스
_predictive_engine = None


def get_predictive_engine() -> PredictiveEngine:
    """예측 엔진 싱글톤 인스턴스 반환"""
    global _predictive_engine
    if _predictive_engine is None:
        _predictive_engine = PredictiveEngine()
    return _predictive_engine


if __name__ == "__main__":
    # 테스트 실행
    engine = get_predictive_engine()

    # 샘플 메트릭으로 테스트
    test_metrics = {
        "git_changes": 133,
        "test_coverage": 19.0,
        "api_response_time": 65.0,
        "memory_usage": 45.0,
        "cpu_usage": 25.0,
        "file_violations": 2,
    }

    # 시스템 건강도 분석
    analysis = engine.analyze_system_health(test_metrics)

    print("🔮 예측적 문제 감지 엔진 테스트 결과:")
    print(f"전체 건강도: {analysis['overall_health']}")
    print(f"이상 징후: {len(analysis['anomalies'])}개")
    print(f"예측 결과: {len(analysis['predictions'])}개")
    print(f"추천사항: {len(analysis['recommendations'])}개")

    # 상세 정보 출력
    for recommendation in analysis["recommendations"]:
        print(f"💡 {recommendation}")

    # 예측 요약
    summary = engine.get_prediction_summary()
    print(f"\n📊 예측 시스템 요약:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
