"""Base exception classes"""

import logging
from typing import Any, Dict, Optional

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
            "{self.error_code}: {message}",
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
