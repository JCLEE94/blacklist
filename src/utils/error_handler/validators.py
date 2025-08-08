"""Validation utilities"""

import ipaddress
from typing import Any, Callable, Dict, Optional

from .custom_errors import ValidationError


def validate_required_fields(data: Dict, required_fields: list) -> None:
    """필수 필드 검증"""
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValidationError(
            f"필수 필드가 누락되었습니다: {', '.join(missing_fields)}",
            field=missing_fields[0],
        )


def validate_ip_format(ip: str) -> bool:
    """IP 형식 검증"""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        raise ValidationError(f"유효하지 않은 IP 주소입니다: {ip}", field="ip")


def validate_and_convert(
    data: Any,
    converter: Callable[[Any], Any],
    error_message: str = "Invalid data format",
    field: Optional[str] = None,
) -> Any:
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
    except (ValueError, TypeError, KeyError):
        raise ValidationError(message=error_message, field=field)
