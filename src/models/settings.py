#!/usr/bin/env python3
"""
애플리케이션 설정 모델
데이터베이스에 저장되는 동적 설정 관리
"""
import json
import sqlite3
import os
from typing import Any, Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

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
    GENERAL = "general"          # 일반 설정
    COLLECTION = "collection"    # 수집 관련 설정
    SECURITY = "security"        # 보안 설정
    NOTIFICATION = "notification" # 알림 설정
    PERFORMANCE = "performance"  # 성능 설정
    INTEGRATION = "integration"  # 외부 연동 설정
    CREDENTIALS = "credentials"  # 인증 정보

@dataclass
class SettingDefinition:
    """설정 정의"""
    key: str                    # 설정 키
    name: str                   # 표시 이름
    description: str            # 설명
    category: SettingCategory   # 카테고리
    setting_type: SettingType   # 데이터 타입
    default_value: Any          # 기본값
    required: bool = False      # 필수 여부
    options: Optional[List[str]] = None  # 선택지 (select 타입용)
    min_value: Optional[int] = None      # 최소값 (숫자형용)
    max_value: Optional[int] = None      # 최대값 (숫자형용)
    validation_regex: Optional[str] = None  # 검증용 정규식
    encrypted: bool = False     # 암호화 여부

class SettingsManager:
    """설정 관리자 클래스"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            from src.config.settings import settings
            db_uri = settings.database_uri
            if db_uri.startswith('sqlite:///'):
                self.db_path = db_uri[10:]
            elif db_uri.startswith('sqlite://'):
                self.db_path = db_uri[9:]
            else:
                self.db_path = str(settings.instance_dir / 'blacklist.db')
        else:
            self.db_path = db_path
        
        self._ensure_settings_table()
        self._load_default_settings()
    
    def _ensure_settings_table(self):
        """설정 테이블 생성"""
        query = """
        CREATE TABLE IF NOT EXISTS app_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT,
            setting_type TEXT NOT NULL,
            category TEXT NOT NULL,
            encrypted BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(query)
            conn.commit()
    
    def _load_default_settings(self):
        """기본 설정 로드"""
        default_settings = [
            # 일반 설정
            SettingDefinition(
                key="app_name",
                name="애플리케이션 이름",
                description="블랙리스트 관리 시스템의 표시 이름",
                category=SettingCategory.GENERAL,
                setting_type=SettingType.STRING,
                default_value="Blacklist Management System"
            ),
            SettingDefinition(
                key="timezone",
                name="시간대",
                description="시스템에서 사용할 시간대",
                category=SettingCategory.GENERAL,
                setting_type=SettingType.STRING,
                default_value="Asia/Seoul",
                options=["Asia/Seoul", "UTC", "Asia/Tokyo", "America/New_York"]
            ),
            SettingDefinition(
                key="items_per_page",
                name="페이지당 항목 수",
                description="목록 페이지에서 한 번에 표시할 항목 수",
                category=SettingCategory.GENERAL,
                setting_type=SettingType.INTEGER,
                default_value=50,
                min_value=10,
                max_value=500
            ),
            
            # 수집 설정
            SettingDefinition(
                key="collection_enabled",
                name="자동 수집 활성화",
                description="REGTECH/SECUDIUM 자동 수집 기능 활성화",
                category=SettingCategory.COLLECTION,
                setting_type=SettingType.BOOLEAN,
                default_value=True
            ),
            SettingDefinition(
                key="collection_interval_hours",
                name="수집 주기 (시간)",
                description="자동 수집을 실행할 주기 (시간 단위)",
                category=SettingCategory.COLLECTION,
                setting_type=SettingType.INTEGER,
                default_value=6,
                min_value=1,
                max_value=168
            ),
            SettingDefinition(
                key="regtech_enabled",
                name="REGTECH 수집 활성화",
                description="REGTECH 데이터 수집 기능 활성화",
                category=SettingCategory.COLLECTION,
                setting_type=SettingType.BOOLEAN,
                default_value=True
            ),
            SettingDefinition(
                key="secudium_enabled",
                name="SECUDIUM 수집 활성화",
                description="SECUDIUM 데이터 수집 기능 활성화",
                category=SettingCategory.COLLECTION,
                setting_type=SettingType.BOOLEAN,
                default_value=True
            ),
            
            # 인증 정보 설정
            SettingDefinition(
                key="regtech_username",
                name="REGTECH 사용자명",
                description="REGTECH 서비스 로그인 사용자명",
                category=SettingCategory.CREDENTIALS,
                setting_type=SettingType.STRING,
                default_value=os.getenv("REGTECH_USERNAME"),
                required=True
            ),
            SettingDefinition(
                key="regtech_password",
                name="REGTECH 비밀번호",
                description="REGTECH 서비스 로그인 비밀번호",
                category=SettingCategory.CREDENTIALS,
                setting_type=SettingType.PASSWORD,
                default_value=os.getenv("REGTECH_PASSWORD"),
                required=True,
                encrypted=True
            ),
            SettingDefinition(
                key="secudium_username",
                name="SECUDIUM 사용자명",
                description="SECUDIUM 서비스 로그인 사용자명",
                category=SettingCategory.CREDENTIALS,
                setting_type=SettingType.STRING,
                default_value=os.getenv("SECUDIUM_USERNAME"),
                required=True
            ),
            SettingDefinition(
                key="secudium_password",
                name="SECUDIUM 비밀번호",
                description="SECUDIUM 서비스 로그인 비밀번호",
                category=SettingCategory.CREDENTIALS,
                setting_type=SettingType.PASSWORD,
                default_value=os.getenv("SECUDIUM_PASSWORD"),
                required=True,
                encrypted=True
            ),
            
            # 보안 설정
            SettingDefinition(
                key="session_timeout_minutes",
                name="세션 타임아웃 (분)",
                description="사용자 세션이 만료되는 시간 (분 단위)",
                category=SettingCategory.SECURITY,
                setting_type=SettingType.INTEGER,
                default_value=60,
                min_value=5,
                max_value=1440
            ),
            SettingDefinition(
                key="api_rate_limit",
                name="API 요청 제한",
                description="시간당 API 요청 제한 수",
                category=SettingCategory.SECURITY,
                setting_type=SettingType.INTEGER,
                default_value=1000,
                min_value=100,
                max_value=10000
            ),
            
            # 알림 설정
            SettingDefinition(
                key="email_notifications",
                name="이메일 알림",
                description="중요한 이벤트에 대한 이메일 알림 활성화",
                category=SettingCategory.NOTIFICATION,
                setting_type=SettingType.BOOLEAN,
                default_value=False
            ),
            SettingDefinition(
                key="admin_email",
                name="관리자 이메일",
                description="알림을 받을 관리자 이메일 주소",
                category=SettingCategory.NOTIFICATION,
                setting_type=SettingType.EMAIL,
                default_value="admin@example.com"
            ),
            
            # 성능 설정
            SettingDefinition(
                key="cache_ttl_seconds",
                name="캐시 TTL (초)",
                description="기본 캐시 유지 시간 (초 단위)",
                category=SettingCategory.PERFORMANCE,
                setting_type=SettingType.INTEGER,
                default_value=300,
                min_value=30,
                max_value=3600
            ),
            SettingDefinition(
                key="max_concurrent_collections",
                name="최대 동시 수집 수",
                description="동시에 실행할 수 있는 수집 작업 수",
                category=SettingCategory.PERFORMANCE,
                setting_type=SettingType.INTEGER,
                default_value=2,
                min_value=1,
                max_value=5
            )
        ]
        
        # 기본 설정이 없으면 추가
        for setting in default_settings:
            if not self.get_setting(setting.key):
                self.set_setting(
                    setting.key,
                    setting.default_value,
                    setting.setting_type.value,
                    setting.category.value
                )
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """설정값 조회"""
        query = "SELECT value, setting_type FROM app_settings WHERE key = ?"
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, (key,))
                row = cursor.fetchone()
                
                if row is None:
                    return default
                
                value, setting_type = row
                
                # 타입에 따른 변환
                if setting_type == SettingType.BOOLEAN.value:
                    return value.lower() in ('true', '1', 'yes') if isinstance(value, str) else bool(value)
                elif setting_type == SettingType.INTEGER.value:
                    return int(value) if value is not None else default
                elif setting_type == SettingType.JSON.value:
                    return json.loads(value) if value else default
                else:
                    return value
        except Exception:
            return default
    
    def set_setting(self, key: str, value: Any, setting_type: str = None, category: str = None):
        """설정값 저장"""
        # 값 직렬화
        if isinstance(value, bool):
            str_value = str(value).lower()
        elif isinstance(value, (dict, list)):
            str_value = json.dumps(value, ensure_ascii=False)
        else:
            str_value = str(value)
        
        query = """
        INSERT OR REPLACE INTO app_settings (key, value, setting_type, category, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'))
        """
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(query, (key, str_value, setting_type or SettingType.STRING.value, category or SettingCategory.GENERAL.value))
            conn.commit()
    
    def get_settings_by_category(self, category: SettingCategory) -> Dict[str, Any]:
        """카테고리별 설정 조회"""
        query = "SELECT key, value, setting_type FROM app_settings WHERE category = ?"
        
        settings = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, (category.value,))
                rows = cursor.fetchall()
                
                for key, value, setting_type in rows:
                    settings[key] = self._convert_value(value, setting_type)
        except Exception:
            pass
        
        return settings
    
    def get_all_settings(self) -> Dict[str, Dict[str, Any]]:
        """모든 설정을 카테고리별로 그룹화하여 조회"""
        query = "SELECT key, value, setting_type, category FROM app_settings ORDER BY category, key"
        
        settings = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query)
                rows = cursor.fetchall()
                
                for key, value, setting_type, category in rows:
                    if category not in settings:
                        settings[category] = {}
                    settings[category][key] = self._convert_value(value, setting_type)
        except Exception:
            pass
        
        return settings
    
    def _convert_value(self, value: str, setting_type: str) -> Any:
        """문자열 값을 적절한 타입으로 변환"""
        if setting_type == SettingType.BOOLEAN.value:
            return value.lower() in ('true', '1', 'yes') if isinstance(value, str) else bool(value)
        elif setting_type == SettingType.INTEGER.value:
            return int(value) if value is not None else 0
        elif setting_type == SettingType.JSON.value:
            return json.loads(value) if value else {}
        else:
            return value
    
    def delete_setting(self, key: str):
        """설정 삭제"""
        query = "DELETE FROM app_settings WHERE key = ?"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(query, (key,))
            conn.commit()
    
    def reset_to_defaults(self):
        """모든 설정을 기본값으로 리셋"""
        query = "DELETE FROM app_settings"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(query)
            conn.commit()
        
        self._load_default_settings()

# 전역 설정 관리자 인스턴스
_settings_manager = None

def get_settings_manager() -> SettingsManager:
    """설정 관리자 싱글톤 인스턴스 반환"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager