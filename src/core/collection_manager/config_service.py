#!/usr/bin/env python3
"""
Collection Configuration Service
수집 설정 관리 서비스
"""

import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CollectionConfigService:
    """수집 설정 관리 서비스"""

    def __init__(self, db_path: str, config_path: str):
        self.db_path = db_path
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(exist_ok=True)

    def load_collection_config(self) -> Dict[str, Any]:
        """수집 설정 로드 (파일 우선, DB 폴백)"""
        try:
            # 1. 파일에서 로드 시도
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    logger.debug("Config loaded from file: {self.config_path}")
                    return config
        except Exception as e:
            logger.warning("Error loading config from file: {e}")

        # 2. DB에서 로드 시도
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT config_data FROM collection_config ORDER BY created_at DESC LIMIT 1"
                )
                row = cursor.fetchone()
                if row:
                    config = json.loads(row[0])
                    logger.debug("Config loaded from database")
                    return config
        except Exception as e:
            logger.warning("Error loading config from database: {e}")

        # 3. 기본 설정 반환
        logger.info("Using default collection config")
        return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """기본 수집 설정 반환"""
        return {
            "enabled": False,  # 기본적으로 비활성화
            "sources": {
                "regtech": {"enabled": False, "last_collection": None},
                "secudium": {"enabled": False, "last_collection": None},
            },
            "safety_settings": {
                "max_auth_attempts": 10,
                "restart_protection": True,
                "auth_timeout_minutes": 30,
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

    def save_collection_config(self, config: Dict[str, Any]):
        """수집 설정 저장 (파일과 DB 모두)"""
        config["updated_at"] = datetime.now().isoformat()

        # 파일 저장
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logger.debug("Config saved to file: {self.config_path}")
        except Exception as e:
            logger.error("Error saving config to file: {e}")

        # DB 저장
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                cursor = conn.cursor()

                # 테이블 생성
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS collection_config (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        config_data TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                # 설정 저장
                cursor.execute(
                    "INSERT INTO collection_config (config_data) VALUES (?)",
                    (json.dumps(config, ensure_ascii=False),),
                )

                conn.commit()
                logger.debug("Config saved to database")
        except Exception as e:
            logger.error("Error saving config to database: {e}")

    def create_initial_config_with_protection(self) -> Dict[str, Any]:
        """보호 기능이 적용된 초기 설정 생성"""
        config = self._get_default_config()

        # 🔴 환경변수 강제 차단 적용
        force_disable = os.getenv("FORCE_DISABLE_COLLECTION", "true").lower() in (
            "true",
            "1",
            "yes",
            "on",
        )

        if force_disable:
            config["enabled"] = False
            config["force_disabled"] = True
            config["force_disable_reason"] = "환경변수 FORCE_DISABLE_COLLECTION=true"
            logger.warning("Collection force disabled by environment variable")

        self.save_collection_config(config)
        return config

    def load_collection_enabled_from_db(self) -> Optional[bool]:
        """DB에서 수집 활성화 상태 로드"""
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                cursor = conn.cursor()

                # collection_status 테이블에서 조회
                cursor.execute(
                    "SELECT enabled FROM collection_status ORDER BY updated_at DESC LIMIT 1"
                )
                row = cursor.fetchone()

                if row is not None:
                    return bool(row[0])

        except sqlite3.Error as e:
            logger.warning("Database error loading collection status: {e}")
        except Exception as e:
            logger.error("Unexpected error loading collection status: {e}")

        return None

    def save_collection_enabled_to_db(self, enabled: bool):
        """수집 활성화 상태를 DB에 저장"""
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                cursor = conn.cursor()

                # 테이블 생성
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS collection_status (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        enabled BOOLEAN NOT NULL,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                # 상태 저장
                cursor.execute(
                    "INSERT INTO collection_status (enabled) VALUES (?)", (enabled,)
                )

                conn.commit()
                logger.debug("Collection status saved to DB: {enabled}")

        except Exception as e:
            logger.error("Error saving collection status to DB: {e}")

    def update_source_config(
        self, source: str, config_updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """특정 소스의 설정 업데이트"""
        config = self.load_collection_config()

        if "sources" not in config:
            config["sources"] = {}

        if source not in config["sources"]:
            config["sources"][source] = {"enabled": False, "last_collection": None}

        # 설정 업데이트
        config["sources"][source].update(config_updates)

        # 저장
        self.save_collection_config(config)

        return config["sources"][source]

    def get_source_config(self, source: str) -> Dict[str, Any]:
        """특정 소스의 설정 조회"""
        config = self.load_collection_config()
        return config.get("sources", {}).get(
            source, {"enabled": False, "last_collection": None}
        )

    def is_source_enabled(self, source: str) -> bool:
        """특정 소스의 활성화 상태 확인"""
        source_config = self.get_source_config(source)
        return source_config.get("enabled", False)

    def get_safety_settings(self) -> Dict[str, Any]:
        """안전 설정 조회"""
        config = self.load_collection_config()
        return config.get(
            "safety_settings",
            {
                "max_auth_attempts": 10,
                "restart_protection": True,
                "auth_timeout_minutes": 30,
            },
        )

    def update_safety_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """안전 설정 업데이트"""
        config = self.load_collection_config()

        if "safety_settings" not in config:
            config["safety_settings"] = self.get_safety_settings()

        config["safety_settings"].update(updates)
        self.save_collection_config(config)

        return config["safety_settings"]
