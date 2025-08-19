"""
시스템 건강 상태 모니터링 데이터 구조체
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class SystemHealth:
    """시스템 건강 상태"""

    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    database_status: str = "unknown"
    cache_status: str = "unknown"
    uptime_seconds: int = 0
    active_connections: int = 0
    error_count_last_hour: int = 0
    warnings: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def overall_status(self) -> str:
        """전체적인 시스템 상태"""
        if self.error_count_last_hour > 50:
            return "critical"
        elif self.cpu_percent > 90 or self.memory_percent > 90:
            return "warning"
        elif self.database_status != "healthy":
            return "warning"
        else:
            return "healthy"

    def add_warning(self, message: str) -> None:
        """경고 메시지 추가"""
        self.warnings.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        logger.warning(f"System health warning: {message}")

    def clear_warnings(self) -> None:
        """경고 메시지 초기화"""
        self.warnings.clear()

    def to_dict(self) -> dict:
        """사전 형태로 변환"""
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "disk_percent": self.disk_percent,
            "database_status": self.database_status,
            "cache_status": self.cache_status,
            "uptime_seconds": self.uptime_seconds,
            "active_connections": self.active_connections,
            "error_count_last_hour": self.error_count_last_hour,
            "warnings": self.warnings,
            "timestamp": self.timestamp.isoformat(),
            "overall_status": self.overall_status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SystemHealth":
        """사전에서 시스템 헬스 인스턴스 생성"""
        # timestamp 처리
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        
        # warnings 처리
        if "warnings" not in data:
            data["warnings"] = []
            
        return cls(**data)

    def is_critical(self) -> bool:
        """심각한 상태인지 확인"""
        return self.overall_status == "critical"

    def needs_attention(self) -> bool:
        """주의가 필요한 상태인지 확인"""
        return self.overall_status in ["warning", "critical"]

    def get_issues(self) -> List[str]:
        """현재 발생한 이슈 목록 반환"""
        issues = []
        
        if self.cpu_percent > 90:
            issues.append(f"High CPU usage: {self.cpu_percent:.1f}%")
        if self.memory_percent > 90:
            issues.append(f"High memory usage: {self.memory_percent:.1f}%")
        if self.disk_percent > 90:
            issues.append(f"High disk usage: {self.disk_percent:.1f}%")
        if self.database_status != "healthy":
            issues.append(f"Database status: {self.database_status}")
        if self.cache_status not in ["healthy", "degraded"]:
            issues.append(f"Cache status: {self.cache_status}")
        if self.error_count_last_hour > 10:
            issues.append(f"High error count: {self.error_count_last_hour} errors/hour")
            
        return issues


if __name__ == "__main__":
    # Validation tests for system health
    import sys
    
    all_validation_failures = []
    total_tests = 0
    
    # Test 1: SystemHealth creation
    total_tests += 1
    try:
        health = SystemHealth()
        if health.overall_status != "healthy":
            all_validation_failures.append(f"Default health status should be healthy, got {health.overall_status}")
    except Exception as e:
        all_validation_failures.append(f"SystemHealth creation failed: {e}")
    
    # Test 2: Warning system
    total_tests += 1
    try:
        health = SystemHealth()
        health.add_warning("Test warning")
        if len(health.warnings) != 1:
            all_validation_failures.append(f"Warning not added correctly, expected 1, got {len(health.warnings)}")
    except Exception as e:
        all_validation_failures.append(f"Warning system test failed: {e}")
    
    # Test 3: Status calculation
    total_tests += 1
    try:
        health = SystemHealth(cpu_percent=95.0)
        if health.overall_status != "warning":
            all_validation_failures.append(f"High CPU should trigger warning status, got {health.overall_status}")
    except Exception as e:
        all_validation_failures.append(f"Status calculation test failed: {e}")
    
    # Test 4: Dictionary conversion
    total_tests += 1
    try:
        health = SystemHealth(cpu_percent=50.0, memory_percent=60.0)
        health_dict = health.to_dict()
        if "cpu_percent" not in health_dict or health_dict["cpu_percent"] != 50.0:
            all_validation_failures.append("Dictionary conversion failed")
    except Exception as e:
        all_validation_failures.append(f"Dictionary conversion test failed: {e}")
    
    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("System health dataclass is validated and ready for use")
        sys.exit(0)
