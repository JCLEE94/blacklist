#!/usr/bin/env python3
"""
통합 에러 핸들링 시스템
표준화된 에러 처리 및 로깅을 위한 중앙 집중형 모듈
"""

import functools
import json
import logging
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Type, Union

from flask import current_app, jsonify, request
from werkzeug.exceptions import HTTPException

# GitHub 이슈 리포터 import
from src.utils.github_issue_reporter import report_error_to_github

logger = logging.getLogger(__name__)


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


class ErrorHandler:
    """중앙 집중형 에러 핸들러"""

    def __init__(self):
        self.error_stats = {}
        self.max_error_logs = 1000
        self.error_logs = []

    def format_error_response(
        self, error: Union[BaseError, Exception], request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """표준 에러 응답 형식 생성"""
        if isinstance(error, BaseError):
            response = {
                "error": {
                    "code": error.code,
                    "message": error.message,
                    "details": error.details,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            }
            status_code = error.status_code
        elif isinstance(error, HTTPException):
            response = {
                "error": {
                    "code": error.name.upper().replace(" ", "_"),
                    "message": error.description or str(error),
                    "details": {},
                    "timestamp": datetime.utcnow().isoformat(),
                }
            }
            status_code = error.code
        else:
            response = {
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "내부 서버 오류가 발생했습니다",
                    "details": {},
                    "timestamp": datetime.utcnow().isoformat(),
                }
            }
            status_code = 500

        # 요청 ID 추가 (디버깅용)
        if request_id:
            response["error"]["request_id"] = request_id

        # 개발 환경에서는 스택 트레이스 포함
        if current_app.debug:
            response["error"]["stack_trace"] = traceback.format_exc()

        return response, status_code

    def log_error(self, error: Exception, context: Optional[Dict] = None):
        """에러 로깅, 통계 수집 및 GitHub 이슈 생성"""
        error_type = type(error).__name__
        error_code = getattr(error, "code", "UNKNOWN_ERROR")

        # 에러 통계 업데이트
        if error_code not in self.error_stats:
            self.error_stats[error_code] = {
                "count": 0,
                "first_seen": datetime.utcnow().isoformat(),
                "last_seen": None,
            }

        self.error_stats[error_code]["count"] += 1
        self.error_stats[error_code]["last_seen"] = datetime.utcnow().isoformat()

        # 에러 로그 저장
        error_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": error_type,
            "code": error_code,
            "message": str(error),
            "context": context or {},
            "request": {
                "method": request.method if request else None,
                "path": request.path if request else None,
                "ip": request.remote_addr if request else None,
            },
        }

        self.error_logs.append(error_log)
        if len(self.error_logs) > self.max_error_logs:
            self.error_logs.pop(0)

        # GitHub 이슈 생성 (심각한 에러만)
        should_create_issue = False
        if isinstance(error, BaseError):
            # 500번대 에러만 GitHub 이슈로 생성
            if error.status_code >= 500:
                should_create_issue = True
                logger.error(
                    f"{error_code}: {error.message}",
                    extra={"error_details": error.details, "context": context},
                )
            else:
                logger.warning(
                    f"{error_code}: {error.message}",
                    extra={"error_details": error.details, "context": context},
                )
        else:
            # 예상치 못한 예외는 모두 GitHub 이슈로 생성
            should_create_issue = True
            logger.error(
                f"Unexpected error: {error}", exc_info=True, extra={"context": context}
            )

        # GitHub 이슈 생성
        if should_create_issue:
            try:
                issue_url = report_error_to_github(error, context)
                if issue_url:
                    logger.info(
                        f"GitHub issue created for error {error_code}: {issue_url}"
                    )
                    # 에러 로그에 이슈 URL 추가
                    error_log["github_issue"] = issue_url
            except Exception as github_error:
                logger.error(f"Failed to create GitHub issue: {github_error}")

    def get_error_stats(self) -> Dict[str, Any]:
        """에러 통계 조회"""
        return {
            "stats": self.error_stats,
            "recent_errors": self.error_logs[-10:],  # 최근 10개
            "total_errors": sum(stat["count"] for stat in self.error_stats.values()),
        }

    def handle_api_error(self, func: Callable) -> Callable:
        """API 에러 처리 데코레이터"""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            request_id = request.headers.get(
                "X-Request-ID", datetime.utcnow().timestamp()
            )

            try:
                return func(*args, **kwargs)
            except BaseError as e:
                self.log_error(e, {"function": func.__name__, "args": str(args)})
                response, status_code = self.format_error_response(e, request_id)
                return jsonify(response), status_code
            except HTTPException as e:
                self.log_error(e, {"function": func.__name__, "args": str(args)})
                response, status_code = self.format_error_response(e, request_id)
                return jsonify(response), status_code
            except Exception as e:
                self.log_error(e, {"function": func.__name__, "args": str(args)})
                response, status_code = self.format_error_response(e, request_id)
                return jsonify(response), status_code

        return wrapper

    def safe_execute(
        self,
        func: Callable,
        default: Any = None,
        error_message: str = "작업 실행 중 오류",
        raise_on_error: bool = False,
    ) -> Any:
        """안전한 함수 실행"""
        try:
            return func()
        except Exception as e:
            self.log_error(e, {"function": func.__name__})
            if raise_on_error:
                raise
            return default


# 전역 에러 핸들러 인스턴스
error_handler = ErrorHandler()


def handle_api_errors(func: Callable) -> Callable:
    """API 에러 처리 데코레이터 (간편 사용)"""
    return error_handler.handle_api_error(func)


def safe_execute(
    func: Callable,
    default: Any = None,
    error_message: str = "작업 실행 중 오류",
    raise_on_error: bool = False,
) -> Any:
    """안전한 함수 실행 (간편 사용)"""
    return error_handler.safe_execute(func, default, error_message, raise_on_error)


def register_error_handlers(app):
    """Flask 앱에 에러 핸들러 등록"""

    @app.errorhandler(BaseError)
    def handle_base_error(error):
        error_handler.log_error(error)
        response, status_code = error_handler.format_error_response(error)
        return jsonify(response), status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        error_handler.log_error(error)
        response, status_code = error_handler.format_error_response(error)
        return jsonify(response), status_code

    @app.errorhandler(Exception)
    def handle_exception(error):
        error_handler.log_error(error)
        response, status_code = error_handler.format_error_response(error)
        return jsonify(response), status_code

    # 에러 통계 엔드포인트 추가
    @app.route("/api/errors/stats", methods=["GET"])
    @handle_api_errors
    def get_error_stats():
        """에러 통계 조회"""
        return jsonify(error_handler.get_error_stats())


# 유틸리티 함수들
def validate_required_fields(data: Dict, required_fields: list) -> None:
    """필수 필드 검증"""
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValidationError(
            f"필수 필드가 누락되었습니다: {', '.join(missing_fields)}", field=missing_fields[0]
        )


def validate_ip_format(ip: str) -> bool:
    """IP 형식 검증"""
    import ipaddress

    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        raise ValidationError(f"유효하지 않은 IP 주소입니다: {ip}", field="ip")


def retry_on_error(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable:
    """재시도 데코레이터"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time

            attempt = 1
            current_delay = delay

            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(f"{func.__name__} 최대 재시도 횟수 초과: {e}")
                        raise

                    logger.warning(
                        f"{func.__name__} 시도 {attempt}/{max_attempts} 실패: {e}"
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
                    attempt += 1

        return wrapper

    return decorator
