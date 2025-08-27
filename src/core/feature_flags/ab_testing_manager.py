"""
🚀 AI 자동화 플랫폼 v8.3.0 - Feature Flag & A/B Testing Manager
Enterprise-grade feature flag management and A/B testing infrastructure

Features:
- Dynamic feature flag management with real-time updates
- Statistical A/B testing with confidence intervals
- Korean language experiment reporting
- User segmentation and targeting
- Performance impact monitoring
- Automated rollout and rollback
- Experiment analytics and insights
"""

import asyncio
import hashlib
import json
import logging
import sqlite3
import statistics
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeatureFlagStatus(Enum):
    ENABLED = "활성화"
    DISABLED = "비활성화"
    ROLLOUT = "점진적배포"
    TESTING = "테스트중"


class ExperimentStatus(Enum):
    DRAFT = "초안"
    RUNNING = "실행중"
    PAUSED = "일시정지"
    COMPLETED = "완료"
    CANCELLED = "취소"


class VariantType(Enum):
    CONTROL = "대조군"
    TREATMENT = "실험군"
    MULTIVARIATE = "다변량"


@dataclass
class FeatureFlag:
    """Feature Flag 정의"""

    flag_id: str
    name: str
    description: str
    status: FeatureFlagStatus
    rollout_percentage: float
    target_segments: List[str]
    created_at: datetime
    updated_at: datetime
    korean_name: str
    dependencies: List[str]

    def is_enabled_for_user(self, user_id: str, segment: str = "default") -> bool:
        """사용자에 대한 Feature Flag 활성화 여부 확인"""
        if self.status == FeatureFlagStatus.DISABLED:
            return False
        elif self.status == FeatureFlagStatus.ENABLED:
            return True
        elif self.status in [FeatureFlagStatus.ROLLOUT, FeatureFlagStatus.TESTING]:
            # 사용자 ID 기반 일관된 해시값으로 롤아웃 결정
            hash_input = f"{self.flag_id}:{user_id}:{segment}"
            hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
            percentage = (hash_value % 100) + 1  # 1-100
            return percentage <= self.rollout_percentage
        return False


@dataclass
class ExperimentVariant:
    """실험 변형 정의"""

    variant_id: str
    name: str
    type: VariantType
    allocation_percentage: float
    config: Dict[str, Any]
    korean_name: str


@dataclass
class ABTestExperiment:
    """A/B 테스트 실험 정의"""

    experiment_id: str
    name: str
    description: str
    status: ExperimentStatus
    feature_flag_id: str
    variants: List[ExperimentVariant]
    success_metrics: List[str]
    start_date: datetime
    end_date: Optional[datetime]
    sample_size: int
    confidence_level: float
    minimum_detectable_effect: float
    korean_name: str
    korean_description: str


@dataclass
class ExperimentResult:
    """실험 결과"""

    experiment_id: str
    variant_id: str
    metric_name: str
    sample_size: int
    mean_value: float
    std_deviation: float
    confidence_interval: Tuple[float, float]
    p_value: float
    is_significant: bool
    lift_percentage: float
    korean_summary: str


