#!/usr/bin/env python3
"""
Collection Protection Service
수집 보호 서비스 - 재시작 감지 및 보호 기능
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ProtectionService:
    """수집 보호 서비스 - 재시작 감지 및 비상 상황 처리"""

    def __init__(self, db_path: str, config_path: str):
        self.db_path = db_path
        self.config_path = Path(config_path)
        self.restart_data_path = self.config_path.parent / "restart_data.json"

        # 환경변수 설정
        self.restart_protection_enabled = os.getenv(
            "RESTART_PROTECTION", "true"
        ).lower() in ("true", "1", "yes", "on")
        self.force_disable_collection = os.getenv(
            "FORCE_DISABLE_COLLECTION", "true"
        ).lower() in ("true", "1", "yes", "on")

        logger.info(
            "Protection Service initialized - restart_protection: "
            "{self.restart_protection_enabled}, "
            "force_disable: {self.force_disable_collection}"
        )

    def is_collection_safe_to_enable(self) -> Tuple[bool, str]:
        """수집 활성화 안전성 검사"""
        # 1. 환경변수 강제 차단 검사
        if self.force_disable_collection:
            return False, "환경변수 FORCE_DISABLE_COLLECTION=true로 인한 강제 차단"

        # 2. 재시작 보호 검사
        if self.restart_protection_enabled:
            rapid_restart_detected = self.detect_rapid_restart()
            if rapid_restart_detected:
                return False, "급속 재시작 감지 - 자동 차단으로 서버 보호"

        # 3. 인증 시도 횟수 검사
        recent_failures = self._count_recent_auth_failures()
        if recent_failures >= 10:  # 기본 리밋
            return False, "최근 인증 실패 {recent_failures}회 초과 - 임시 차단"

        return True, "수집 활성화 안전"

    def detect_rapid_restart(self) -> bool:
        """급속 재시작 감지"""
        if not self.restart_protection_enabled:
            return False

        try:
            restart_data = self._load_restart_data()
            current_time = datetime.now()

            # 최근 10분 내 재시작 횟수 확인
            recent_restarts = [
                datetime.fromisoformat(timestamp)
                for timestamp in restart_data.get("restart_timestamps", [])
                if (current_time - datetime.fromisoformat(timestamp)).total_seconds()
                < 600
            ]

            if len(recent_restarts) >= 3:  # 10분 내 3회 이상 재시작
                logger.warning(
                    "Rapid restart detected: {len(recent_restarts)} restarts in 10 minutes"
                )
                self._record_restart_protection_event()
                return True

            # 현재 재시작 기록
            self._update_restart_data(len(recent_restarts) + 1)

        except Exception as e:
            logger.error(f"Error detecting rapid restart: {e}")
            # 오류 시 보수적으로 차단
            return True

        return False

    def _load_restart_data(self) -> Dict:
        """재시작 데이터 로드"""
        try:
            if self.restart_data_path.exists():
                with open(self.restart_data_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading restart data: {e}")

        return {"restart_count": 0, "restart_timestamps": [], "last_restart": None}

    def _update_restart_data(self, count: int):
        """재시작 데이터 업데이트"""
        try:
            restart_data = self._load_restart_data()
            current_time = datetime.now().isoformat()

            restart_data["restart_count"] = count
            restart_data["last_restart"] = current_time

            # 재시작 타임스탬프 추가
            restart_data["restart_timestamps"].append(current_time)

            # 오래된 타임스탬프 제거 (24시간 이상)
            cutoff_time = datetime.now() - timedelta(hours=24)
            restart_data["restart_timestamps"] = [
                ts
                for ts in restart_data["restart_timestamps"]
                if datetime.fromisoformat(ts) > cutoff_time
            ]

            with open(self.restart_data_path, "w", encoding="utf-8") as f:
                json.dump(restart_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Error updating restart data: {e}")

    def _record_restart_protection_event(self):
        """재시작 보호 이벤트 기록"""
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS protection_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT NOT NULL,
                        description TEXT,
                        data TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                cursor.execute(
                    """
                    INSERT INTO protection_events (event_type, description, data)
                    VALUES (?, ?, ?)
                    """,
                    (
                        "rapid_restart_protection",
                        "급속 재시작 감지로 인한 자동 보호 작동",
                        json.dumps(self._load_restart_data(), ensure_ascii=False),
                    ),
                )

                conn.commit()
                logger.info("Restart protection event recorded")

        except Exception as e:
            logger.error(f"Error recording protection event: {e}")

    def _count_recent_auth_failures(self, hours: int = 1) -> int:
        """최근 인증 실패 횟수 조회"""
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                cursor = conn.cursor()

                cutoff_time = datetime.now() - timedelta(hours=hours)

                cursor.execute(
                    """
                    SELECT COUNT(*) FROM auth_attempts
                    WHERE success = 0
                      AND created_at > ?
                    """,
                    (cutoff_time.isoformat(),),
                )

                row = cursor.fetchone()
                return row[0] if row else 0

        except Exception as e:
            logger.error(f"Error counting recent auth failures: {e}")
            return 0

    def reset_protection_state(self) -> Dict[str, bool]:
        """보호 상태 리셋 - 사용자 수동 리셋용"""
        result = {"restart_data_cleared": False, "auth_history_cleared": False}

        try:
            # 1. 재시작 데이터 삭제
            if self.restart_data_path.exists():
                self.restart_data_path.unlink()
                result["restart_data_cleared"] = True
                logger.info("Restart data cleared")

            # 2. 인증 실패 이력 삭제
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM auth_attempts WHERE success = 0")
                conn.commit()
                result["auth_history_cleared"] = True
                logger.info("Auth failure history cleared")

        except Exception as e:
            logger.error(f"Error resetting protection state: {e}")

        return result

    def get_protection_status(self) -> Dict:
        """보호 상태 조회"""
        restart_data = self._load_restart_data()
        recent_failures = self._count_recent_auth_failures()
        safe, reason = self.is_collection_safe_to_enable()

        return {
            "protection_enabled": self.restart_protection_enabled,
            "force_disable_active": self.force_disable_collection,
            "safe_to_enable": safe,
            "safety_reason": reason,
            "restart_data": restart_data,
            "recent_auth_failures": recent_failures,
            "last_check": datetime.now().isoformat(),
        }

    def create_protection_bypass(self, reason: str, duration_minutes: int = 60) -> Dict:
        """보호 바이패스 생성 (임시적 보호 해제)"""
        try:
            bypass_data = {
                "created_at": datetime.now().isoformat(),
                "expires_at": (
                    datetime.now() + timedelta(minutes=duration_minutes)
                ).isoformat(),
                "reason": reason,
                "active": True,
            }

            bypass_path = self.config_path.parent / "protection_bypass.json"
            with open(bypass_path, "w", encoding="utf-8") as f:
                json.dump(bypass_data, f, ensure_ascii=False, indent=2)

            logger.warning(
                "Protection bypass created: {reason} (expires in {duration_minutes} minutes)"
            )
            return {"success": True, "bypass_data": bypass_data}

        except Exception as e:
            logger.error(f"Error creating protection bypass: {e}")
            return {"success": False, "error": str(e)}

    def check_protection_bypass(self) -> Optional[Dict]:
        """보호 바이패스 확인"""
        try:
            bypass_path = self.config_path.parent / "protection_bypass.json"
            if not bypass_path.exists():
                return None

            with open(bypass_path, "r", encoding="utf-8") as f:
                bypass_data = json.load(f)

            expires_at = datetime.fromisoformat(bypass_data["expires_at"])

            if datetime.now() > expires_at:
                # 만료된 바이패스 제거
                bypass_path.unlink()
                return None

            return bypass_data

        except Exception as e:
            logger.error(f"Error checking protection bypass: {e}")
            return None
