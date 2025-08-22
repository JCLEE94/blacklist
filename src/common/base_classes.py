# !/usr/bin/env python3
"""
공통 기본 클래스들
중복되는 __init__ 패턴과 공통 기능을 통합

Sample input: 다양한 서비스 클래스의 공통 초기화 패턴
Expected output: 재사용 가능한 기본 클래스와 mixin들
"""

import logging
import sqlite3
from datetime import datetime
from typing import Any, Dict, Optional

from .imports import logger


class DatabaseMixin:
    """데이터베이스 연결을 위한 Mixin 클래스"""

    def __init__(self, db_path: str = "instance/blacklist.db", **kwargs):
        self.db_path = db_path
        super().__init__(**kwargs)

    def _get_db_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결 생성 (재사용 가능)"""
        try:
            return sqlite3.connect(self.db_path, timeout=10)
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def _execute_query(self, query: str, params: tuple = ()) -> list:
        """쿼리 실행 (재사용 가능)"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                result = cursor.fetchall()
                return result
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return []

    def _execute_write_query(self, query: str, params: tuple = ()) -> bool:
        """쓰기 쿼리 실행 (재사용 가능)"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Write query execution failed: {e}")
            return False


class ConfigurableMixin:
    """설정 가능한 매개변수를 위한 Mixin 클래스"""

    def __init__(self, **kwargs):
        # 기본 설정값들
        self._default_config = {"timeout": 30, "max_retries": 3, "debug": False}

        # 전달받은 설정으로 기본값 덮어쓰기
        self._config = {**self._default_config, **kwargs}

        # 설정값들을 인스턴스 속성으로 설정
        for key, value in self._config.items():
            setattr(self, key, value)

        super().__init__()


class TimestampMixin:
    """타임스탬프 관리를 위한 Mixin 클래스"""

    def __init__(self, **kwargs):
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        super().__init__(**kwargs)

    def touch(self):
        """업데이트 시간을 현재 시간으로 갱신"""
        self.updated_at = datetime.now()


class ValidationMixin:
    """검증 기능을 위한 Mixin 클래스"""

    def __init__(self, **kwargs):
        self._validation_rules = {}
        super().__init__(**kwargs)

    def add_validation_rule(self, field: str, rule: callable):
        """검증 규칙 추가"""
        self._validation_rules[field] = rule

    def validate(self, data: Dict[str, Any]) -> Dict[str, str]:
        """데이터 검증 수행"""
        errors = {}
        for field, rule in self._validation_rules.items():
            if field in data:
                try:
                    if not rule(data[field]):
                        errors[field] = f"Validation failed for {field}"
                except Exception as e:
                    errors[field] = f"Validation error for {field}: {e}"
        return errors


class LoggingMixin:
    """로깅 기능을 위한 Mixin 클래스"""

    def __init__(self, logger_name: Optional[str] = None, **kwargs):
        if logger_name:
            self.logger = logging.getLogger(logger_name)
        else:
            self.logger = logging.getLogger(self.__class__.__name__)
        super().__init__(**kwargs)

    def log_info(self, message: str):
        """정보 로그"""
        self.logger.info(f"[{self.__class__.__name__}] {message}")

    def log_error(self, message: str, exception: Optional[Exception] = None):
        """에러 로그"""
        if exception:
            self.logger.error(f"[{self.__class__.__name__}] {message}: {exception}")
        else:
            self.logger.error(f"[{self.__class__.__name__}] {message}")

    def log_debug(self, message: str):
        """디버그 로그"""
        self.logger.debug(f"[{self.__class__.__name__}] {message}")


class BaseService(DatabaseMixin, ConfigurableMixin, TimestampMixin, LoggingMixin):
    """서비스 클래스를 위한 기본 클래스"""

    def __init__(self, service_name: str, **kwargs):
        self.service_name = service_name
        self.is_initialized = False

        # 모든 mixin들 초기화
        super().__init__(**kwargs)

        self.log_info(f"Service '{service_name}' initialized")
        self.is_initialized = True

    def health_check(self) -> Dict[str, Any]:
        """서비스 상태 체크"""
        return {
            "service_name": self.service_name,
            "is_initialized": self.is_initialized,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class BaseAnalyzer(DatabaseMixin, LoggingMixin):
    """분석기 클래스를 위한 기본 클래스"""

    def __init__(self, analyzer_name: str, **kwargs):
        self.analyzer_name = analyzer_name
        super().__init__(**kwargs)
        self.log_info(f"Analyzer '{analyzer_name}' initialized")

    def _safe_execute(self, func_name: str, func) -> Dict[str, Any]:
        """안전한 함수 실행 (예외 처리)"""
        try:
            result = func()
            return {"success": True, "data": result}
        except Exception as e:
            self.log_error(f"Error in {func_name}", e)
            return {"success": False, "error": str(e)}


class BaseCollector(DatabaseMixin, ConfigurableMixin, LoggingMixin):
    """수집기 클래스를 위한 기본 클래스"""

    def __init__(self, collector_name: str, source_name: str, **kwargs):
        self.collector_name = collector_name
        self.source_name = source_name
        self.collection_stats = {
            "total_attempts": 0,
            "successful_collections": 0,
            "failed_collections": 0,
            "last_collection": None,
        }
        super().__init__(**kwargs)
        self.log_info(
            f"Collector '{collector_name}' for source '{source_name}' initialized"
        )

    def update_stats(self, success: bool):
        """수집 통계 업데이트"""
        self.collection_stats["total_attempts"] += 1
        if success:
            self.collection_stats["successful_collections"] += 1
        else:
            self.collection_stats["failed_collections"] += 1
        self.collection_stats["last_collection"] = datetime.now().isoformat()
        self.touch()

    def get_stats(self) -> Dict[str, Any]:
        """수집 통계 조회"""
        return {
            "collector_name": self.collector_name,
            "source_name": self.source_name,
            **self.collection_stats,
        }


if __name__ == "__main__":
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: DatabaseMixin functionality
    total_tests += 1
    try:

        class TestDbClass(DatabaseMixin):
            pass

        test_db = TestDbClass(db_path="test.db")
        if not hasattr(test_db, "_get_db_connection"):
            all_validation_failures.append(
                "DatabaseMixin test: Missing _get_db_connection method"
            )
    except Exception as e:
        all_validation_failures.append(
            f"DatabaseMixin test: Failed to create instance - {e}"
        )

    # Test 2: BaseService functionality
    total_tests += 1
    try:
        test_service = BaseService(service_name="test_service", db_path="test.db")
        health = test_service.health_check()
        if "service_name" not in health or health["service_name"] != "test_service":
            all_validation_failures.append("BaseService test: Health check failed")
    except Exception as e:
        all_validation_failures.append(
            f"BaseService test: Failed to create service - {e}"
        )

    # Test 3: Mixin composition
    total_tests += 1
    try:

        class TestComposite(TimestampMixin, ValidationMixin):
            def __init__(self):
                super().__init__()

        test_composite = TestComposite()
        if not hasattr(test_composite, "created_at") or not hasattr(
            test_composite, "validate"
        ):
            all_validation_failures.append(
                "Mixin composition test: Missing expected attributes"
            )
    except Exception as e:
        all_validation_failures.append(
            f"Mixin composition test: Failed to create composite - {e}"
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
        print("Base classes module is validated and ready for use")
        sys.exit(0)
