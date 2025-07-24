"""
예외 클래스 정의

시스템에서 사용하는 모든 커스텀 예외를 정의합니다.
일관된 에러 처리와 디버깅을 위해 구조화된 예외 계층을 제공합니다.
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BlacklistError(Exception):
    """
    Secudium 시스템의 기본 예외 클래스

    모든 커스텀 예외의 부모 클래스로, 공통적인 에러 처리 로직을 제공합니다.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.cause = cause

        # 로깅
        logger.error(
            f"{self.error_code}: {message}",
            extra={
                "error_code": self.error_code,
                "details": self.details,
                "cause": str(cause) if cause else None,
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        """예외를 딕셔너리로 변환"""
        result = {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }

        if self.cause:
            result["cause"] = str(self.cause)

        return result

    def to_api_response(self) -> Dict[str, Any]:
        """API 응답용 딕셔너리 변환"""
        return {
            "error": self.message,
            "error_code": self.error_code,
            "details": self.details,
        }


class ValidationError(BlacklistError):
    """
    데이터 검증 관련 예외

    IP 주소, 날짜 형식, 입력 데이터 등의 검증 실패 시 발생합니다.
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        validation_errors: Optional[List[str]] = None,
    ):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        if validation_errors:
            details["validation_errors"] = validation_errors

        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field
        self.value = value
        self.validation_errors = validation_errors or []


class CacheError(BlacklistError):
    """
    캐시 관련 예외

    Redis 연결 실패, 캐시 데이터 손상, TTL 설정 오류 등에 사용됩니다.
    """

    def __init__(
        self,
        message: str,
        cache_key: Optional[str] = None,
        operation: Optional[str] = None,
        cache_type: str = "unknown",
    ):
        details = {"cache_type": cache_type}
        if cache_key:
            details["cache_key"] = cache_key
        if operation:
            details["operation"] = operation

        super().__init__(message, "CACHE_ERROR", details)
        self.cache_key = cache_key
        self.operation = operation
        self.cache_type = cache_type


class DatabaseError(BlacklistError):
    """
    데이터베이스 관련 예외

    SQLite 연결 실패, 쿼리 오류, 스키마 문제 등에 사용됩니다.
    """

    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        table: Optional[str] = None,
        database_url: Optional[str] = None,
    ):
        details = {}
        if query:
            details["query"] = query
        if table:
            details["table"] = table
        if database_url:
            # 보안을 위해 URL에서 민감한 정보 제거
            details["database_url"] = self._sanitize_url(database_url)

        super().__init__(message, "DATABASE_ERROR", details)
        self.query = query
        self.table = table
        self.database_url = database_url

    @staticmethod
    def _sanitize_url(url: str) -> str:
        """데이터베이스 URL에서 민감한 정보 제거"""
        import re

        # 비밀번호 마스킹
        return re.sub(r"://([^:]+):([^@]+)@", r"://\1:****@", url)


class AuthenticationError(BlacklistError):
    """
    인증 관련 예외

    JWT 토큰 검증 실패, API 키 오류, 권한 부족 등에 사용됩니다.
    """

    def __init__(
        self,
        message: str,
        auth_type: Optional[str] = None,
        user_id: Optional[str] = None,
        required_permission: Optional[str] = None,
    ):
        details = {}
        if auth_type:
            details["auth_type"] = auth_type
        if user_id:
            details["user_id"] = user_id
        if required_permission:
            details["required_permission"] = required_permission

        super().__init__(message, "AUTHENTICATION_ERROR", details)
        self.auth_type = auth_type
        self.user_id = user_id
        self.required_permission = required_permission


class AuthorizationError(BlacklistError):
    """
    권한 부여 관련 예외

    역할 기반 접근 제어, 리소스 접근 권한 등의 오류에 사용됩니다.
    """

    def __init__(
        self,
        message: str,
        user_id: Optional[str] = None,
        required_role: Optional[str] = None,
        resource: Optional[str] = None,
    ):
        details = {}
        if user_id:
            details["user_id"] = user_id
        if required_role:
            details["required_role"] = required_role
        if resource:
            details["resource"] = resource

        super().__init__(message, "AUTHORIZATION_ERROR", details)
        self.user_id = user_id
        self.required_role = required_role
        self.resource = resource


class RateLimitError(BlacklistError):
    """
    Rate Limiting 관련 예외

    요청 한도 초과, 속도 제한 등에 사용됩니다.
    """

    def __init__(
        self,
        message: str,
        identifier: Optional[str] = None,
        limit: Optional[int] = None,
        window_seconds: Optional[int] = None,
        retry_after: Optional[int] = None,
    ):
        details = {}
        if identifier:
            details["identifier"] = identifier
        if limit is not None:
            details["limit"] = limit
        if window_seconds is not None:
            details["window_seconds"] = window_seconds
        if retry_after is not None:
            details["retry_after"] = retry_after

        super().__init__(message, "RATE_LIMIT_ERROR", details)
        self.identifier = identifier
        self.limit = limit
        self.window_seconds = window_seconds
        self.retry_after = retry_after


class DataProcessingError(BlacklistError):
    """
    데이터 처리 관련 예외

    파일 읽기/쓰기 실패, 데이터 파싱 오류, 변환 실패 등에 사용됩니다.
    """

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        operation: Optional[str] = None,
        data_type: Optional[str] = None,
    ):
        details = {}
        if file_path:
            details["file_path"] = file_path
        if operation:
            details["operation"] = operation
        if data_type:
            details["data_type"] = data_type

        super().__init__(message, "DATA_PROCESSING_ERROR", details)
        self.file_path = file_path
        self.operation = operation
        self.data_type = data_type


class DataError(BlacklistError):
    """
    데이터 관련 예외 (DataProcessingError의 별칭)

    데이터 로드, 검색, 처리 실패 등에 사용됩니다.
    """

    def __init__(
        self,
        message: str,
        data_source: Optional[str] = None,
        operation: Optional[str] = None,
    ):
        details = {}
        if data_source:
            details["data_source"] = data_source
        if operation:
            details["operation"] = operation

        super().__init__(message, "DATA_ERROR", details)
        self.data_source = data_source
        self.operation = operation


class ConnectionError(BlacklistError):
    """
    연결 관련 예외

    네트워크 연결 실패, API 호출 실패 등에 사용됩니다.
    """

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        timeout: Optional[int] = None,
        status_code: Optional[int] = None,
    ):
        details = {}
        if url:
            details["url"] = url
        if timeout is not None:
            details["timeout"] = timeout
        if status_code is not None:
            details["status_code"] = status_code

        super().__init__(message, "CONNECTION_ERROR", details)
        self.url = url
        self.timeout = timeout
        self.status_code = status_code


class ServiceUnavailableError(BlacklistError):
    """
    서비스 불가 상태 예외

    외부 API 연결 실패, 시스템 과부하, 유지보수 모드 등에 사용됩니다.
    """

    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        retry_after: Optional[int] = None,
        status_code: Optional[int] = None,
    ):
        details = {}
        if service_name:
            details["service_name"] = service_name
        if retry_after is not None:
            details["retry_after"] = retry_after
        if status_code is not None:
            details["status_code"] = status_code

        super().__init__(message, "SERVICE_UNAVAILABLE_ERROR", details)
        self.service_name = service_name
        self.retry_after = retry_after
        self.status_code = status_code


class ConfigurationError(BlacklistError):
    """
    구성 관련 예외

    환경 변수 누락, 설정 파일 오류, 잘못된 구성 값 등에 사용됩니다.
    """

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_file: Optional[str] = None,
        expected_type: Optional[str] = None,
    ):
        details = {}
        if config_key:
            details["config_key"] = config_key
        if config_file:
            details["config_file"] = config_file
        if expected_type:
            details["expected_type"] = expected_type

        super().__init__(message, "CONFIGURATION_ERROR", details)
        self.config_key = config_key
        self.config_file = config_file
        self.expected_type = expected_type


class DependencyError(BlacklistError):
    """
    의존성 관련 예외

    의존성 주입 실패, 순환 의존성, 서비스 해결 실패 등에 사용됩니다.
    """

    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        dependency_chain: Optional[List[str]] = None,
    ):
        details = {}
        if service_name:
            details["service_name"] = service_name
        if dependency_chain:
            details["dependency_chain"] = dependency_chain

        super().__init__(message, "DEPENDENCY_ERROR", details)
        self.service_name = service_name
        self.dependency_chain = dependency_chain or []


class MonitoringError(BlacklistError):
    """
    모니터링 관련 예외

    메트릭 수집 실패, 헬스체크 오류, 알림 전송 실패 등에 사용됩니다.
    """

    def __init__(
        self,
        message: str,
        metric_name: Optional[str] = None,
        component: Optional[str] = None,
    ):
        details = {}
        if metric_name:
            details["metric_name"] = metric_name
        if component:
            details["component"] = component

        super().__init__(message, "MONITORING_ERROR", details)
        self.metric_name = metric_name
        self.component = component


# 편의 함수들
def handle_exception(
    exc: Exception, context: Optional[Dict[str, Any]] = None
) -> BlacklistError:
    """
    일반 예외를 Secudium 예외로 변환

    Args:
        exc: 원본 예외
        context: 추가 컨텍스트 정보

    Returns:
        BlacklistError 인스턴스
    """
    if isinstance(exc, BlacklistError):
        return exc

    # 예외 타입에 따른 적절한 BlacklistError 변환
    if isinstance(exc, ValueError):
        return ValidationError(str(exc), cause=exc)
    elif isinstance(exc, FileNotFoundError):
        return DataProcessingError(f"File not found: {exc}", cause=exc)
    elif isinstance(exc, PermissionError):
        return AuthorizationError(f"Permission denied: {exc}", cause=exc)
    elif isinstance(exc, ConnectionError):
        return ServiceUnavailableError(f"Connection failed: {exc}", cause=exc)
    else:
        return BlacklistError(f"Unexpected error: {exc}", cause=exc, details=context)


def log_exception(exc: Exception, logger_instance: Optional[logging.Logger] = None):
    """
    예외를 구조화된 형태로 로깅

    Args:
        exc: 로깅할 예외
        logger_instance: 사용할 로거 (기본값: 모듈 로거)
    """
    log = logger_instance or logger

    if isinstance(exc, BlacklistError):
        log.error(
            f"{exc.error_code}: {exc.message}",
            extra={
                "error_code": exc.error_code,
                "details": exc.details,
                "cause": str(exc.cause) if exc.cause else None,
            },
        )
    else:
        log.error(f"Unhandled exception: {exc}", exc_info=True)


def create_error_response(
    exc: Exception, include_details: bool = False
) -> Dict[str, Any]:
    """
    예외를 API 응답 형태로 변환

    Args:
        exc: 변환할 예외
        include_details: 상세 정보 포함 여부

    Returns:
        API 응답 딕셔너리
    """
    if isinstance(exc, BlacklistError):
        response = exc.to_api_response()
        if not include_details:
            response.pop("details", None)
        return response
    else:
        return {
            "error": "Internal server error",
            "error_code": "INTERNAL_ERROR",
            "message": str(exc) if include_details else "An unexpected error occurred",
        }
