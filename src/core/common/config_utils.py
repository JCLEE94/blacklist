"""
통합 설정 관리 유틸리티
환경 변수 읽기 및 설정 검증 표준화
"""

import logging
import os
from typing import Any, Dict, List, Optional, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ConfigLoader:
    """환경 변수 및 설정 로더"""

    @staticmethod
    def get_env(
        key: str,
        default: Optional[T] = None,
        required: bool = False,
        var_type: Type[T] = str,
        choices: Optional[List[T]] = None,
    ) -> T:
        """
        환경 변수 읽기 (타입 변환 포함)

        Args:
            key: 환경 변수 키
            default: 기본값
            required: 필수 여부
            var_type: 변환할 타입
            choices: 허용된 값 목록

        Returns:
            환경 변수 값

        Raises:
            ValueError: 필수 변수가 없거나 타입 변환 실패
        """
        value = os.environ.get(key)

        # 값이 없는 경우
        if value is None:
            if required and default is None:
                raise ValueError(f"Required environment variable '{key}' is not set")
            return default

        # 타입 변환
        try:
            if var_type == bool:
                converted_value = value.lower() in ("true", "1", "yes", "on")
            elif var_type == int:
                converted_value = int(value)
            elif var_type == float:
                converted_value = float(value)
            elif var_type == list:
                # 쉼표로 구분된 리스트
                converted_value = [
                    item.strip() for item in value.split(",") if item.strip()
                ]
            else:
                converted_value = value

        except (ValueError, TypeError) as e:
            raise ValueError(f"Failed to convert '{key}' to {var_type.__name__}: {e}")

        # 선택지 검증
        if choices and converted_value not in choices:
            raise ValueError(
                f"'{key}' must be one of {choices}, got '{converted_value}'"
            )

        return converted_value

    @staticmethod
    def get_int(
        key: str,
        default: int = 0,
        min_val: Optional[int] = None,
        max_val: Optional[int] = None,
    ) -> int:
        """정수형 환경 변수 읽기 (범위 검증 포함)"""
        value = ConfigLoader.get_env(key, default, var_type=int)

        if min_val is not None and value < min_val:
            raise ValueError(f"'{key}' must be >= {min_val}, got {value}")
        if max_val is not None and value > max_val:
            raise ValueError(f"'{key}' must be <= {max_val}, got {value}")

        return value

    @staticmethod
    def get_bool(key: str, default: bool = False) -> bool:
        """불린형 환경 변수 읽기"""
        return ConfigLoader.get_env(key, default, var_type=bool)

    @staticmethod
    def get_list(
        key: str, default: Optional[List[str]] = None, separator: str = ","
    ) -> List[str]:
        """리스트형 환경 변수 읽기"""
        value = os.environ.get(key)
        if value is None:
            return default or []

        return [item.strip() for item in value.split(separator) if item.strip()]

    @staticmethod
    def get_dict(key_prefix: str) -> Dict[str, str]:
        """특정 프리픽스로 시작하는 모든 환경 변수를 딕셔너리로 반환"""
        result = {}
        for key, value in os.environ.items():
            if key.startswith(key_prefix):
                # 프리픽스 제거하고 소문자로 변환
                clean_key = key[len(key_prefix) :].lower()
                result[clean_key] = value
        return result


class ConfigValidator:
    """설정 검증 유틸리티"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def require(self, condition: bool, error_message: str) -> "ConfigValidator":
        """필수 조건 검증"""
        if not condition:
            self.errors.append(error_message)
        return self

    def recommend(self, condition: bool, warning_message: str) -> "ConfigValidator":
        """권장 조건 검증"""
        if not condition:
            self.warnings.append(warning_message)
        return self

    def check_env(
        self, key: str, required: bool = True, message: Optional[str] = None
    ) -> "ConfigValidator":
        """환경 변수 존재 확인"""
        exists = key in os.environ and os.environ[key]

        if required and not exists:
            error_msg = message or f"Environment variable '{key}' is required"
            self.errors.append(error_msg)
        elif not required and not exists:
            warning_msg = message or f"Environment variable '{key}' is recommended"
            self.warnings.append(warning_msg)

        return self

    def check_file(
        self, path: str, required: bool = True, message: Optional[str] = None
    ) -> "ConfigValidator":
        """파일 존재 확인"""
        exists = os.path.exists(path)

        if required and not exists:
            error_msg = message or f"Required file not found: {path}"
            self.errors.append(error_msg)
        elif not required and not exists:
            warning_msg = message or f"Recommended file not found: {path}"
            self.warnings.append(warning_msg)

        return self

    def check_directory(
        self, path: str, create: bool = True, message: Optional[str] = None
    ) -> "ConfigValidator":
        """디렉토리 확인 (선택적 생성)"""
        if not os.path.exists(path):
            if create:
                try:
                    os.makedirs(path, exist_ok=True)
                    logger.info(f"Created directory: {path}")
                except Exception as e:
                    error_msg = message or f"Failed to create directory {path}: {e}"
                    self.errors.append(error_msg)
            else:
                error_msg = message or f"Directory not found: {path}"
                self.errors.append(error_msg)

        return self

    def validate(self) -> bool:
        """검증 수행 및 결과 반환"""
        if self.warnings:
            for warning in self.warnings:
                logger.warning(f"Config warning: {warning}")

        if self.errors:
            for error in self.errors:
                logger.error(f"Config error: {error}")
            return False

        return True

    def get_report(self) -> Dict[str, Any]:
        """검증 결과 리포트"""
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }


class ConfigMixin:
    """설정 관련 공통 기능을 제공하는 믹스인 클래스"""

    @classmethod
    def load_from_env(cls) -> Dict[str, Any]:
        """환경 변수에서 설정 로드"""
        config = {}

        # 클래스 속성 중 대문자로 된 것들을 설정으로 간주
        for key in dir(cls):
            if key.isupper() and not key.startswith("_"):
                # 환경 변수에서 같은 이름 찾기
                env_value = os.environ.get(key)
                if env_value is not None:
                    # 기존 값의 타입에 맞춰 변환
                    default_value = getattr(cls, key)
                    if isinstance(default_value, bool):
                        config[key] = env_value.lower() in ("true", "1", "yes", "on")
                    elif isinstance(default_value, int):
                        config[key] = int(env_value)
                    elif isinstance(default_value, list):
                        config[key] = [item.strip() for item in env_value.split(",")]
                    else:
                        config[key] = env_value
                else:
                    config[key] = getattr(cls, key)

        return config

    @classmethod
    def get_safe_config(cls) -> Dict[str, Any]:
        """민감한 정보를 제외한 설정 반환"""
        config = cls.to_dict() if hasattr(cls, "to_dict") else cls.load_from_env()

        # 민감한 키 필터링
        sensitive_keys = ["PASSWORD", "SECRET", "KEY", "TOKEN", "CREDENTIAL"]
        safe_config = {}

        for key, value in config.items():
            is_sensitive = any(sensitive in key.upper() for sensitive in sensitive_keys)
            if is_sensitive:
                safe_config[key] = "***MASKED***"
            else:
                safe_config[key] = value

        return safe_config
