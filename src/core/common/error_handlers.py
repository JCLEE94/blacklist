"""
통합 에러 처리 유틸리티
일관된 에러 처리 및 로깅 제공
"""
import functools
import logging
from typing import TypeVar, Callable, Any, Optional, Type, Union, Tuple
from flask import jsonify, Response

from src.core.exceptions import (
    BlacklistError, ValidationError, CacheError, DatabaseError,
    AuthenticationError, AuthorizationError, RateLimitError,
    DataProcessingError, ConnectionError as CustomConnectionError,
    ServiceUnavailableError, ConfigurationError
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


def safe_execute(
    default_return: Any = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    log_level: str = "error",
    message: str = "Operation failed"
) -> Callable:
    """
    안전한 함수 실행 데코레이터
    
    Args:
        default_return: 에러 시 반환할 기본값
        exceptions: 처리할 예외 타입들
        log_level: 로그 레벨 (debug, info, warning, error)
        message: 에러 메시지
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
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
    BlacklistError를 적절한 HTTP 응답으로 변환
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Union[Response, Any]:
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error in {func.__name__}: {e.message}")
            return jsonify({
                "error": e.message,
                "error_code": e.error_code,
                "details": e.details
            }), 422
        except AuthenticationError as e:
            logger.warning(f"Authentication error in {func.__name__}: {e.message}")
            return jsonify({
                "error": e.message,
                "error_code": e.error_code
            }), 401
        except AuthorizationError as e:
            logger.warning(f"Authorization error in {func.__name__}: {e.message}")
            return jsonify({
                "error": e.message,
                "error_code": e.error_code
            }), 403
        except RateLimitError as e:
            logger.warning(f"Rate limit error in {func.__name__}: {e.message}")
            response = jsonify({
                "error": e.message,
                "error_code": e.error_code,
                "retry_after": e.retry_after
            })
            if e.retry_after:
                response.headers['Retry-After'] = str(e.retry_after)
            return response, 429
        except (DatabaseError, CacheError) as e:
            logger.error(f"Storage error in {func.__name__}: {e.message}")
            return jsonify({
                "error": "Internal storage error",
                "error_code": "STORAGE_ERROR"
            }), 500
        except ServiceUnavailableError as e:
            logger.error(f"Service unavailable in {func.__name__}: {e.message}")
            return jsonify({
                "error": e.message,
                "error_code": e.error_code
            }), 503
        except BlacklistError as e:
            logger.error(f"Blacklist error in {func.__name__}: {e.message}")
            return jsonify(e.to_api_response()), 500
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}")
            return jsonify({
                "error": "Internal server error",
                "error_code": "INTERNAL_ERROR"
            }), 500
    return wrapper


def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    """
    실패 시 재시도 데코레이터
    
    Args:
        max_attempts: 최대 시도 횟수
        delay: 초기 대기 시간 (초)
        backoff: 백오프 배수
        exceptions: 재시도할 예외 타입들
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            import time
            
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
            
            raise last_exception
        return wrapper
    return decorator


class ErrorContext:
    """에러 컨텍스트 관리자"""
    
    def __init__(
        self,
        operation: str,
        default_return: Any = None,
        suppress: bool = False,
        log_level: str = "error"
    ):
        """
        Args:
            operation: 작업 설명
            default_return: 에러 시 반환값
            suppress: 에러 억제 여부
            log_level: 로그 레벨
        """
        self.operation = operation
        self.default_return = default_return
        self.suppress = suppress
        self.log_level = log_level
        self.exception = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.exception = exc_val
            log_func = getattr(logger, self.log_level, logger.error)
            log_func(f"Error during {self.operation}: {exc_val}")
            
            if self.suppress:
                return True  # 예외 억제
        return False


def validate_and_convert(
    data: Any,
    converter: Callable[[Any], T],
    error_message: str = "Invalid data format",
    field: Optional[str] = None
) -> T:
    """
    데이터 검증 및 변환 헬퍼
    
    Args:
        data: 변환할 데이터
        converter: 변환 함수
        error_message: 에러 메시지
        field: 필드 이름 (옵션)
        
    Returns:
        변환된 데이터
        
    Raises:
        ValidationError: 변환 실패 시
    """
    try:
        return converter(data)
    except (ValueError, TypeError, KeyError) as e:
        raise ValidationError(
            message=error_message,
            field=field,
            value=data,
            validation_errors=[str(e)]
        )


def log_performance(operation: str) -> Callable:
    """
    성능 측정 및 로깅 데코레이터
    
    Args:
        operation: 작업 이름
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
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