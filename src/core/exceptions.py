"""
예외 클래스 정의 - 모듈화된 구조

시스템에서 사용하는 모든 커스텀 예외를 정의합니다.
일관된 에러 처리와 디버깅을 위해 구조화된 예외 계층을 제공합니다.

이 파일은 하위 모듈에서 예외 클래스들을 임포트하여 재정의하는 방식으로
기존 코드와의 호환성을 유지하면서 모듈화를 구현합니다.
"""

# 모듈화된 예외 클래스들을 임포트하여 재정의
# 기존 코드에서 'from src.core.exceptions import ValidationError'가 계속 작동함

try:
    # 모듈화된 구조에서 모든 예외 클래스 임포트
    from .exceptions import (
        AuthenticationError,
        AuthorizationError,
        BlacklistError,
        CacheError,
        ConfigurationError,
        ConnectionError,
        DataError,
        DataProcessingError,
        DatabaseError,
        DependencyError,
        MonitoringError,
        RateLimitError,
        ServiceUnavailableError,
        ValidationError,
        create_error_response,
        handle_exception,
        log_exception,
    )
    
    # 모든 클래스와 함수를 현재 모듈에서 사용할 수 있도록 정의
    __all__ = [
        "BlacklistError",
        "ValidationError", 
        "CacheError",
        "DatabaseError",
        "AuthenticationError",
        "AuthorizationError", 
        "RateLimitError",
        "DataProcessingError",
        "DataError",
        "ConnectionError",
        "ServiceUnavailableError",
        "ConfigurationError",
        "DependencyError", 
        "MonitoringError",
        "handle_exception",
        "log_exception", 
        "create_error_response",
    ]
    
except ImportError:
    # 모듈화된 구조를 불러올 수 없는 경우 기본 구현 사용
    import logging
    from typing import Any, Dict, List, Optional

    logger = logging.getLogger(__name__)

    class BlacklistError(Exception):
        """기본 예외 클래스 - 폴백 구현"""
        def __init__(self, message: str, error_code: Optional[str] = None, 
                     details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
            super().__init__(message)
            self.message = message
            self.error_code = error_code or self.__class__.__name__
            self.details = details or {}
            self.cause = cause
            logger.error(f"{self.error_code}: {message}")
        
        def to_api_response(self) -> Dict[str, Any]:
            return {"error": self.message, "error_code": self.error_code, "details": self.details}

    # 다른 예외 클래스들도 기본 구현으로 정의
    ValidationError = type("ValidationError", (BlacklistError,), {})
    CacheError = type("CacheError", (BlacklistError,), {})
    DatabaseError = type("DatabaseError", (BlacklistError,), {})
    
    def handle_exception(exc: Exception, context: Optional[Dict[str, Any]] = None) -> BlacklistError:
        return BlacklistError(f"Error: {exc}", details=context)
    
    def log_exception(exc: Exception, logger_instance: Optional[logging.Logger] = None):
        (logger_instance or logger).error(f"Exception: {exc}")
    
    def create_error_response(exc: Exception, include_details: bool = False) -> Dict[str, Any]:
        return {"error": str(exc), "error_code": "INTERNAL_ERROR"}
