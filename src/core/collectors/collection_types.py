#!/usr/bin/env python3
"""
수집 시스템 데이터 타입 정의

수집 상태, 결과, 설정 등에 대한 데이터 클래스를 정의합니다.
상태 추적, 성능 지표, 메타데이터 지원을 제공합니다.

관련 패키지 문서:
- dataclasses: https://docs.python.org/3/library/dataclasses.html
- enum: https://docs.python.org/3/library/enum.html

입력 예시:
- source_name: "데이터 소스 이름"
- status: CollectionStatus.RUNNING
- collected_count: 100

출력 예시:
- CollectionResult 객체 (소요시간, 성공률 포함)
- 딕셔너리 형태의 직렬화된 데이터
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class CollectionStatus(Enum):
    """수집 상태 열거형"""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    RETRYING = "retrying"


class CollectionPriority(Enum):
    """수집 우선순위 열거형"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CollectionResult:
    """수집 결과 데이터 클래스"""

    source_name: str
    status: CollectionStatus
    collected_count: int = 0
    error_count: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    data: List[Any] = None  # For test compatibility
    errors: List[str] = None  # For test compatibility
    warnings: List[str] = None
    performance_metrics: Dict[str, float] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.data is None:
            self.data = []
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.performance_metrics is None:
            self.performance_metrics = {}

    @property
    def duration(self) -> Optional[float]:
        """수집 소요 시간 (초)"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def success_rate(self) -> float:
        """수집 성공률"""
        total = self.collected_count + self.error_count
        if total == 0:
            return 0.0
        return (self.collected_count / total) * 100

    @property
    def items_per_second(self) -> Optional[float]:
        """초당 수집 아이템 수"""
        if self.duration and self.duration > 0:
            return self.collected_count / self.duration
        return None

    def add_warning(self, message: str):
        """경고 메시지 추가"""
        self.warnings.append(message)

    def add_error(self, message: str):
        """에러 메시지 추가"""
        self.errors.append(message)
        self.error_count += 1

    def add_performance_metric(self, key: str, value: float):
        """성능 지표 추가"""
        self.performance_metrics[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        result = asdict(self)
        result["status"] = self.status.value
        result["duration"] = self.duration
        result["success_rate"] = self.success_rate
        result["items_per_second"] = self.items_per_second
        
        if self.start_time:
            result["start_time"] = self.start_time.isoformat()
        if self.end_time:
            result["end_time"] = self.end_time.isoformat()
            
        return result

    def is_successful(self) -> bool:
        """수집이 성공했는지 확인"""
        return self.status == CollectionStatus.COMPLETED and self.collected_count > 0

    def has_errors(self) -> bool:
        """에러가 있는지 확인"""
        return self.error_count > 0 or len(self.errors) > 0

    def has_warnings(self) -> bool:
        """경고가 있는지 확인"""
        return len(self.warnings) > 0


@dataclass
class CollectionConfig:
    """수집 설정 데이터 클래스"""

    enabled: bool = True
    interval: int = 3600  # 기본 1시간
    max_retries: int = 3
    timeout: int = 300  # 기본 5분
    parallel_workers: int = 1
    priority: CollectionPriority = CollectionPriority.NORMAL
    settings: Dict[str, Any] = None
    rate_limit: Optional[float] = None  # 초당 요청 수 제한
    retry_delay: int = 5  # 재시도 지연 시간 (초)
    circuit_breaker_threshold: int = 5  # 연속 실패 임계값

    def __post_init__(self):
        if self.settings is None:
            self.settings = {}

    def update_setting(self, key: str, value: Any):
        """설정 값 업데이트"""
        self.settings[key] = value

    def get_setting(self, key: str, default: Any = None) -> Any:
        """설정 값 조회"""
        return self.settings.get(key, default)

    def is_rate_limited(self) -> bool:
        """비율 제한이 설정되어 있는지 확인"""
        return self.rate_limit is not None and self.rate_limit > 0

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        result = asdict(self)
        result["priority"] = self.priority.value
        return result


@dataclass
class CollectionStats:
    """수집 통계 데이터 클래스"""

    total_collections: int = 0
    successful_collections: int = 0
    failed_collections: int = 0
    cancelled_collections: int = 0
    total_items_collected: int = 0
    total_errors: int = 0
    average_duration: float = 0.0
    average_success_rate: float = 0.0
    last_collection_time: Optional[datetime] = None
    uptime_seconds: float = 0.0

    def update_from_result(self, result: CollectionResult):
        """수집 결과로 통계 업데이트"""
        self.total_collections += 1
        
        if result.status == CollectionStatus.COMPLETED:
            self.successful_collections += 1
        elif result.status == CollectionStatus.FAILED:
            self.failed_collections += 1
        elif result.status == CollectionStatus.CANCELLED:
            self.cancelled_collections += 1
            
        self.total_items_collected += result.collected_count
        self.total_errors += result.error_count
        
        if result.end_time:
            self.last_collection_time = result.end_time
            
        # 평균 계산 업데이트
        self._update_averages(result)

    def _update_averages(self, result: CollectionResult):
        """평균값 업데이트"""
        if self.total_collections > 0:
            # 누적 평균 계산
            if result.duration:
                self.average_duration = (
                    (self.average_duration * (self.total_collections - 1) + result.duration)
                    / self.total_collections
                )
            
            self.average_success_rate = (
                (self.average_success_rate * (self.total_collections - 1) + result.success_rate)
                / self.total_collections
            )

    @property
    def success_rate(self) -> float:
        """전체 성공률"""
        if self.total_collections == 0:
            return 0.0
        return (self.successful_collections / self.total_collections) * 100

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        result = asdict(self)
        if self.last_collection_time:
            result["last_collection_time"] = self.last_collection_time.isoformat()
        result["success_rate"] = self.success_rate
        return result


if __name__ == "__main__":
    import sys
    from datetime import datetime, timedelta
    
    # 실제 데이터로 검증
    all_validation_failures = []
    total_tests = 0
    
    # 테스트 1: CollectionResult 기본 기능
    total_tests += 1
    try:
        result = CollectionResult(
            source_name="test_source",
            status=CollectionStatus.RUNNING,
            start_time=datetime.now()
        )
        
        result.collected_count = 100
        result.error_count = 5
        result.end_time = datetime.now() + timedelta(seconds=30)
        
        if result.duration is None or result.duration <= 0:
            all_validation_failures.append("CollectionResult duration 계산 오류")
        
        expected_rate = 100 / (100 + 5) * 100  # 95.238...
        if abs(result.success_rate - expected_rate) > 0.01:  # 부동소수점 허용 오차
            all_validation_failures.append(f"CollectionResult success_rate: 예상 {expected_rate:.2f}, 실제 {result.success_rate:.2f}")
            
    except Exception as e:
        all_validation_failures.append(f"CollectionResult 기본 기능 오류: {e}")
    
    # 테스트 2: CollectionConfig 설정 관리
    total_tests += 1
    try:
        config = CollectionConfig(
            enabled=True,
            interval=1800,
            priority=CollectionPriority.HIGH
        )
        
        config.update_setting("custom_key", "custom_value")
        retrieved_value = config.get_setting("custom_key")
        
        if retrieved_value != "custom_value":
            all_validation_failures.append(f"CollectionConfig 설정: 예상 'custom_value', 실제 '{retrieved_value}'")
            
    except Exception as e:
        all_validation_failures.append(f"CollectionConfig 설정 관리 오류: {e}")
    
    # 테스트 3: CollectionStats 통계 업데이트
    total_tests += 1
    try:
        stats = CollectionStats()
        
        # 성공 결과 추가
        success_result = CollectionResult(
            source_name="test",
            status=CollectionStatus.COMPLETED,
            collected_count=50,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=10)
        )
        
        stats.update_from_result(success_result)
        
        if stats.total_collections != 1:
            all_validation_failures.append(f"CollectionStats total_collections: 예상 1, 실제 {stats.total_collections}")
        
        if stats.successful_collections != 1:
            all_validation_failures.append(f"CollectionStats successful_collections: 예상 1, 실제 {stats.successful_collections}")
            
    except Exception as e:
        all_validation_failures.append(f"CollectionStats 통계 업데이트 오류: {e}")
    
    # 테스트 4: 상태 변환 및 직렬화
    total_tests += 1
    try:
        result_dict = result.to_dict()
        
        if "status" not in result_dict or result_dict["status"] != "running":
            all_validation_failures.append("상태 변환: status 필드 오류")
        
        if "duration" not in result_dict:
            all_validation_failures.append("상태 변환: duration 필드 누락")
            
    except Exception as e:
        all_validation_failures.append(f"상태 변환 오류: {e}")
    
    # 테스트 5: 에러 및 경고 관리
    total_tests += 1
    try:
        test_result = CollectionResult(
            source_name="error_test",
            status=CollectionStatus.FAILED
        )
        
        test_result.add_error("테스트 에러")
        test_result.add_warning("테스트 경고")
        
        if not test_result.has_errors():
            all_validation_failures.append("에러 관리: has_errors() 오류")
        
        if not test_result.has_warnings():
            all_validation_failures.append("경고 관리: has_warnings() 오류")
            
    except Exception as e:
        all_validation_failures.append(f"에러/경고 관리 오류: {e}")
    
    # 최종 검증 결과
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Collection types module is validated and ready for use")
        sys.exit(0)
