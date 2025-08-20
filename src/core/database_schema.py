"""
데이터베이스 스키마 정의 및 마이그레이션 (호환성 래퍼)

이 모듈은 모듈화된 데이터베이스 시스템에 대한 호환성 래퍼입니다.
새로운 코드는 src.core.database 모듈을 직접 사용하시기 바랍니다.
"""

import logging
from typing import Any
from typing import Dict
from typing import Optional

# 새로운 모듈화된 시스템에서 임포트
from .database import DatabaseSchema
from .database import get_database_schema
from .database import initialize_database
from .database import migrate_database

# 로깅 설정
logger = logging.getLogger(__name__)

# 하위 호환성을 위한 모든 함수와 클래스 재내보내기
__all__ = [
    "DatabaseSchema",
    "get_database_schema",
    "initialize_database",
    "migrate_database",
]

# 경고 메시지 출력
logger.warning(
    "database_schema.py is deprecated. "
    "Please use 'from src.core.database import ...' instead."
)
