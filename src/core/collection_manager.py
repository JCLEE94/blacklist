"""
통합 수집 관리자 (Unified Collection Manager)
REGTECH, SECUDIUM 등 다양한 소스의 데이터 수집을 통합 관리
수집 ON/OFF 기능 및 데이터 클리어 기능 포함
"""

import json
import logging
import os
import shutil
import sqlite3
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CollectionManager:
    """통합 수집 관리자 - 수집 ON/OFF 및 데이터 관리"""

    def __init__(
        self,
        db_path: str = "instance/blacklist.db",
        config_path: str = "instance/collection_config.json",
    ):
        """
        초기화 - 방어적 자동 인증 차단 시스템

        Args:
            db_path: 데이터베이스 경로
            config_path: 수집 설정 파일 경로
        """
        self.db_path = db_path
        self.config_path = Path(config_path)

        # 설정 디렉토리 생성
        self.config_path.parent.mkdir(exist_ok=True)

        # 🔴 방어적 차단 시스템 - 환경변수로 강제 차단 가능
        force_disable_collection = os.getenv(
            "FORCE_DISABLE_COLLECTION", "true"
        ).lower() in ("true", "1", "yes", "on")

        # 🔴 재시작 감지 및 자동 차단 메커니즘
        self._restart_protection_enabled = os.getenv(
            "RESTART_PROTECTION", "true"
        ).lower() in ("true", "1", "yes", "on")

        if force_disable_collection:
            logger.warning("🚫 FORCE_DISABLE_COLLECTION=true 설정으로 모든 수집 기능 강제 차단")
            self.collection_enabled = False
            self._save_collection_enabled_to_db(False)
            self._create_initial_config_with_protection()
            return

        # 수집 설정 로드
        self.config = self._load_collection_config()

        # 환경변수를 최우선으로 확인
        env_collection_enabled = os.getenv("COLLECTION_ENABLED")
        if env_collection_enabled is not None:
            # 환경변수가 설정되어 있으면 이를 사용
            self.collection_enabled = env_collection_enabled.lower() in (
                "true",
                "1",
                "yes",
                "on",
            )
            self.config["collection_enabled"] = self.collection_enabled
            logger.info(f"환경변수 COLLECTION_ENABLED 적용: {self.collection_enabled}")
            # DB에도 저장
            self._save_collection_enabled_to_db(self.collection_enabled)
        else:
            # 환경변수가 없으면 DB에서 설정 로드를 우선시
            db_collection_enabled = self._load_collection_enabled_from_db()
            if db_collection_enabled is not None:  # DB에 값이 있으면
                self.collection_enabled = db_collection_enabled
                self.config["collection_enabled"] = db_collection_enabled
                logger.info(
                    f"DB 설정 우선 적용: collection_enabled = {db_collection_enabled}"
                )
            else:  # DB에 값이 없으면 config 파일 값 사용 (기본값: False)
                self.collection_enabled = self.config.get("collection_enabled", False)
                # DB에 현재 값 저장
                self._save_collection_enabled_to_db(self.collection_enabled)

        # 🔴 재시작 보호 로직 - 무한 재시작 방지
        if self._restart_protection_enabled and self._detect_rapid_restart():
            logger.error("🚨 빠른 재시작 감지 - 자동 수집 기능 차단으로 서버 보호")
            self.collection_enabled = False
            self.config["collection_enabled"] = False
            self._save_collection_enabled_to_db(False)
            self._record_restart_protection_event()

        self._save_collection_config()

        # 최종 상태 로깅
        if self.collection_enabled:
            logger.warning("⚠️  수집 기능 활성화됨 - 외부 인증 시도가 발생할 수 있습니다")
        else:
            logger.info("✅ 수집 기능 차단됨 - 외부 인증 시도 없음 (안전 모드)")

        # 일일 자동 수집 설정 (기본값: False)
        self.daily_collection_enabled = self.config.get(
            "daily_collection_enabled", False
        )
        self.last_daily_collection = self.config.get("last_daily_collection", None)

        # 🔴 소스별 기본 차단 설정 (수동 활성화 필요)
        self.sources = {
            "regtech": {
                "name": "REGTECH (금융보안원)",
                "status": "blocked",  # 기본적으로 차단
                "last_collection": None,
                "total_ips": 0,
                "manual_only": True,
                "enabled": self.config.get("sources", {}).get(
                    "regtech", False
                ),  # 기본값 False (비활성화)
                "auth_attempts": 0,  # 인증 시도 횟수 추적
                "last_auth_attempt": None,
                "blocked_until": None,  # 차단 해제 시간
            },
            "secudium": {
                "name": "SECUDIUM (에스케이인포섹)",
                "status": "blocked",  # 기본적으로 차단
                "last_collection": None,
                "total_ips": 0,
                "manual_only": True,
                "enabled": False,  # Secudium 수집기 비활성화
                "auth_attempts": 0,  # 인증 시도 횟수 추적
                "last_auth_attempt": None,
                "blocked_until": None,  # 차단 해제 시간
            },
        }

    def _load_collection_config(self) -> Dict[str, Any]:
        """
        수집 설정 로드 - 방어적 기본값 적용

        🔴 보안 기본값:
        - collection_enabled: False (기본 차단)
        - 모든 소스 기본 False (비활성화)
        - 재시작 보호 기본 활성화
        """
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)

                    # 🔴 기존 설정도 강제로 보안 모드 적용
                    logger.info("🛡️  기존 설정 파일 발견 - 보안 검사 적용")

                    # 최초 실행이거나 보안 설정이 없는 경우 강제 차단
                    if not config.get(
                        "initial_collection_done", False
                    ) or not config.get("security_initialized", False):
                        logger.warning("🚫 보안 초기화 - 모든 수집 기능 기본 차단")
                        config["collection_enabled"] = False  # 강제 OFF
                        config["sources"] = {
                            "regtech": False,
                            "secudium": False,
                        }  # 모두 OFF
                        config["initial_collection_needed"] = False
                        config["security_initialized"] = True
                        config["force_disabled"] = True
                        config["security_mode"] = "DEFENSIVE"

                    # 🔴 재시작 보호 설정 확인/초기화
                    if "restart_protection" not in config:
                        config["restart_protection"] = {
                            "enabled": True,
                            "last_restart": datetime.now().isoformat(),
                            "restart_count": 0,
                            "protection_active": False,
                        }

                    return config
            else:
                # 🔴 설정 파일이 없으면 완전 방어적 초기 설정
                logger.warning("🛡️  최초 실행 - 완전 방어적 보안 모드로 초기화")
                return {
                    "collection_enabled": False,  # 기본값 완전 OFF
                    "sources": {"regtech": False, "secudium": False},  # 모두 OFF
                    "last_enabled_at": None,  # 활성화 기록 없음
                    "last_disabled_at": datetime.now().isoformat(),
                    "daily_collection_enabled": False,
                    "last_daily_collection": None,
                    "initial_collection_done": True,  # 초기 수집 완료로 표시 (자동 실행 방지)
                    "initial_collection_needed": False,  # 초기 수집 불필요
                    "security_initialized": True,  # 보안 초기화 완료
                    "force_disabled": True,  # 강제 차단 모드
                    "security_mode": "DEFENSIVE",  # 방어적 모드
                    "restart_protection": {
                        "enabled": True,
                        "last_restart": datetime.now().isoformat(),
                        "restart_count": 0,
                        "protection_active": False,
                    },
                    "created_at": datetime.now().isoformat(),
                    "security_notes": [
                        "모든 외부 인증 시도 기본 차단",
                        "수동 활성화만 허용",
                        "재시작 보호 기능 활성화",
                        "REGTECH/SECUDIUM 자동 수집 차단",
                    ],
                }
        except Exception as e:
            logger.error(f"설정 로드 실패: {e}")
            # 🔴 오류 시에도 완전 방어적 설정 반환
            logger.warning("🚨 설정 로드 오류 - 긴급 방어 모드 활성화")
            return {
                "collection_enabled": False,  # 오류 시에도 완전 OFF
                "sources": {"regtech": False, "secudium": False},  # 모두 OFF
                "last_enabled_at": None,
                "last_disabled_at": datetime.now().isoformat(),
                "daily_collection_enabled": False,
                "last_daily_collection": None,
                "initial_collection_done": True,
                "initial_collection_needed": False,
                "security_initialized": True,
                "force_disabled": True,
                "security_mode": "EMERGENCY_DEFENSIVE",  # 긴급 방어 모드
                "error_protection": True,
                "restart_protection": {
                    "enabled": True,
                    "last_restart": datetime.now().isoformat(),
                    "restart_count": 0,
                    "protection_active": True,  # 오류 시 보호 활성화
                },
                "error_details": str(e),
                "recovery_mode": True,
            }

    def _load_collection_enabled_from_db(self) -> Optional[bool]:
        """DB에서 collection_enabled 설정 로드"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # app_settings 테이블 확인
            cursor.execute(
                """
                SELECT value FROM app_settings
                WHERE key = 'collection_enabled'
            """
            )
            result = cursor.fetchone()

            if result:
                # DB에 설정이 있으면 사용
                value = result[0]
                if isinstance(value, str):
                    enabled = value.lower() in ("true", "1", "yes", "on")
                else:
                    enabled = bool(value)
                logger.info(f"DB에서 collection_enabled 로드: {enabled}")
                return enabled
            else:
                # DB에 설정이 없으면 None 반환
                logger.info("DB에 collection_enabled 설정 없음")
                return None

        except Exception as e:
            logger.error(f"DB에서 설정 로드 실패: {e}")
            return None  # 오류 시 None 반환
        finally:
            if "conn" in locals():
                conn.close()

    def _save_collection_enabled_to_db(self, enabled: bool):
        """DB에 collection_enabled 설정 저장 (Settings Manager 사용)"""
        try:
            # 임시로 비활성화 - settings manager 순환 참조 문제 해결 후 재활성화
            logger.info(f"Collection 상태 변경: {enabled} (DB 저장은 임시 비활성화)")
            pass

        except Exception as e:
            logger.error(f"DB에 설정 저장 실패: {e}")

    def _save_collection_config(self):
        """수집 설정 저장"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            logger.info(f"설정 저장됨: {self.config_path}")
        except Exception as e:
            logger.error(f"설정 저장 실패: {e}")

    def _create_initial_config_with_protection(self):
        """강제 차단 모드용 초기 설정 생성"""
        config = {
            "collection_enabled": False,
            "sources": {"regtech": False, "secudium": False},
            "last_enabled_at": None,
            "last_disabled_at": datetime.now().isoformat(),
            "daily_collection_enabled": False,
            "last_daily_collection": None,
            "initial_collection_done": True,  # 초기 수집 완료로 표시
            "initial_collection_needed": False,
            "force_disabled": True,  # 강제 차단 플래그
            "protection_mode": "FORCE_DISABLE",
            "restart_protection": {
                "enabled": True,
                "last_restart": datetime.now().isoformat(),
                "restart_count": 0,
                "protection_active": False,
            },
        }

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.config = config
            logger.info("🛡️  강제 차단 모드 설정 생성 완료")
        except Exception as e:
            logger.error(f"강제 차단 설정 생성 실패: {e}")

    def _detect_rapid_restart(self) -> bool:
        """빠른 재시작 감지 (무한 재시작 방지)"""
        try:
            restart_data = self.config.get("restart_protection", {})
            last_restart_str = restart_data.get("last_restart")
            restart_count = restart_data.get("restart_count", 0)

            if not last_restart_str:
                # 첫 번째 시작
                self._update_restart_data(1)
                return False

            last_restart = datetime.fromisoformat(
                last_restart_str.replace("Z", "+00:00")
            )
            current_time = datetime.now()
            time_diff = (current_time - last_restart).total_seconds()

            # 1분 이내에 재시작된 경우
            if time_diff < 60:
                new_count = restart_count + 1
                self._update_restart_data(new_count)

                # 5회 이상 빠른 재시작 시 차단
                if new_count >= 5:
                    logger.error(f"🚨 {new_count}회 연속 빠른 재시작 감지 (지난 {time_diff:.1f}초)")
                    return True
                else:
                    logger.warning(
                        f"⚠️  빠른 재시작 감지 ({new_count}/5회, 지난 {time_diff:.1f}초)"
                    )
                    return False
            else:
                # 1분 이상 경과 시 카운터 리셋
                self._update_restart_data(1)
                return False

        except Exception as e:
            logger.error(f"재시작 감지 오류: {e}")
            return False

    def _update_restart_data(self, count: int):
        """재시작 데이터 업데이트"""
        if "restart_protection" not in self.config:
            self.config["restart_protection"] = {}

        self.config["restart_protection"].update(
            {
                "last_restart": datetime.now().isoformat(),
                "restart_count": count,
                "enabled": self._restart_protection_enabled,
            }
        )

    def _record_restart_protection_event(self):
        """재시작 보호 이벤트 기록"""
        protection_data = {
            "protection_active": True,
            "protected_at": datetime.now().isoformat(),
            "reason": "rapid_restart_detection",
            "auto_disabled": True,
        }

        if "restart_protection" not in self.config:
            self.config["restart_protection"] = {}

        self.config["restart_protection"].update(protection_data)
        logger.info("🛡️  재시작 보호 모드 활성화 - 수집 기능 자동 차단")

    def _check_auth_attempt_limit(self, source: str) -> bool:
        """인증 시도 횟수 제한 확인"""
        if source not in self.sources:
            return False

        source_info = self.sources[source]
        auth_attempts = source_info.get("auth_attempts", 0)
        last_attempt = source_info.get("last_auth_attempt")
        blocked_until = source_info.get("blocked_until")

        # 차단 시간이 설정되어 있고 아직 해제되지 않은 경우
        if blocked_until:
            try:
                blocked_until_dt = datetime.fromisoformat(blocked_until)
                if datetime.now() < blocked_until_dt:
                    remaining = (blocked_until_dt - datetime.now()).total_seconds()
                    logger.warning(f"🚫 {source} 소스 차단 중 (해제까지 {remaining:.0f}초)")
                    return False
                else:
                    # 차단 해제
                    source_info["blocked_until"] = None
                    source_info["auth_attempts"] = 0
                    logger.info(f"✅ {source} 소스 차단 해제")
            except Exception as e:
                logger.error(f"차단 시간 확인 오류: {e}")

        # 인증 시도 횟수 확인 (24시간 내 10회 제한)
        if last_attempt:
            try:
                last_attempt_dt = datetime.fromisoformat(last_attempt)
                hours_passed = (datetime.now() - last_attempt_dt).total_seconds() / 3600

                if hours_passed < 24 and auth_attempts >= 10:
                    # 24시간 차단
                    blocked_until = (datetime.now() + timedelta(hours=24)).isoformat()
                    source_info["blocked_until"] = blocked_until
                    logger.error(f"🚨 {source} 소스 24시간 차단 - 인증 시도 {auth_attempts}회 초과")
                    return False
                elif hours_passed >= 24:
                    # 24시간 경과 시 카운터 리셋
                    source_info["auth_attempts"] = 0
            except Exception as e:
                logger.error(f"인증 시도 시간 확인 오류: {e}")

        return True

    def record_auth_attempt(self, source: str, success: bool = False):
        """인증 시도 기록"""
        if source not in self.sources:
            return

        source_info = self.sources[source]
        current_time = datetime.now().isoformat()

        if not success:
            source_info["auth_attempts"] = source_info.get("auth_attempts", 0) + 1
            logger.warning(f"⚠️  {source} 인증 실패 기록 ({source_info['auth_attempts']}회)")
        else:
            source_info["auth_attempts"] = 0  # 성공 시 카운터 리셋
            logger.info(f"✅ {source} 인증 성공 - 카운터 리셋")

        source_info["last_auth_attempt"] = current_time
        self._save_collection_config()

    def is_collection_safe_to_enable(self) -> tuple[bool, str]:
        """수집 활성화가 안전한지 확인"""
        # 강제 차단 모드 확인
        if os.getenv("FORCE_DISABLE_COLLECTION", "true").lower() in (
            "true",
            "1",
            "yes",
            "on",
        ):
            return False, "환경변수 FORCE_DISABLE_COLLECTION=true로 인한 강제 차단"

        # 재시작 보호 활성화 확인
        protection_data = self.config.get("restart_protection", {})
        if protection_data.get("protection_active", False):
            return False, "빠른 재시작 감지로 인한 보호 모드 활성화"

        # 소스별 차단 상태 확인
        blocked_sources = []
        for source_name, source_info in self.sources.items():
            if source_info.get("blocked_until"):
                try:
                    blocked_until_dt = datetime.fromisoformat(
                        source_info["blocked_until"]
                    )
                    if datetime.now() < blocked_until_dt:
                        remaining = (blocked_until_dt - datetime.now()).total_seconds()
                        blocked_sources.append(f"{source_name} ({remaining:.0f}초 남음)")
                except Exception:
                    pass

        if blocked_sources:
            return False, f"차단된 소스: {', '.join(blocked_sources)}"

        return True, "수집 활성화 가능"

    def enable_collection(
        self, sources: Optional[Dict[str, bool]] = None, clear_data: bool = False
    ) -> Dict[str, Any]:
        """
        수집 활성화 - 보안 검사 후 선택적으로 기존 데이터 클리어

        🔴 방어적 보안 검사:
        - 강제 차단 모드 확인
        - 재시작 보호 모드 확인
        - 인증 시도 제한 확인
        - 수동 활성화만 허용
        """
        try:
            # 🔴 보안 검사 1: 수집 활성화 안전성 확인
            is_safe, safety_reason = self.is_collection_safe_to_enable()
            if not is_safe:
                logger.warning(f"🚫 수집 활성화 거부: {safety_reason}")
                return {
                    "success": False,
                    "message": f"수집 활성화 불가: {safety_reason}",
                    "security_blocked": True,
                    "reason": safety_reason,
                }

            # 🔴 보안 검사 2: 강제 차단 환경변수 재확인
            if os.getenv("FORCE_DISABLE_COLLECTION", "true").lower() in (
                "true",
                "1",
                "yes",
                "on",
            ):
                logger.error("🚨 FORCE_DISABLE_COLLECTION=true로 인한 수집 활성화 차단")
                return {
                    "success": False,
                    "message": "환경변수 FORCE_DISABLE_COLLECTION=true로 인해 수집을 활성화할 수 없습니다",
                    "security_blocked": True,
                    "force_disabled": True,
                }

            # 🔴 보안 검사 3: 소스별 인증 시도 제한 확인
            for source_name in ["regtech", "secudium"]:
                if not self._check_auth_attempt_limit(source_name):
                    logger.warning(f"🚫 {source_name} 소스 인증 시도 제한 초과")
                    return {
                        "success": False,
                        "message": f"{source_name} 소스가 인증 시도 제한으로 차단된 상태입니다",
                        "security_blocked": True,
                        "blocked_source": source_name,
                    }

            # 이미 활성화되어 있는지 확인
            was_already_enabled = self.config.get("collection_enabled", False)
            cleared_data = False
            clear_result = {"cleared_items": []}

            # 명시적으로 요청된 경우에만 데이터 클리어
            if clear_data:
                clear_result = self.clear_all_data()
                if not clear_result.get("success", False):
                    return {
                        "success": False,
                        "message": f'데이터 클리어 실패: {clear_result.get("message")}',
                    }
                cleared_data = True

            # 수집 활성화
            self.config["collection_enabled"] = True
            self.collection_enabled = True  # 인스턴스 속성도 업데이트
            self.config["last_enabled_at"] = datetime.now().isoformat()

            # 🔴 보안 이벤트 로깅
            logger.warning("⚠️  수집 기능 수동 활성화됨 - 외부 인증 시도 가능")
            logger.info(f"📋 활성화 요청자: 수동 관리자 요청")

            # DB에 설정 저장
            self._save_collection_enabled_to_db(True)

            if sources:
                self.config["sources"].update(sources)
            else:
                # 기본적으로 모든 소스 활성화 (보안 경고와 함께)
                for source in self.config["sources"]:
                    self.config["sources"][source] = True
                    logger.warning(f"⚠️  {source} 소스 활성화 - 외부 서버 인증 시도 발생")

            # 소스 상태 업데이트
            for source_key in self.sources:
                enabled = self.config["sources"].get(source_key, False)
                self.sources[source_key]["enabled"] = enabled

                if enabled:
                    self.sources[source_key]["status"] = "enabled"
                    logger.warning(f"🔓 {source_key} 소스 잠금 해제 - 인증 준비")
                else:
                    self.sources[source_key]["status"] = "disabled"

            # 재시작 보호 해제 (수동 활성화 시)
            if "restart_protection" in self.config:
                self.config["restart_protection"]["protection_active"] = False
                logger.info("🛡️  수동 활성화로 인한 재시작 보호 해제")

            self._save_collection_config()

            message = "🔓 수집이 활성화되었습니다."
            if cleared_data:
                message += " 기존 데이터가 클리어되었습니다."
            elif was_already_enabled:
                message = "ℹ️  수집은 이미 활성화 상태입니다."

            # 🔴 최종 보안 경고
            active_sources = [k for k, v in self.config["sources"].items() if v]
            if active_sources:
                logger.warning(f"🚨 활성화된 소스: {', '.join(active_sources)} - 외부 인증 시도 시작됨")

            return {
                "success": True,
                "message": message,
                "collection_enabled": True,
                "cleared_data": cleared_data,
                "sources": self.config["sources"],
                "enabled_at": self.config["last_enabled_at"],
                "cleared_items": (
                    clear_result.get("cleared_items", []) if cleared_data else []
                ),
                "security_warnings": [
                    "외부 서버 인증 시도가 활성화되었습니다",
                    "REGTECH 및 SECUDIUM 서버에 로그인 시도가 발생할 수 있습니다",
                    "수집 중단을 원하면 즉시 disable_collection을 호출하세요",
                ],
                "active_sources": active_sources,
            }

        except Exception as e:
            logger.error(f"수집 활성화 실패: {e}")
            return {"success": False, "message": f"수집 활성화 실패: {str(e)}"}

    def disable_collection(self) -> Dict[str, Any]:
        """수집 비활성화"""
        try:
            self.config["collection_enabled"] = False
            self.collection_enabled = False  # 인스턴스 속성도 업데이트
            self.config["last_disabled_at"] = datetime.now().isoformat()

            # 모든 소스 비활성화
            for source in self.config["sources"]:
                self.config["sources"][source] = False

            # 소스 상태 업데이트
            for source_key in self.sources:
                self.sources[source_key]["enabled"] = False

            self._save_collection_config()

            # DB에 설정 저장
            self._save_collection_enabled_to_db(False)

            logger.info("수집이 비활성화되었습니다.")

            return {
                "success": True,
                "message": "수집이 비활성화되었습니다.",
                "collection_enabled": False,
                "disabled_at": self.config["last_disabled_at"],
            }

        except Exception as e:
            logger.error(f"수집 비활성화 실패: {e}")
            return {"success": False, "message": f"수집 비활성화 실패: {str(e)}"}

    def clear_all_data(self) -> Dict[str, Any]:
        """모든 데이터 클리어"""
        try:
            cleared_items = []

            # 1. 데이터베이스 클리어
            if Path(self.db_path).exists():
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # 테이블별 데이터 삭제
                tables = ["blacklist_ip", "ip_detection", "daily_stats"]
                for table in tables:
                    try:
                        cursor.execute(f"DELETE FROM {table}")
                        row_count = cursor.rowcount
                        cleared_items.append(f"테이블 {table}: {row_count}개 레코드 삭제")
                    except sqlite3.Error as e:
                        logger.warning(f"테이블 {table} 삭제 중 오류: {e}")

                conn.commit()
                conn.close()
                logger.info("데이터베이스 클리어 완료")

            # 2. 데이터 디렉토리 클리어
            data_dirs = [
                "data/blacklist",
                "data/sources",
                "data/regtech",
                "data/secudium",
            ]

            for data_dir in data_dirs:
                dir_path = Path(data_dir)
                if dir_path.exists():
                    try:
                        shutil.rmtree(dir_path)
                        dir_path.mkdir(parents=True, exist_ok=True)
                        cleared_items.append(f"디렉토리 {data_dir} 클리어")
                    except Exception as e:
                        logger.warning(f"디렉토리 {data_dir} 클리어 실패: {e}")

            # 3. 캐시 파일 클리어
            cache_files = ["instance/.cache_stats", "instance/.last_update"]

            for cache_file in cache_files:
                cache_path = Path(cache_file)
                if cache_path.exists():
                    try:
                        cache_path.unlink()
                        cleared_items.append(f"캐시 파일 {cache_file} 삭제")
                    except Exception as e:
                        logger.warning(f"캐시 파일 {cache_file} 삭제 실패: {e}")

            # 소스 상태 초기화
            for source_key in self.sources:
                self.sources[source_key]["total_ips"] = 0
                self.sources[source_key]["status"] = "inactive"
                self.sources[source_key]["last_collection"] = None

            logger.info(f"데이터 클리어 완료: {len(cleared_items)}개 항목")

            return {
                "success": True,
                "message": "모든 데이터가 클리어되었습니다.",
                "cleared_items": cleared_items,
                "cleared_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"데이터 클리어 실패: {e}")
            return {"success": False, "message": f"데이터 클리어 실패: {str(e)}"}

    def is_collection_enabled(self, source: Optional[str] = None) -> bool:
        """수집 활성화 상태 확인"""
        if not self.config.get("collection_enabled", False):
            return False

        if source:
            return self.config.get("sources", {}).get(source, False)

        return True

    def get_status(self) -> Dict[str, Any]:
        """
        수집 서비스 전체 상태 반환 (ON/OFF 상태 포함)

        Returns:
            수집 상태 정보
        """
        try:
            # 데이터베이스에서 실제 IP 수 확인
            total_ips = self._get_total_ip_count()

            # 각 소스별 IP 수 확인
            for source_key in self.sources.keys():
                self.sources[source_key]["total_ips"] = self._get_source_ip_count(
                    source_key.upper()
                )

            active_sources = sum(1 for s in self.sources.values() if s["total_ips"] > 0)
            enabled_sources = sum(
                1 for s in self.sources.values() if s.get("enabled", False)
            )

            return {
                "status": (
                    "active"
                    if self.config.get("collection_enabled", False)
                    else "inactive"
                ),
                "collection_enabled": self.config.get("collection_enabled", False),
                "daily_collection_enabled": self.daily_collection_enabled,
                "last_enabled_at": self.config.get("last_enabled_at"),
                "last_disabled_at": self.config.get("last_disabled_at"),
                "last_daily_collection": self.last_daily_collection,
                "last_updated": datetime.now().isoformat(),
                "sources": {
                    source_key: {
                        "name": source_info["name"],
                        "enabled": source_info.get("enabled", False),
                        "status": (
                            "active" if source_info["total_ips"] > 0 else "no_data"
                        ),
                        "last_collection": source_info["last_collection"],
                        "total_ips": source_info["total_ips"],
                        "manual_only": source_info.get("manual_only", False),
                    }
                    for source_key, source_info in self.sources.items()
                },
                "summary": {
                    "total_sources": len(self.sources),
                    "enabled_sources": enabled_sources,
                    "active_sources": active_sources,
                    "total_ips_collected": total_ips,
                },
            }
        except Exception as e:
            logger.error(f"상태 조회 오류: {e}")
            return {
                "status": "error",
                "error": str(e),
                "last_updated": datetime.now().isoformat(),
            }

    def set_daily_collection_enabled(self) -> Dict[str, Any]:
        """
        일일 자동 수집 활성화
        """
        try:
            self.daily_collection_enabled = True
            self.config["daily_collection_enabled"] = True
            self._save_collection_config()

            logger.info("✅ 일일 자동 수집 활성화")

            return {
                "success": True,
                "message": "일일 자동 수집이 활성화되었습니다",
                "daily_collection_enabled": True,
            }
        except Exception as e:
            logger.error(f"일일 자동 수집 활성화 실패: {e}")
            return {"success": False, "error": str(e)}

    def set_daily_collection_disabled(self) -> Dict[str, Any]:
        """
        일일 자동 수집 비활성화
        """
        try:
            self.daily_collection_enabled = False
            self.config["daily_collection_enabled"] = False
            self._save_collection_config()

            logger.info("⏹️ 일일 자동 수집 비활성화")

            return {
                "success": True,
                "message": "일일 자동 수집이 비활성화되었습니다",
                "daily_collection_enabled": False,
            }
        except Exception as e:
            logger.error(f"일일 자동 수집 비활성화 실패: {e}")
            return {"success": False, "error": str(e)}

    def trigger_daily_collection(self) -> Dict[str, Any]:
        """
        일일 자동 수집 실행 (하루 단위 데이터만)
        """
        try:
            if not self.daily_collection_enabled:
                return {
                    "success": False,
                    "message": "일일 자동 수집이 비활성화 상태입니다",
                }

            # 오늘 날짜로 수집 범위 설정
            today = datetime.now()
            start_date = today.strftime("%Y%m%d")
            end_date = today.strftime("%Y%m%d")

            logger.info(f"🔄 일일 자동 수집 시작: {start_date}")

            results = {}

            # REGTECH 수집 (하루 단위)
            regtech_result = self.trigger_regtech_collection(
                start_date=start_date, end_date=end_date
            )
            results["regtech"] = regtech_result

            # SECUDIUM 수집 비활성화
            results["secudium"] = {
                "status": "disabled",
                "message": "SECUDIUM 수집기가 비활성화되었습니다",
                "source": "secudium",
                "collected_count": 0,
            }

            # 마지막 수집 시간 업데이트
            self.last_daily_collection = datetime.now().isoformat()
            self.config["last_daily_collection"] = self.last_daily_collection
            self._save_collection_config()

            return {
                "success": True,
                "message": "일일 자동 수집 완료",
                "collection_date": start_date,
                "results": results,
            }

        except Exception as e:
            logger.error(f"일일 자동 수집 실패: {e}")
            return {"success": False, "error": str(e)}

    def mark_initial_collection_done(self):
        """최초 수집 완료 표시"""
        self.config["initial_collection_done"] = True
        self.config["initial_collection_needed"] = False
        self._save_collection_config()
        logger.info("✅ 최초 수집 완료 표시")

    def is_initial_collection_needed(self) -> bool:
        """최초 수집이 필요한지 확인"""
        return self.config.get("initial_collection_needed", False)

    def trigger_regtech_collection(
        self, start_date: str = None, end_date: str = None
    ) -> Dict[str, Any]:
        """
        REGTECH 수집 트리거 - 보안 검사 후 실행

        🔴 방어적 보안 검사:
        - 수집 기능 활성화 상태 확인
        - 인증 시도 제한 확인
        - 강제 차단 모드 확인
        - 재시작 보호 모드 확인

        Args:
            start_date: 시작일 (YYYYMMDD), None이면 최근 90일
            end_date: 종료일 (YYYYMMDD), None이면 오늘

        Returns:
            수집 결과
        """
        try:
            # 🔴 보안 검사 1: 수집 기능 활성화 확인
            if not self.is_collection_enabled():
                logger.warning("🚫 REGTECH 수집 차단: 수집 기능이 비활성화됨")
                return {
                    "success": False,
                    "message": "수집 기능이 비활성화되어 있습니다. 먼저 수집을 활성화하세요.",
                    "source": "regtech",
                    "timestamp": datetime.now().isoformat(),
                    "security_blocked": True,
                    "reason": "collection_disabled",
                }

            # 🔴 보안 검사 2: 강제 차단 환경변수 확인
            if os.getenv("FORCE_DISABLE_COLLECTION", "true").lower() in (
                "true",
                "1",
                "yes",
                "on",
            ):
                logger.error("🚨 REGTECH 수집 차단: FORCE_DISABLE_COLLECTION=true")
                return {
                    "success": False,
                    "message": "환경변수 FORCE_DISABLE_COLLECTION=true로 인해 수집이 차단되었습니다",
                    "source": "regtech",
                    "timestamp": datetime.now().isoformat(),
                    "security_blocked": True,
                    "force_disabled": True,
                }

            # 🔴 보안 검사 3: 인증 시도 제한 확인
            if not self._check_auth_attempt_limit("regtech"):
                logger.warning("🚫 REGTECH 수집 차단: 인증 시도 제한 초과")
                return {
                    "success": False,
                    "message": "REGTECH 소스가 인증 시도 제한으로 차단되었습니다",
                    "source": "regtech",
                    "timestamp": datetime.now().isoformat(),
                    "security_blocked": True,
                    "auth_limit_exceeded": True,
                }

            # 🔴 보안 검사 4: 소스 활성화 상태 확인
            if not self.sources["regtech"]["enabled"]:
                logger.warning("🚫 REGTECH 수집 차단: 소스가 비활성화됨")
                return {
                    "success": False,
                    "message": "REGTECH 소스가 비활성화되어 있습니다",
                    "source": "regtech",
                    "timestamp": datetime.now().isoformat(),
                    "security_blocked": True,
                    "source_disabled": True,
                }

            logger.warning(
                f"⚠️  REGTECH 외부 인증 시작 (start_date={start_date}, end_date={end_date})"
            )
            logger.info("🔓 금융보안원 서버 접속 시도 중...")

            # 인증 시도 기록 (시작)
            self.record_auth_attempt("regtech", success=False)

            # Enhanced REGTECH 수집기 import 및 실행
            try:
                # Enhanced 수집기 우선 시도
                try:
                    from .regtech_collector_enhanced import EnhancedRegtechCollector

                    data_dir = os.path.join(os.path.dirname(self.db_path), "..", "data")
                    collector = EnhancedRegtechCollector(data_dir=data_dir)

                    # 수집 실행
                    logger.info(
                        f"Enhanced REGTECH 수집기 사용 (start_date={start_date}, end_date={end_date})"
                    )
                    ips = collector.collect_from_web(
                        start_date=start_date, end_date=end_date
                    )

                    if ips:
                        # 인증 성공 기록
                        self.record_auth_attempt("regtech", success=True)

                        # 데이터베이스에 저장
                        saved_count = self._save_ips_to_database(ips, "REGTECH")

                        # 수집 성공
                        self.sources["regtech"][
                            "last_collection"
                        ] = datetime.now().isoformat()
                        self.sources["regtech"]["status"] = "active"

                        # IP 수 업데이트
                        ip_count = self._get_source_ip_count("REGTECH")
                        self.sources["regtech"]["total_ips"] = ip_count

                        logger.info(f"✅ REGTECH 수집 성공: {saved_count:,}개 IP 수집")

                        return {
                            "success": True,
                            "message": f"REGTECH 수집 완료: {saved_count:,}개 IP 저장 (총 {ip_count:,}개)",
                            "source": "regtech",
                            "timestamp": datetime.now().isoformat(),
                            "details": {
                                "collected": len(ips),
                                "saved": saved_count,
                                "total_in_db": ip_count,
                                "collector": "enhanced",
                                "auth_success": True,
                            },
                        }
                    else:
                        # 인증 실패 기록
                        self.record_auth_attempt("regtech", success=False)
                        logger.error("❌ REGTECH 수집 실패: 데이터 없음")

                        return {
                            "success": False,
                            "message": "REGTECH 수집 실패: 데이터를 가져오지 못했습니다 (인증 오류 가능)",
                            "source": "regtech",
                            "timestamp": datetime.now().isoformat(),
                            "auth_failed": True,
                        }

                except ImportError:
                    # HAR 기반 수집기로 폴백
                    logger.warning("Enhanced 수집기 사용 불가, HAR 기반 수집기로 폴백")
                    from .har_based_regtech_collector import HarBasedRegtechCollector

                    data_dir = os.path.join(os.path.dirname(self.db_path), "..", "data")
                    collector = HarBasedRegtechCollector(data_dir=data_dir)

                    if start_date and end_date:
                        ips = collector.collect_from_web(
                            start_date=start_date, end_date=end_date
                        )
                        result = {
                            "success": True if ips else False,
                            "total_collected": len(ips) if ips else 0,
                            "ips": ips,
                        }
                    else:
                        result = collector.auto_collect(
                            prefer_web=True, db_path=self.db_path
                        )

                    if result.get("success", False):
                        # 인증 성공 기록
                        self.record_auth_attempt("regtech", success=True)

                        self.sources["regtech"][
                            "last_collection"
                        ] = datetime.now().isoformat()
                        self.sources["regtech"]["status"] = "active"
                        ip_count = self._get_source_ip_count("REGTECH")
                        self.sources["regtech"]["total_ips"] = ip_count

                        logger.info(f"✅ REGTECH HAR 수집 성공: {ip_count:,}개 IP")

                        return {
                            "success": True,
                            "message": f"REGTECH 수집 완료: {ip_count:,}개 IP",
                            "source": "regtech",
                            "timestamp": datetime.now().isoformat(),
                            "details": {
                                **result,
                                "collector": "har_based",
                                "auth_success": True,
                            },
                        }
                    else:
                        # 인증 실패 기록
                        self.record_auth_attempt("regtech", success=False)
                        logger.error(
                            f"❌ REGTECH HAR 수집 실패: {result.get('error', '알 수 없는 오류')}"
                        )

                        return {
                            "success": False,
                            "message": f'REGTECH 수집 실패: {result.get("error", "알 수 없는 오류")} (인증 문제 가능)',
                            "source": "regtech",
                            "timestamp": datetime.now().isoformat(),
                            "auth_failed": True,
                        }

            except ImportError as e:
                logger.error(f"REGTECH 수집기 import 실패: {e}")
                # 인증 시도 실패 기록
                self.record_auth_attempt("regtech", success=False)

                return {
                    "success": False,
                    "message": f"REGTECH 수집기 모듈을 찾을 수 없습니다: {e}",
                    "source": "regtech",
                    "timestamp": datetime.now().isoformat(),
                    "module_error": True,
                }

        except Exception as e:
            logger.error(f"REGTECH 수집 오류: {e}")
            logger.error(traceback.format_exc())

            # 예외 발생 시에도 인증 실패 기록
            self.record_auth_attempt("regtech", success=False)

            return {
                "success": False,
                "message": f"REGTECH 수집 중 오류 발생: {str(e)}",
                "source": "regtech",
                "timestamp": datetime.now().isoformat(),
                "exception_error": True,
            }

    def collect_secudium_data(self) -> Dict[str, Any]:
        """
        SECUDIUM 데이터 수집 - 비활성화됨

        Returns:
            수집 결과
        """
        return self.trigger_secudium_collection()

    def trigger_secudium_collection(self) -> Dict[str, Any]:
        """
        SECUDIUM 수집 트리거 - 보안 검사 후 차단

        🔴 방어적 보안 검사:
        - 기본적으로 모든 SECUDIUM 수집 차단
        - 수집 기능 활성화 상태 확인
        - 인증 시도 제한 확인
        - 강제 차단 모드 확인

        Returns:
            수집 결과 (기본적으로 차단됨)
        """
        # 🔴 보안 검사 1: SECUDIUM 기본 차단 (계정 문제로 인한)
        logger.warning("🚫 SECUDIUM 수집 기본 차단: 계정 문제 및 보안상 차단")
        return {
            "success": False,
            "status": "blocked",
            "message": "SECUDIUM 수집기가 보안상 차단되었습니다 (계정 문제 및 서버 보호)",
            "source": "secudium",
            "collected_count": 0,
            "timestamp": datetime.now().isoformat(),
            "security_blocked": True,
            "reason": "default_security_block",
            "details": {
                "account_issues": True,
                "server_protection": True,
                "manual_enable_required": False,  # 수동 활성화도 차단
            },
        }

    def get_collection_history(
        self, source: str = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        수집 히스토리 조회

        Args:
            source: 특정 소스 (없으면 전체)
            limit: 최대 결과 수

        Returns:
            수집 히스토리 목록
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if source:
                cursor.execute(
                    """
                    SELECT ip, source, detection_date, created_at
                    FROM blacklist_ip
                    WHERE UPPER(source) = UPPER(?)
                    ORDER BY created_at DESC LIMIT ?
                """,
                    (source, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT ip, source, detection_date, created_at
                    FROM blacklist_ip
                    ORDER BY created_at DESC LIMIT ?
                """,
                    (limit,),
                )

            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    "ip": row[0],
                    "source": row[1],
                    "detection_date": row[2],
                    "created_at": row[3],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"수집 히스토리 조회 오류: {e}")
            return []

    def _get_total_ip_count(self) -> int:
        """총 IP 수 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM blacklist_ip")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"총 IP 수 조회 오류: {e}")
            return 0

    def _get_source_ip_count(self, source: str) -> int:
        """특정 소스의 IP 수 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM blacklist_ip WHERE UPPER(source) = UPPER(?)",
                (source,),
            )
            count = cursor.fetchone()[0]
            conn.close()
            logger.debug(f"Source {source} has {count} IPs in database")
            return count
        except Exception as e:
            logger.error(f"소스 IP 수 조회 오류: {e}")
            return 0

    def _save_ips_to_database(self, ips: List[Any], source: str) -> int:
        """
        IP 목록을 데이터베이스에 저장

        Args:
            ips: BlacklistEntry 객체 목록
            source: 소스명

        Returns:
            저장된 IP 수
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            saved_count = 0

            for ip_entry in ips:
                try:
                    # BlacklistEntry 객체에서 데이터 추출
                    ip_address = ip_entry.ip_address
                    country = getattr(ip_entry, "country", "Unknown")
                    reason = getattr(ip_entry, "reason", "")
                    reg_date = getattr(
                        ip_entry, "reg_date", datetime.now().strftime("%Y-%m-%d")
                    )
                    threat_level = getattr(ip_entry, "threat_level", "high")

                    # 중복 확인
                    cursor.execute(
                        "SELECT COUNT(*) FROM blacklist_ip WHERE ip = ? AND source = ?",
                        (ip_address, source),
                    )

                    if cursor.fetchone()[0] == 0:
                        # 새로운 IP 삽입
                        cursor.execute(
                            """
                            INSERT INTO blacklist_ip
                            (ip, source, country, reason, detection_date, threat_level, is_active, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, 1, datetime('now'))
                        """,
                            (
                                ip_address,
                                source,
                                country,
                                reason,
                                reg_date,
                                threat_level,
                            ),
                        )
                        saved_count += 1
                    else:
                        # 기존 IP 업데이트
                        cursor.execute(
                            """
                            UPDATE blacklist_ip
                            SET country = ?, reason = ?, detection_date = ?,
                                threat_level = ?, updated_at = datetime('now')
                            WHERE ip = ? AND source = ?
                        """,
                            (
                                country,
                                reason,
                                reg_date,
                                threat_level,
                                ip_address,
                                source,
                            ),
                        )

                except Exception as e:
                    logger.warning(f"IP 저장 중 오류 ({ip_address}): {e}")
                    continue

            conn.commit()
            conn.close()

            logger.info(f"{source}: {saved_count}개 IP 저장됨")
            return saved_count

        except Exception as e:
            logger.error(f"데이터베이스 저장 오류: {e}")
            return 0

    def clear_source_data(self, source: str) -> Dict[str, Any]:
        """
        특정 소스의 데이터 삭제

        Args:
            source: 삭제할 소스명

        Returns:
            삭제 결과
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM blacklist_ip WHERE UPPER(source) = UPPER(?)", (source,)
            )
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()

            # 소스 상태 업데이트
            source_key = source.lower()
            if source_key in self.sources:
                self.sources[source_key]["total_ips"] = 0
                self.sources[source_key]["status"] = "inactive"

            return {
                "success": True,
                "message": f"{source} 데이터 삭제 완료: {deleted_count:,}개",
                "deleted_count": deleted_count,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"소스 데이터 삭제 오류: {e}")
            return {
                "success": False,
                "message": f"{source} 데이터 삭제 실패: {str(e)}",
                "timestamp": datetime.now().isoformat(),
            }


# 전역 인스턴스
collection_manager = CollectionManager()
