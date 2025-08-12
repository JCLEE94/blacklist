"""Error context management"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ErrorContext:
    """
    에러 컨텍스트 관리자
    with 문을 사용하여 에러를 안전하게 처리
    """

    def __init__(
        self,
        operation: str,
        default_return: Any = None,
        suppress: bool = True,
        log_level: str = "error",
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
            log_func("Error during {self.operation}: {exc_val}")

            if self.suppress:
                return True  # 예외 억제
        return False
