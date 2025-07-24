"""
IP 및 데이터 검증 유틸리티
공통 모듈로 마이그레이션 - 후방 호환성 유지
"""
from typing import List, Optional, Tuple

# 공통 모듈에서 import
from .common import DateUtils
from .common import sanitize_ip as _sanitize_ip
from .common import validate_ip as _validate_ip
from .common import validate_ip_list as _validate_ip_list


# 후방 호환성을 위한 래퍼 함수들
def validate_ip(ip_address: str) -> bool:
    """IP 주소 형식 검증"""
    return _validate_ip(ip_address)


def validate_month_format(month: str) -> bool:
    """월 형식 검증 (YYYY-MM)"""
    return DateUtils.validate_month_format(month)


def validate_ip_list(
    ip_list: List[str], max_count: int = 100
) -> Tuple[List[str], List[str]]:
    """
    IP 리스트 검증
    Returns: (valid_ips, invalid_ips)
    """
    return _validate_ip_list(ip_list, max_count)


def sanitize_ip(ip_address: str) -> Optional[str]:
    """IP 주소 정리 및 정규화"""
    return _sanitize_ip(ip_address)
