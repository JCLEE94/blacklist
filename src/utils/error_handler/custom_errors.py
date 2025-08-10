"""Custom error classes"""

from typing import Dict, Optional


class BaseError(Exception):
    """기본 커스텀 에러 클래스"""

    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        status_code: int = 500,
        details: Optional[Dict] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(BaseError):
    """데이터 검증 에러"""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            details={"field": field} if field else {},
        )


class AuthenticationError(BaseError):
    """인증 에러"""

    def __init__(self, message: str = "인증이 필요합니다", **kwargs):
        super().__init__(message=message, code="AUTHENTICATION_ERROR", status_code=401)


class AuthorizationError(BaseError):
    """권한 에러"""

    def __init__(self, message: str = "접근 권한이 없습니다", **kwargs):
        super().__init__(message=message, code="AUTHORIZATION_ERROR", status_code=403)


class ResourceNotFoundError(BaseError):
    """리소스 미발견 에러"""

    def __init__(self, resource: str, identifier: Optional[str] = None, **kwargs):
        message = f"{resource}을(를) 찾을 수 없습니다"
        if identifier:
            message += f" (ID: {identifier})"
        super().__init__(
            message=message,
            code="RESOURCE_NOT_FOUND",
            status_code=404,
            details={"resource": resource, "identifier": identifier},
        )


class ExternalServiceError(BaseError):
    """외부 서비스 에러"""

    def __init__(self, service: str, message: str, **kwargs):
        super().__init__(
            message=f"{service} 서비스 오류: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=503,
            details={"service": service},
        )


class CollectionError(BaseError):
    """수집 관련 에러"""

    def __init__(self, source: str, message: str, **kwargs):
        super().__init__(
            message=f"{source} 수집 오류: {message}",
            code="COLLECTION_ERROR",
            status_code=500,
            details={"source": source},
        )


class DatabaseError(BaseError):
    """데이터베이스 에러"""

    def __init__(self, operation: str, message: str, **kwargs):
        super().__init__(
            message=f"데이터베이스 {operation} 오류: {message}",
            code="DATABASE_ERROR",
            status_code=500,
            details={"operation": operation},
        )
