#!/usr/bin/env python3
"""
기본 설정 정의
애플리케이션 초기 설정값들
"""
import os

from .setting_types import SettingCategory, SettingDefinition, SettingType


def get_default_settings():
    """기본 설정 리스트 반환"""
    return [
        # 일반 설정
        SettingDefinition(
            key="app_name",
            name="애플리케이션 이름",
            description="블랙리스트 관리 시스템의 표시 이름",
            category=SettingCategory.GENERAL,
            setting_type=SettingType.STRING,
            default_value="Blacklist Management System",
        ),
        SettingDefinition(
            key="timezone",
            name="시간대",
            description="시스템에서 사용할 시간대",
            category=SettingCategory.GENERAL,
            setting_type=SettingType.STRING,
            default_value="Asia/Seoul",
            options=["Asia/Seoul", "UTC", "Asia/Tokyo", "America/New_York"],
        ),
        SettingDefinition(
            key="items_per_page",
            name="페이지당 항목 수",
            description="목록 페이지에서 한 번에 표시할 항목 수",
            category=SettingCategory.GENERAL,
            setting_type=SettingType.INTEGER,
            default_value=50,
            min_value=10,
            max_value=500,
        ),
        # 수집 설정
        SettingDefinition(
            key="collection_enabled",
            name="데이터 수집 활성화",
            description="외부 소스로부터 데이터 수집 여부",
            category=SettingCategory.COLLECTION,
            setting_type=SettingType.BOOLEAN,
            default_value=os.getenv("COLLECTION_ENABLED", "false").lower() == "true",
        ),
        SettingDefinition(
            key="collection_interval",
            name="수집 주기",
            description="자동 데이터 수집 간격(분)",
            category=SettingCategory.COLLECTION,
            setting_type=SettingType.INTEGER,
            default_value=60,
            min_value=5,
            max_value=1440,
        ),
        SettingDefinition(
            key="regtech_enabled",
            name="REGTECH 소스 활성화",
            description="REGTECH 데이터 수집 여부",
            category=SettingCategory.COLLECTION,
            setting_type=SettingType.BOOLEAN,
            default_value=True,
        ),
        SettingDefinition(
            key="secudium_enabled",
            name="SECUDIUM 소스 활성화",
            description="SECUDIUM 데이터 수집 여부",
            category=SettingCategory.COLLECTION,
            setting_type=SettingType.BOOLEAN,
            default_value=True,
        ),
        # 보안 설정
        SettingDefinition(
            key="force_disable_collection",
            name="수집 강제 비활성화",
            description="모든 외부 인증 차단 (보안 모드)",
            category=SettingCategory.SECURITY,
            setting_type=SettingType.BOOLEAN,
            default_value=os.getenv("FORCE_DISABLE_COLLECTION", "true").lower()
            == "true",
        ),
        SettingDefinition(
            key="max_auth_attempts",
            name="최대 인증 시도",
            description="로그인 시도 최대 횟수",
            category=SettingCategory.SECURITY,
            setting_type=SettingType.INTEGER,
            default_value=int(os.getenv("MAX_AUTH_ATTEMPTS", "10")),
            min_value=1,
            max_value=100,
        ),
        # 인증 정보
        SettingDefinition(
            key="regtech_username",
            name="REGTECH 사용자명",
            description="REGTECH 로그인 사용자명",
            category=SettingCategory.CREDENTIALS,
            setting_type=SettingType.STRING,
            default_value=os.getenv("REGTECH_USERNAME", ""),
            required=True,
        ),
        SettingDefinition(
            key="regtech_password",
            name="REGTECH 비밀번호",
            description="REGTECH 로그인 비밀번호",
            category=SettingCategory.CREDENTIALS,
            setting_type=SettingType.PASSWORD,
            default_value=os.getenv("REGTECH_PASSWORD", ""),
            encrypted=True,
            required=True,
        ),
        SettingDefinition(
            key="secudium_username",
            name="SECUDIUM 사용자명",
            description="SECUDIUM 로그인 사용자명",
            category=SettingCategory.CREDENTIALS,
            setting_type=SettingType.STRING,
            default_value=os.getenv("SECUDIUM_USERNAME", ""),
            required=True,
        ),
        SettingDefinition(
            key="secudium_password",
            name="SECUDIUM 비밀번호",
            description="SECUDIUM 로그인 비밀번호",
            category=SettingCategory.CREDENTIALS,
            setting_type=SettingType.PASSWORD,
            default_value=os.getenv("SECUDIUM_PASSWORD", ""),
            encrypted=True,
            required=True,
        ),
    ]
