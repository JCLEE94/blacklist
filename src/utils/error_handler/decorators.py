"""Error handling decorators"""

import functools
import logging
from typing import Any, Callable, Union

from flask import Response, jsonify

from .custom_errors import (AuthenticationError, AuthorizationError,
                            ValidationError)

logger = logging.getLogger(__name__)


def safe_execute(
    default_return: Any = None,
    exceptions: tuple = (Exception,),
    log_level: str = "error",
    message: str = "Operation failed",
) -> Callable:
    """
    안전한 함수 실행 데코레이터

    Args:
        default_return: 에러 시 반환할 기본값
        exceptions: 처리할 예외 타입들
        log_level: 로그 레벨 (debug, info, warning, error)
        message: 에러 메시지
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                log_func = getattr(logger, log_level, logger.error)
                log_func(f"{message} in {func.__name__}: {str(e)}")
                return default_return

        return wrapper

    return decorator


def handle_api_errors(func: Callable) -> Callable:
    """
    API 엔드포인트 에러 처리 데코레이터
    커스텀 에러를 적절한 HTTP 응답으로 변환
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Union[Response, Any]:
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error in {func.__name__}: {e.message}")
            return (
                jsonify(
                    {
                        "error": e.message,
                        "error_code": e.code,
                        "details": e.details,
                    }
                ),
                422,
            )
        except AuthenticationError as e:
            logger.warning(f"Authentication error in {func.__name__}: {e.message}")
            return jsonify({"error": e.message, "error_code": e.code}), 401
        except AuthorizationError as e:
            logger.warning(f"Authorization error in {func.__name__}: {e.message}")
            return jsonify({"error": e.message, "error_code": e.code}), 403
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            return (
                jsonify(
                    {"error": "Internal server error", "error_code": "INTERNAL_ERROR"}
                ),
                500,
            )

    return wrapper


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


def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable:
    """재시도 데코레이터 (alias for retry_on_error)"""
    return retry_on_error(max_attempts, delay, backoff, exceptions)


def log_performance(operation: str) -> Callable:
    """
    성능 측정 및 로깅 데코레이터

    Args:
        operation: 작업 이름
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time

            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time

                if elapsed > 1.0:  # 1초 이상 걸린 작업만 로깅
                    logger.warning(f"{operation} took {elapsed:.2f}s")
                else:
                    logger.debug(f"{operation} completed in {elapsed:.3f}s")

                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"{operation} failed after {elapsed:.2f}s: {e}")
                raise

        return wrapper

    return decorator