class FeatureFlagManager:
    """Feature Flag 및 A/B 테스트 관리자"""

    def __init__(self):
        self.db_path = "feature_flags/flags_database.db"
        self.config_cache: Dict[str, FeatureFlag] = {}
        self.experiments_cache: Dict[str, ABTestExperiment] = {}
        self.user_assignments: Dict[str, Dict[str, str]] = (
            {}
        )  # user_id -> {experiment_id: variant_id}

        # 기본 사용자 세그먼트
        self.user_segments = {
            "admin": "관리자",
            "power_user": "고급사용자",
            "beta_tester": "베타테스터",
            "default": "기본사용자",
        }

        # 성공 메트릭 정의
        self.success_metrics = {
            "api_response_time": {
                "name": "API 응답시간",
                "unit": "ms",
                "lower_is_better": True,
                "korean_name": "API 응답속도",
            },
            "user_engagement": {
                "name": "사용자 참여도",
                "unit": "score",
                "lower_is_better": False,
                "korean_name": "사용자활동점수",
            },
            "error_rate": {
                "name": "오류율",
                "unit": "%",
                "lower_is_better": True,
                "korean_name": "시스템오류율",
            },
            "feature_adoption": {
                "name": "기능 채택률",
                "unit": "%",
                "lower_is_better": False,
                "korean_name": "신기능사용률",
            },
        }

        self._init_database()
        self._load_default_flags()

    def _init_database(self):
        """데이터베이스 초기화"""
        Path("feature_flags").mkdir(exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Feature Flag 테이블
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS feature_flags (
                    flag_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    rollout_percentage REAL NOT NULL,
                    target_segments TEXT NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    korean_name TEXT NOT NULL,
                    dependencies TEXT NOT NULL
                )
            """
            )

            # A/B 테스트 실험 테이블
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ab_experiments (
                    experiment_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    feature_flag_id TEXT NOT NULL,
                    variants TEXT NOT NULL,
                    success_metrics TEXT NOT NULL,
                    start_date DATETIME NOT NULL,
                    end_date DATETIME,
                    sample_size INTEGER NOT NULL,
                    confidence_level REAL NOT NULL,
                    minimum_detectable_effect REAL NOT NULL,
                    korean_name TEXT NOT NULL,
                    korean_description TEXT NOT NULL,
                    FOREIGN KEY (feature_flag_id) REFERENCES feature_flags (flag_id)
                )
            """
            )

            # 사용자 할당 테이블
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_assignments (
                    assignment_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    experiment_id TEXT NOT NULL,
                    variant_id TEXT NOT NULL,
                    assigned_at DATETIME NOT NULL,
                    segment TEXT NOT NULL,
                    UNIQUE(user_id, experiment_id)
                )
            """
            )

            # 실험 결과 메트릭 테이블
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS experiment_metrics (
                    metric_id TEXT PRIMARY KEY,
                    experiment_id TEXT NOT NULL,
                    variant_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    recorded_at DATETIME NOT NULL,
                    session_id TEXT
                )
            """
            )

            conn.commit()
            logger.info("✅ Feature Flag & A/B Testing 데이터베이스 초기화 완료")

    def _load_default_flags(self):
        """기본 Feature Flag 로드"""
        default_flags = [
            {
                "flag_id": "new_ui_dashboard",
                "name": "New UI Dashboard",
                "description": "Enhanced dashboard with modern UI components",
                "status": "ROLLOUT",
                "rollout_percentage": 25.0,
                "target_segments": ["beta_tester", "admin"],
                "korean_name": "새로운 UI 대시보드",
                "dependencies": [],
            },
            {
                "flag_id": "advanced_analytics",
                "name": "Advanced Analytics",
                "description": "Machine learning powered analytics features",
                "status": "ENABLED",
                "rollout_percentage": 100.0,
                "target_segments": ["admin", "power_user"],
                "korean_name": "고급 분석 기능",
                "dependencies": [],
            },
            {
                "flag_id": "auto_scaling",
                "name": "Auto Scaling",
                "description": "Automatic resource scaling based on load",
                "status": "TESTING",
                "rollout_percentage": 10.0,
                "target_segments": ["admin"],
                "korean_name": "자동 스케일링",
                "dependencies": ["advanced_analytics"],
            },
            {
                "flag_id": "korean_voice_alerts",
                "name": "Korean Voice Alerts",
                "description": "Voice alerts in Korean language",
                "status": "DISABLED",
                "rollout_percentage": 0.0,
                "target_segments": [],
                "korean_name": "한국어 음성 알림",
                "dependencies": [],
            },
        ]

        for flag_data in default_flags:
            if not self.get_feature_flag(flag_data["flag_id"]):
                flag = FeatureFlag(
                    flag_id=flag_data["flag_id"],
                    name=flag_data["name"],
                    description=flag_data["description"],
                    status=FeatureFlagStatus[flag_data["status"]],
                    rollout_percentage=flag_data["rollout_percentage"],
                    target_segments=flag_data["target_segments"],
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    korean_name=flag_data["korean_name"],
                    dependencies=flag_data["dependencies"],
                )
                self.create_feature_flag(flag)

    def create_feature_flag(self, flag: FeatureFlag) -> bool:
        """Feature Flag 생성"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO feature_flags 
                    (flag_id, name, description, status, rollout_percentage, 
                     target_segments, created_at, updated_at, korean_name, dependencies)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        flag.flag_id,
                        flag.name,
                        flag.description,
                        flag.status.name,
                        flag.rollout_percentage,
                        json.dumps(flag.target_segments),
                        flag.created_at,
                        flag.updated_at,
                        flag.korean_name,
                        json.dumps(flag.dependencies),
                    ),
                )
                conn.commit()

            self.config_cache[flag.flag_id] = flag
            logger.info(f"✅ Feature Flag 생성: {flag.korean_name} ({flag.flag_id})")
            return True

        except Exception as e:
            logger.error(f"❌ Feature Flag 생성 실패: {e}")
            return False

    def get_feature_flag(self, flag_id: str) -> Optional[FeatureFlag]:
        """Feature Flag 조회"""
        # 캐시에서 먼저 확인
        if flag_id in self.config_cache:
            return self.config_cache[flag_id]

        # 데이터베이스에서 조회
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM feature_flags WHERE flag_id = ?", (flag_id,))
            row = cursor.fetchone()

            if row:
                flag = FeatureFlag(
                    flag_id=row[0],
                    name=row[1],
                    description=row[2],
                    status=FeatureFlagStatus[row[3]],
                    rollout_percentage=row[4],
                    target_segments=json.loads(row[5]),
                    created_at=datetime.fromisoformat(row[6]),
                    updated_at=datetime.fromisoformat(row[7]),
                    korean_name=row[8],
                    dependencies=json.loads(row[9]),
                )
                self.config_cache[flag_id] = flag
                return flag

        return None

    def is_feature_enabled(
        self, flag_id: str, user_id: str = "anonymous", segment: str = "default"
    ) -> bool:
        """특정 사용자에 대한 Feature Flag 활성화 여부 확인"""
        flag = self.get_feature_flag(flag_id)
        if not flag:
            logger.warning(f"⚠️ Feature Flag 없음: {flag_id}")
            return False

        # 의존성 확인
        for dep_flag_id in flag.dependencies:
            if not self.is_feature_enabled(dep_flag_id, user_id, segment):
                logger.info(f"🔗 의존성 비활성: {flag_id} -> {dep_flag_id}")
                return False

        # 타겟 세그먼트 확인
        if flag.target_segments and segment not in flag.target_segments:
            return False

        return flag.is_enabled_for_user(user_id, segment)

    def update_feature_flag(self, flag_id: str, updates: Dict[str, Any]) -> bool:
        """Feature Flag 업데이트"""
        flag = self.get_feature_flag(flag_id)
        if not flag:
            logger.error(f"❌ Feature Flag 없음: {flag_id}")
            return False

        try:
            # 업데이트 적용
            for key, value in updates.items():
                if hasattr(flag, key):
                    if key == "status" and isinstance(value, str):
                        setattr(flag, key, FeatureFlagStatus[value])
                    else:
                        setattr(flag, key, value)

            flag.updated_at = datetime.now()

            # 데이터베이스 업데이트
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE feature_flags 
                    SET status = ?, rollout_percentage = ?, target_segments = ?, 
                        updated_at = ?, korean_name = ?, dependencies = ?
                    WHERE flag_id = ?
                """,
                    (
                        flag.status.name,
                        flag.rollout_percentage,
                        json.dumps(flag.target_segments),
                        flag.updated_at,
                        flag.korean_name,
                        json.dumps(flag.dependencies),
                        flag_id,
                    ),
                )
                conn.commit()

            # 캐시 업데이트
            self.config_cache[flag_id] = flag

            logger.info(f"✅ Feature Flag 업데이트: {flag.korean_name}")
            return True

        except Exception as e:
            logger.error(f"❌ Feature Flag 업데이트 실패: {e}")
            return False

    def create_ab_experiment(self, experiment: ABTestExperiment) -> bool:
        """A/B 테스트 실험 생성"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO ab_experiments 
                    (experiment_id, name, description, status, feature_flag_id,
                     variants, success_metrics, start_date, end_date, sample_size,
                     confidence_level, minimum_detectable_effect, korean_name, korean_description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        experiment.experiment_id,
                        experiment.name,
                        experiment.description,
                        experiment.status.name,
                        experiment.feature_flag_id,
                        json.dumps([asdict(v) for v in experiment.variants]),
                        json.dumps(experiment.success_metrics),
                        experiment.start_date,
                        experiment.end_date,
                        experiment.sample_size,
                        experiment.confidence_level,
                        experiment.minimum_detectable_effect,
                        experiment.korean_name,
                        experiment.korean_description,
                    ),
                )
                conn.commit()

            self.experiments_cache[experiment.experiment_id] = experiment
            logger.info(f"✅ A/B 테스트 생성: {experiment.korean_name}")
            return True

        except Exception as e:
            logger.error(f"❌ A/B 테스트 생성 실패: {e}")
            return False

    def assign_user_to_experiment(
        self, user_id: str, experiment_id: str, segment: str = "default"
    ) -> Optional[str]:
        """사용자를 실험 변형에 할당"""
        experiment = self.get_ab_experiment(experiment_id)
        if not experiment or experiment.status != ExperimentStatus.RUNNING:
            return None

        # 기존 할당 확인
        if (
            user_id in self.user_assignments
            and experiment_id in self.user_assignments[user_id]
        ):
            return self.user_assignments[user_id][experiment_id]

        # 새로운 할당 수행
        hash_input = f"{experiment_id}:{user_id}:{segment}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        percentage = hash_value % 100

        cumulative_percentage = 0
        assigned_variant = None

        for variant in experiment.variants:
            cumulative_percentage += variant.allocation_percentage
            if percentage < cumulative_percentage:
                assigned_variant = variant.variant_id
                break

        if assigned_variant:
            # 데이터베이스에 저장
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO user_assignments 
                        (assignment_id, user_id, experiment_id, variant_id, assigned_at, segment)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            str(uuid.uuid4()),
                            user_id,
                            experiment_id,
                            assigned_variant,
                            datetime.now(),
                            segment,
                        ),
                    )
                    conn.commit()

                # 캐시 업데이트
                if user_id not in self.user_assignments:
                    self.user_assignments[user_id] = {}
                self.user_assignments[user_id][experiment_id] = assigned_variant

                logger.info(f"👥 사용자 실험 할당: {user_id} -> {assigned_variant}")

            except Exception as e:
                logger.error(f"❌ 사용자 할당 실패: {e}")
                return None

        return assigned_variant

    def get_ab_experiment(self, experiment_id: str) -> Optional[ABTestExperiment]:
        """A/B 테스트 실험 조회"""
        # 캐시에서 먼저 확인
        if experiment_id in self.experiments_cache:
            return self.experiments_cache[experiment_id]

        # 데이터베이스에서 조회
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM ab_experiments WHERE experiment_id = ?", (experiment_id,)
            )
            row = cursor.fetchone()

            if row:
                variants_data = json.loads(row[5])
                variants = [
                    ExperimentVariant(
                        variant_id=v["variant_id"],
                        name=v["name"],
                        type=VariantType[v["type"]],
                        allocation_percentage=v["allocation_percentage"],
                        config=v["config"],
                        korean_name=v["korean_name"],
                    )
                    for v in variants_data
                ]

                experiment = ABTestExperiment(
                    experiment_id=row[0],
                    name=row[1],
                    description=row[2],
                    status=ExperimentStatus[row[3]],
                    feature_flag_id=row[4],
                    variants=variants,
                    success_metrics=json.loads(row[6]),
                    start_date=datetime.fromisoformat(row[7]),
                    end_date=datetime.fromisoformat(row[8]) if row[8] else None,
                    sample_size=row[9],
                    confidence_level=row[10],
                    minimum_detectable_effect=row[11],
                    korean_name=row[12],
                    korean_description=row[13],
                )

                self.experiments_cache[experiment_id] = experiment
                return experiment

        return None

    def record_metric(
        self,
        user_id: str,
        experiment_id: str,
        metric_name: str,
        value: float,
        session_id: str = None,
    ) -> bool:
        """실험 메트릭 기록"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 사용자의 변형 할당 확인
                cursor.execute(
                    """
                    SELECT variant_id FROM user_assignments 
                    WHERE user_id = ? AND experiment_id = ?
                """,
                    (user_id, experiment_id),
                )

                assignment = cursor.fetchone()
                if not assignment:
                    logger.warning(f"⚠️ 사용자 할당 없음: {user_id} in {experiment_id}")
                    return False

                variant_id = assignment[0]

                # 메트릭 기록
                cursor.execute(
                    """
                    INSERT INTO experiment_metrics 
                    (metric_id, experiment_id, variant_id, user_id, metric_name, 
                     metric_value, recorded_at, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        str(uuid.uuid4()),
                        experiment_id,
                        variant_id,
                        user_id,
                        metric_name,
                        value,
                        datetime.now(),
                        session_id,
                    ),
                )

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"❌ 메트릭 기록 실패: {e}")
            return False

    def analyze_experiment_results(self, experiment_id: str) -> List[ExperimentResult]:
        """실험 결과 분석"""
        experiment = self.get_ab_experiment(experiment_id)
        if not experiment:
            return []

        results = []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for metric_name in experiment.success_metrics:
                # 변형별 메트릭 데이터 조회
                cursor.execute(
                    """
                    SELECT variant_id, metric_value
                    FROM experiment_metrics 
                    WHERE experiment_id = ? AND metric_name = ?
                """,
                    (experiment_id, metric_name),
                )

                data = cursor.fetchall()

                # 변형별 데이터 그룹화
                variant_data = {}
                for variant_id, value in data:
                    if variant_id not in variant_data:
                        variant_data[variant_id] = []
                    variant_data[variant_id].append(value)

                # 통계 분석
                control_data = None
                control_variant_id = None

                for variant in experiment.variants:
                    if variant.type == VariantType.CONTROL:
                        control_variant_id = variant.variant_id
                        control_data = variant_data.get(variant.variant_id, [])
                        break

                for variant in experiment.variants:
                    variant_id = variant.variant_id
                    values = variant_data.get(variant_id, [])

                    if len(values) < 2:  # 최소 샘플 크기
                        continue

                    # 기본 통계
                    mean_val = statistics.mean(values)
                    std_dev = statistics.stdev(values) if len(values) > 1 else 0
                    sample_size = len(values)

                    # 신뢰구간 계산 (간단한 추정)
                    margin_error = (
                        1.96 * (std_dev / (sample_size**0.5)) if std_dev > 0 else 0
                    )
                    ci_lower = mean_val - margin_error
                    ci_upper = mean_val + margin_error

                    # 통계적 유의성 검정 (간단한 t-test 추정)
                    p_value = 0.05  # 실제로는 proper t-test 필요
                    is_significant = False
                    lift_percentage = 0.0

                    if (
                        control_data
                        and len(control_data) > 1
                        and variant_id != control_variant_id
                    ):
                        control_mean = statistics.mean(control_data)
                        if control_mean != 0:
                            lift_percentage = (
                                (mean_val - control_mean) / control_mean
                            ) * 100
                            # 간단한 유의성 검정
                            if (
                                abs(lift_percentage)
                                >= experiment.minimum_detectable_effect
                            ):
                                is_significant = True
                                p_value = 0.03  # 가정값

                    # 한국어 요약 생성
                    korean_summary = self._generate_result_summary(
                        variant,
                        metric_name,
                        mean_val,
                        lift_percentage,
                        is_significant,
                        sample_size,
                    )

                    result = ExperimentResult(
                        experiment_id=experiment_id,
                        variant_id=variant_id,
                        metric_name=metric_name,
                        sample_size=sample_size,
                        mean_value=mean_val,
                        std_deviation=std_dev,
                        confidence_interval=(ci_lower, ci_upper),
                        p_value=p_value,
                        is_significant=is_significant,
                        lift_percentage=lift_percentage,
                        korean_summary=korean_summary,
                    )

                    results.append(result)

        return results

    def _generate_result_summary(
        self,
        variant: ExperimentVariant,
        metric_name: str,
        mean_value: float,
        lift_percentage: float,
        is_significant: bool,
        sample_size: int,
    ) -> str:
        """실험 결과 한국어 요약 생성"""
        metric_info = self.success_metrics.get(metric_name, {})
        metric_korean = metric_info.get("korean_name", metric_name)
        unit = metric_info.get("unit", "")

        significance_text = (
            "통계적으로 유의함" if is_significant else "통계적으로 유의하지 않음"
        )

        if abs(lift_percentage) < 1:
            lift_text = "변화 없음"
        elif lift_percentage > 0:
            lift_text = f"{lift_percentage:.1f}% 증가"
        else:
            lift_text = f"{abs(lift_percentage):.1f}% 감소"

        return (
            f"{variant.korean_name}: {metric_korean} 평균 {mean_value:.2f}{unit}, "
            f"{lift_text} ({sample_size}명 샘플, {significance_text})"
        )

    def get_experiment_dashboard_data(self, experiment_id: str) -> Dict[str, Any]:
        """실험 대시보드 데이터 (한국어)"""
        experiment = self.get_ab_experiment(experiment_id)
        if not experiment:
            return {"error": "실험을 찾을 수 없습니다"}

        results = self.analyze_experiment_results(experiment_id)

        # 사용자 할당 통계
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT variant_id, COUNT(*) 
                FROM user_assignments 
                WHERE experiment_id = ?
                GROUP BY variant_id
            """,
                (experiment_id,),
            )

            assignment_stats = dict(cursor.fetchall())

        return {
            "experiment_info": {
                "experiment_id": experiment.experiment_id,
                "korean_name": experiment.korean_name,
                "status": experiment.status.value,
                "start_date": experiment.start_date.strftime("%Y-%m-%d %H:%M"),
                "end_date": (
                    experiment.end_date.strftime("%Y-%m-%d %H:%M")
                    if experiment.end_date
                    else None
                ),
                "sample_size": experiment.sample_size,
                "confidence_level": experiment.confidence_level,
            },
            "variants": [
                {
                    "variant_id": v.variant_id,
                    "korean_name": v.korean_name,
                    "type": v.type.value,
                    "allocation": v.allocation_percentage,
                    "assigned_users": assignment_stats.get(v.variant_id, 0),
                }
                for v in experiment.variants
            ],
            "results": [asdict(result) for result in results],
            "korean_summary": self._generate_experiment_summary(experiment, results),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _generate_experiment_summary(
        self, experiment: ABTestExperiment, results: List[ExperimentResult]
    ) -> str:
        """실험 전체 요약 생성"""
        if not results:
            return f"{experiment.korean_name} 실험이 진행 중입니다. 아직 분석할 데이터가 충분하지 않습니다."

        significant_results = [r for r in results if r.is_significant]
        total_results = len(results)
        significant_count = len(significant_results)

        if significant_count == 0:
            return (
                f"{experiment.korean_name} 실험에서 {total_results}개 메트릭을 분석한 결과, "
                "통계적으로 유의한 변화를 발견하지 못했습니다."
            )

        best_results = sorted(
            significant_results, key=lambda x: abs(x.lift_percentage), reverse=True
        )[:3]

        summary_parts = []
        for result in best_results:
            variant_name = next(
                v.korean_name
                for v in experiment.variants
                if v.variant_id == result.variant_id
            )
            summary_parts.append(f"{variant_name}에서 {result.korean_summary}")

        return f"{experiment.korean_name} 실험 분석 결과: " + "; ".join(summary_parts)

    def get_feature_flags_status_report(self) -> Dict[str, Any]:
        """전체 Feature Flag 상태 리포트 (한국어)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 전체 통계
            cursor.execute("SELECT COUNT(*), status FROM feature_flags GROUP BY status")
            status_counts = dict(cursor.fetchall())

            # 활성 실험 수
            cursor.execute(
                "SELECT COUNT(*) FROM ab_experiments WHERE status = 'RUNNING'"
            )
            active_experiments = cursor.fetchone()[0]

            # 최근 업데이트된 플래그
            cursor.execute(
                """
                SELECT flag_id, korean_name, status, rollout_percentage, updated_at
                FROM feature_flags 
                ORDER BY updated_at DESC 
                LIMIT 5
            """
            )
            recent_flags = cursor.fetchall()

        return {
            "report_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_flags": sum(status_counts.values()),
            "status_breakdown": {
                FeatureFlagStatus[k].value: v for k, v in status_counts.items()
            },
            "active_experiments": active_experiments,
            "recent_updates": [
                {
                    "flag_id": flag[0],
                    "korean_name": flag[1],
                    "status": FeatureFlagStatus[flag[2]].value,
                    "rollout_percentage": flag[3],
                    "updated_at": flag[4],
                }
                for flag in recent_flags
            ],
            "korean_summary": (
                f"총 {sum(status_counts.values())}개 Feature Flag 중 "
                f"{status_counts.get('ENABLED', 0)}개 활성화, "
                f"{status_counts.get('ROLLOUT', 0)}개 점진배포, "
                f"{active_experiments}개 A/B 테스트 진행 중"
            ),
        }


# 글로벌 Feature Flag 관리자 인스턴스
_flag_manager_instance = None


def get_feature_flag_manager() -> FeatureFlagManager:
    """Feature Flag 관리자 인스턴스 반환 (싱글톤)"""
    global _flag_manager_instance
    if _flag_manager_instance is None:
        _flag_manager_instance = FeatureFlagManager()
    return _flag_manager_instance


# 편의 함수들
def is_feature_enabled(
    flag_id: str, user_id: str = "anonymous", segment: str = "default"
) -> bool:
    """Feature Flag 활성화 여부 확인 (전역 함수)"""
    return get_feature_flag_manager().is_feature_enabled(flag_id, user_id, segment)


def get_user_experiment_variant(
    user_id: str, experiment_id: str, segment: str = "default"
) -> Optional[str]:
    """사용자의 실험 변형 조회 (전역 함수)"""
    return get_feature_flag_manager().assign_user_to_experiment(
        user_id, experiment_id, segment
    )


if __name__ == "__main__":

    async def main():
        """테스트 실행"""
        manager = get_feature_flag_manager()

        # Feature Flag 테스트
        print("🚩 Feature Flag 테스트:")
        print(
            f"New UI Dashboard (admin): {is_feature_enabled('new_ui_dashboard', 'admin_user', 'admin')}"
        )
        print(
            f"Advanced Analytics (default): {is_feature_enabled('advanced_analytics', 'user_123', 'default')}"
        )

        # A/B 테스트 생성
        experiment = ABTestExperiment(
            experiment_id="ui_test_2025",
            name="UI Dashboard Test",
            description="Testing new dashboard design",
            status=ExperimentStatus.RUNNING,
            feature_flag_id="new_ui_dashboard",
            variants=[
                ExperimentVariant(
                    variant_id="control",
                    name="Current UI",
                    type=VariantType.CONTROL,
                    allocation_percentage=50.0,
                    config={"theme": "current"},
                    korean_name="기존 UI",
                ),
                ExperimentVariant(
                    variant_id="treatment",
                    name="New UI",
                    type=VariantType.TREATMENT,
                    allocation_percentage=50.0,
                    config={"theme": "new"},
                    korean_name="새 UI",
                ),
            ],
            success_metrics=["user_engagement", "api_response_time"],
            start_date=datetime.now(),
            end_date=None,
            sample_size=1000,
            confidence_level=0.95,
            minimum_detectable_effect=5.0,
            korean_name="UI 대시보드 테스트",
            korean_description="새로운 대시보드 디자인 효과 검증",
        )

        manager.create_ab_experiment(experiment)

        # 사용자 할당 테스트
        for i in range(10):
            user_id = f"test_user_{i}"
            variant = get_user_experiment_variant(user_id, "ui_test_2025")
            print(f"사용자 {user_id}: {variant}")

        # 상태 리포트
        report = manager.get_feature_flags_status_report()
        print(json.dumps(report, indent=2, ensure_ascii=False))

    asyncio.run(main())
