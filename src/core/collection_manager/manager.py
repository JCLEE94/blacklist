#!/usr/bin/env python3
"""
Collection Manager - Main coordination class
통합 수집 관리자 (Unified Collection Manager)
REGTECH, SECUDIUM 등 다양한 소스의 데이터 수집을 통합 관리
수집 ON/OFF 기능 및 데이터 클리어 기능 포함
"""

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .auth_service import AuthService
from .config_service import CollectionConfigService
from .protection_service import ProtectionService
from .status_service import StatusService

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

        # Initialize services
        self.config_service = CollectionConfigService(db_path, str(config_path))
        self.protection_service = ProtectionService(db_path, str(config_path))
        self.auth_service = AuthService(db_path)
        self.status_service = StatusService(
            self.config_service, self.protection_service, self.auth_service
        )

        # 초기 설정 및 보호 시스템 활성화
        self._initialize_protection_system()

        logger.info(
            "CollectionManager initialized with modular services - DB: {db_path}, Config: {config_path}"
        )

    def _initialize_protection_system(self):
        """보호 시스템 초기화"""
        try:
            # 설정 파일이 없으면 보호 기능이 적용된 초기 설정 생성
            if not self.config_path.exists():
                logger.info("Creating initial protected configuration")
                self.config_service.create_initial_config_with_protection()

            # 급속 재시작 감지
            if self.protection_service.detect_rapid_restart():
                logger.warning(
                    "Rapid restart detected - collection will be disabled for safety"
                )

        except Exception as e:
            logger.error(f"Error initializing protection system: {e}")

    def enable_collection(
        self,
        sources: Optional[List[str]] = None,
        clear_data_first: bool = True,
        bypass_protection: bool = False,
        reason: str = "Manual enable request",
    ) -> Dict[str, Any]:
        """수집 활성화 (보호 시스템 적용)"""
        try:
            # 1. 보호 시스템 검사 (바이패스 옵션 확인)
            if not bypass_protection:
                (
                    safe,
                    safety_reason,
                ) = self.protection_service.is_collection_safe_to_enable()
                if not safe:
                    return {
                        "success": False,
                        "error": "보호 시스템에 의한 차단",
                        "reason": safety_reason,
                        "timestamp": datetime.now().isoformat(),
                        "protection_active": True,
                    }
            else:
                logger.warning(
                    f"Protection bypass used for collection enable: {reason}"
                )

            # 2. 데이터 클리어 (요청 시)
            clear_result = None
            if clear_data_first:
                clear_result = self.clear_all_data()
                logger.info(f"Data cleared before enabling collection: {clear_result}")

            # 3. 설정 업데이트
            config = self.config_service.load_collection_config()
            config["enabled"] = True
            config["enabled_at"] = datetime.now().isoformat()
            config["enabled_reason"] = reason
            config["bypass_protection"] = bypass_protection

            # 소스별 활성화
            if sources:
                for source in sources:
                    if source in ["regtech", "secudium"]:
                        config.setdefault("sources", {})[source] = {
                            "enabled": True,
                            "enabled_at": datetime.now().isoformat(),
                        }
            else:
                # 모든 소스 활성화
                config.setdefault("sources", {})["regtech"] = {
                    "enabled": True,
                    "enabled_at": datetime.now().isoformat(),
                }
                config.setdefault("sources", {})["secudium"] = {
                    "enabled": True,
                    "enabled_at": datetime.now().isoformat(),
                }

            # 설정 저장
            self.config_service.save_collection_config(config)
            self.config_service.save_collection_enabled_to_db(True)

            # 4. 인증 실패 기록 리셋
            self.auth_service.reset_auth_attempts()

            result = {
                "success": True,
                "enabled": True,
                "sources": sources or ["regtech", "secudium"],
                "data_cleared": clear_data_first,
                "clear_result": clear_result,
                "bypass_protection": bypass_protection,
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(f"Collection enabled successfully: {result}")
            return result

        except Exception as e:
            logger.error(f"Error enabling collection: {e}")
            return {
                "success": False,
                "error": "수집 활성화 중 오류: {e}",
                "timestamp": datetime.now().isoformat(),
            }

    def disable_collection(self) -> Dict[str, Any]:
        """수집 비활성화"""
        try:
            # 설정 업데이트
            config = self.config_service.load_collection_config()
            config["enabled"] = False
            config["disabled_at"] = datetime.now().isoformat()
            config["disabled_reason"] = "Manual disable request"

            # 모든 소스 비활성화
            if "sources" in config:
                for source in config["sources"]:
                    config["sources"][source]["enabled"] = False
                    config["sources"][source][
                        "disabled_at"
                    ] = datetime.now().isoformat()

            self.config_service.save_collection_config(config)
            self.config_service.save_collection_enabled_to_db(False)

            result = {
                "success": True,
                "enabled": False,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(f"Collection disabled successfully: {result}")
            return result

        except Exception as e:
            logger.error(f"Error disabling collection: {e}")
            return {
                "success": False,
                "error": "수집 비활성화 중 오류: {e}",
                "timestamp": datetime.now().isoformat(),
            }

    def clear_all_data(self) -> Dict[str, Any]:
        """모든 수집 데이터 삭제"""
        try:
            cleared_items = {
                "files_removed": 0,
                "directories_cleaned": 0,
                "auth_records_cleared": 0,
            }

            # 1. Excel 파일들 삭제
            patterns = [
                "regtech*.xlsx",
                "REGTECH*.xlsx",
                "secudium*.xlsx",
                "SECUDIUM*.xlsx",
            ]

            for pattern in patterns:
                import glob

                for file_path in glob.glob(pattern, recursive=True):
                    try:
                        os.remove(file_path)
                        cleared_items["files_removed"] += 1
                        logger.debug(f"Removed file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Could not remove {file_path}: {e}")

            # 2. 임시 디렉토리 정리
            temp_dirs = ["temp", "downloads", "cache"]
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir) and os.path.isdir(temp_dir):
                    try:
                        shutil.rmtree(temp_dir)
                        os.makedirs(temp_dir, exist_ok=True)
                        cleared_items["directories_cleaned"] += 1
                        logger.debug(f"Cleaned directory: {temp_dir}")
                    except Exception as e:
                        logger.warning(f"Could not clean directory {temp_dir}: {e}")

            # 3. 인증 실패 기록 정리
            auth_clear_result = self.auth_service.reset_auth_attempts()
            cleared_items["auth_records_cleared"] = auth_clear_result.get(
                "records_cleared", 0
            )

            result = {
                "success": True,
                "cleared_items": cleared_items,
                "total_items_cleared": sum(cleared_items.values()),
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(f"Data cleared successfully: {cleared_items}")
            return result

        except Exception as e:
            logger.error(f"Error clearing data: {e}")
            return {
                "success": False,
                "error": "데이터 삭제 중 오류: {e}",
                "timestamp": datetime.now().isoformat(),
            }

    # Delegate methods to appropriate services
    def is_collection_enabled(self, source: Optional[str] = None) -> bool:
        """수집 활성화 상태 확인"""
        return self.status_service.is_collection_enabled(source)

    def get_status(self) -> Dict[str, Any]:
        """수집 상태 조회"""
        return self.status_service.get_status()

    def get_detailed_status(self) -> Dict[str, Any]:
        """상세 수집 상태 조회"""
        return self.status_service.get_detailed_status()

    def record_auth_attempt(
        self, source: str, success: bool = False, details: str = None
    ):
        """인증 시도 기록"""
        self.auth_service.record_auth_attempt(source, success, details)

    def get_auth_statistics(self, source: str = None, hours: int = 24) -> Dict:
        """인증 통계 조회"""
        return self.auth_service.get_auth_statistics(source, hours)

    def reset_protection_state(self) -> Dict[str, bool]:
        """보호 상태 리셋"""
        return self.protection_service.reset_protection_state()

    # Legacy methods for backward compatibility
    def set_daily_collection_enabled(self) -> Dict[str, Any]:
        """일일 수집 활성화 (legacy)"""
        return self.enable_collection(reason="Daily collection schedule")

    def set_daily_collection_disabled(self) -> Dict[str, Any]:
        """일일 수집 비활성화 (legacy)"""
        return self.disable_collection()

    def is_collection_safe_to_enable(self) -> tuple[bool, str]:
        """수집 활성화 안전성 검사"""
        return self.protection_service.is_collection_safe_to_enable()

    def create_protection_bypass(self, reason: str, duration_minutes: int = 60) -> Dict:
        """보호 바이패스 생성"""
        return self.protection_service.create_protection_bypass(
            reason, duration_minutes
        )

    def validate_collection_requirements(self) -> Dict[str, Any]:
        """수집 요구사항 검증"""
        return self.status_service.validate_collection_requirements()

    @property
    def collection_enabled(self) -> bool:
        """수집 활성화 상태 속성 (backward compatibility)"""
        return self.is_collection_enabled()

    def get_collection_status(self) -> Dict[str, Any]:
        """수집 상태 조회 (backward compatibility for get_status)"""
        return self.get_status()

    def is_initial_collection_needed(self) -> bool:
        """초기 수집이 필요한지 확인 (backward compatibility)"""
        try:
            status = self.get_status()
            # 수집이 활성화되어 있지만 마지막 업데이트가 없거나 오래된 경우
            if status.get("enabled", False):
                last_update = status.get("last_update")
                if not last_update:
                    return True

                # 마지막 업데이트가 24시간 이전이면 초기 수집 필요
                from datetime import datetime, timedelta

                try:
                    last_update_dt = datetime.fromisoformat(
                        last_update.replace("Z", "+00:00")
                    )
                    return datetime.now() - last_update_dt > timedelta(hours=24)
                except (ValueError, TypeError):
                    return True

            return False
        except Exception as e:
            logger.warning(f"Error checking initial collection need: {e}")
            return False

    def mark_initial_collection_done(self) -> Dict[str, Any]:
        """초기 수집 완료 표시 (backward compatibility)"""
        try:
            config = self.config_service.load_collection_config()
            config["initial_collection_done"] = True
            config["initial_collection_completed_at"] = datetime.now().isoformat()
            self.config_service.save_collection_config(config)

            logger.info("Initial collection marked as completed")
            return {
                "success": True,
                "message": "Initial collection marked as completed",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error marking initial collection done: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
