from ..common.imports import jsonify, request, logger

"""Core error handler class"""

import functools
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Union

from werkzeug.exceptions import HTTPException

from .custom_errors import BaseError

try:
    from src.utils.github_issue_reporter import report_error_to_github
except ImportError:

    def report_error_to_github(error, context):
        return None




class ErrorHandler:
    """중앙 집중형 에러 핸들러"""

    def __init__(self):
        self.error_stats = {}
        self.max_error_logs = 1000
        self.error_logs = []

    def format_error_response(
        self, error: Union[BaseError, Exception], request_id: Optional[str] = None
    ) -> tuple[Dict[str, Any], int]:
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
        if current_app and current_app.debug:
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
        should_create_issue = self._should_create_github_issue(error)

        if should_create_issue:
            try:
                issue_url = report_error_to_github(error, context)
                if issue_url:
                    logger.info(
                        f"GitHub issue created for error {error_code}: {issue_url}"
                    )
                    error_log["github_issue"] = issue_url
            except Exception as github_error:
                logger.error(f"Failed to create GitHub issue: {github_error}")

        self._log_error_message(error, error_code, context)

        # Return the error log entry for testing and further processing
        return error_log

    def _should_create_github_issue(self, error: Exception) -> bool:
        """GitHub 이슈 생성 여부 결정"""
        if isinstance(error, BaseError):
            return error.status_code >= 500
        return True  # 예상치 못한 예외는 모두 GitHub 이슈로 생성

    def _log_error_message(
        self, error: Exception, error_code: str, context: Optional[Dict]
    ):
        """에러 메시지 로깅"""
        if isinstance(error, BaseError):
            if error.status_code >= 500:
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
            logger.error(
                f"Unexpected error: {error}", exc_info=True, extra={"context": context}
            )

    def get_error_stats(self) -> Dict[str, Any]:
        """에러 통계 조회"""
        return {
            "stats": self.error_stats,
            "recent_errors": self.error_logs[-10:],  # 최근 10개
            "total_errors": sum(stat["count"] for stat in self.error_stats.values()),
        }

    def handle_api_error(self, func: Callable) -> Callable:
        """예전 스타일 API 에러 처리 데코레이터"""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                request_id = request.headers.get(
                    "X-Request-ID", str(datetime.utcnow().timestamp())
                )
                return func(*args, **kwargs)
            except (BaseError, HTTPException, Exception) as e:
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
            self.log_error(e, {"function": getattr(func, "__name__", "anonymous")})
            if raise_on_error:
                raise
            return default
