# !/usr/bin/env python3
"""
공통 모듈 및 유틸리티
전체 프로젝트에서 사용되는 공통 함수들
"""

import logging
from datetime import datetime
from typing import Any, Dict


# 공통 로거 설정
def get_logger(name: str) -> logging.Logger:
    """표준화된 로거 생성"""
    return logging.getLogger(name)


# 공통 함수
def format_timestamp(dt: datetime = None) -> str:
    """표준 타임스탬프 형식"""
    if dt is None:
        dt = datetime.now()
    return dt.isoformat()


def safe_dict_get(d: Dict[str, Any], key: str, default: Any = None) -> Any:
    """안전한 딕셔너리 값 가져오기"""
    try:
        return d.get(key, default)
    except Exception:
        return default
