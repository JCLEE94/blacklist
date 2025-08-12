#!/usr/bin/env python3
"""
애플리케이션 설정 모델
데이터베이스에 저장되는 동적 설정 관리
"""
import json
import sqlite3
from typing import Any
from typing import Dict

from .setting_types import SettingCategory
from .setting_types import SettingType


class SettingsManager:
    """설정 관리자 클래스"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            from src.config.settings import settings

            db_uri = settings.database_uri
            if db_uri.startswith("sqlite:///"):
                self.db_path = db_uri[10:]
            elif db_uri.startswith("sqlite://"):
                self.db_path = db_uri[9:]
            else:
                self.db_path = str(settings.instance_dir / "blacklist.db")
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
        from .default_settings import get_default_settings

        default_settings = get_default_settings()

        # 기본 설정이 없으면 추가
        for setting in default_settings:
            if not self.get_setting(setting.key):
                self.set_setting(
                    setting.key,
                    setting.default_value,
                    setting.setting_type.value,
                    setting.category.value,
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
                    return (
                        value.lower() in ("true", "1", "yes")
                        if isinstance(value, str)
                        else bool(value)
                    )
                elif setting_type == SettingType.INTEGER.value:
                    return int(value) if value is not None else default
                elif setting_type == SettingType.JSON.value:
                    return json.loads(value) if value else default
                else:
                    return value
        except Exception:
            return default

    def set_setting(
        self, key: str, value: Any, setting_type: str = None, category: str = None
    ):
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
            conn.execute(
                query,
                (
                    key,
                    str_value,
                    setting_type or SettingType.STRING.value,
                    category or SettingCategory.GENERAL.value,
                ),
            )
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
            return (
                value.lower() in ("true", "1", "yes")
                if isinstance(value, str)
                else bool(value)
            )
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
