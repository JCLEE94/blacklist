#!/usr/bin/env python3
"""
설정 관련 타입 정의
열거형과 데이터클래스 정의
"""
from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional


class SettingType(Enum):
    """설정 타입 열거형"""

    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    JSON = "json"
    PASSWORD = "password"  # 암호화된 비밀번호
    URL = "url"
    EMAIL = "email"


class SettingCategory(Enum):
    """설정 카테고리"""

    GENERAL = "general"  # 일반 설정
    COLLECTION = "collection"  # 수집 관련 설정
    SECURITY = "security"  # 보안 설정
    NOTIFICATION = "notification"  # 알림 설정
    PERFORMANCE = "performance"  # 성능 설정
    INTEGRATION = "integration"  # 외부 연동 설정
    CREDENTIALS = "credentials"  # 인증 정보


@dataclass
class SettingDefinition:
    """설정 정의"""

    key: str  # 설정 키
    name: str  # 표시 이름
    description: str  # 설명
    category: SettingCategory  # 카테고리
    setting_type: SettingType  # 데이터 타입
    default_value: Any  # 기본값
    required: bool = False  # 필수 여부
    options: Optional[List[str]] = None  # 선택지 (select 타입용)
    min_value: Optional[int] = None  # 최소값 (숫자형용)
    max_value: Optional[int] = None  # 최대값 (숫자형용)
    validation_regex: Optional[str] = None  # 검증용 정규식
    encrypted: bool = False  # 암호화 여부
