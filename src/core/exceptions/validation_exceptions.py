"""Validation related exceptions"""

from typing import Any
from typing import List
from typing import Optional

from .base_exceptions import BlacklistError


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
