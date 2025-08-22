from ..common.imports import jsonify, logger

"""Error handling decorators"""

import functools
from typing import Any, Callable, Union


from .custom_errors import AuthenticationError, AuthorizationError, ValidationError



def safe_execute(
    func: Callable = None,
    default: Any = None,
    exceptions: tuple = (Exception,),
    log_level: str = "error",
    message: str = "Operation failed",
) -> Any:
    """
    안전한 함수 실행 - 함수를 직접 실행하거나 데코레이터로 사용

    Args:
        func: 실행할 함수 (직접 호출 시)
        default: 에러 시 반환할 기본값
        exceptions: 처리할 예외 타입들
        log_level: 로그 레벨 (debug, info, warning, error)
        message: 에러 메시지
    """

    def execute_safely(target_func):
        try:
            return target_func()
        except exceptions as e:
            log_func = getattr(logger, log_level, logger.error)
            log_func(f"{message} in {target_func.__name__}: {str(e)}")
            return default

    if func is not None:
        # 직접 함수 실행
        return execute_safely(func)

    # 데코레이터로 사용
    def decorator(target_func: Callable) -> Callable:
        @functools.wraps(target_func)
        def wrapper(*args, **kwargs):
            def bound_func():
                return target_func(*args, **kwargs)

            return execute_safely(bound_func)

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


def log_performance(func: Callable = None, *, operation: str = None) -> Callable:
    """
    성능 측정 및 로깅 데코레이터

    Args:
        func: 데코레이트할 함수
        operation: 작업 이름 (선택사항, 기본값은 함수명)
    """

    def decorator(target_func: Callable) -> Callable:
        @functools.wraps(target_func)
        def wrapper(*args, **kwargs):
            import time

            op_name = operation or target_func.__name__
            start_time = time.time()

            try:
                result = target_func(*args, **kwargs)
                elapsed = time.time() - start_time

                if elapsed > 1.0:  # 1초 이상 걸린 작업만 로깅
                    logger.warning(f"{op_name} took {elapsed:.2f}s")
                else:
                    logger.debug(f"{op_name} completed in {elapsed:.3f}s")

                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"{op_name} failed after {elapsed:.2f}s: {e}")
                raise

        return wrapper

    if func is None:
        # 매개변수와 함께 호출: @log_performance(operation="test")
        return decorator
    else:
        # 매개변수 없이 호출: @log_performance
        return decorator(func)
