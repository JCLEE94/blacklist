#!/usr/bin/env python3
"""
Collection Status Service
수집 상태 및 정보 관리 서비스
"""

import logging
import os
from datetime import datetime
from typing import Any
from typing import Dict
from typing import Optional

from .auth_service import AuthService
from .config_service import CollectionConfigService
from .protection_service import ProtectionService

logger = logging.getLogger(__name__)


class StatusService:
    """수집 상태 및 정보 서비스"""

    def __init__(
        self,
        config_service: CollectionConfigService,
        protection_service: ProtectionService,
        auth_service: AuthService,
    ):
        self.config_service = config_service
        self.protection_service = protection_service
        self.auth_service = auth_service

    def get_status(self) -> Dict[str, Any]:
        """전체 수집 상태 조회"""
        try:
            # 기본 설정 정보
            config = self.config_service.load_collection_config()
            enabled = config.get("enabled", False)

            # 보호 상태 조회
            protection_status = self.protection_service.get_protection_status()

            # 인증 통계
            auth_stats = self.auth_service.get_auth_statistics(hours=24)

            # 환경변수 상태
            env_info = self._get_environment_info()

            # 소스별 상태
            sources_status = self._get_sources_status()

            return {
                "enabled": enabled,
                "safe_to_enable": protection_status["safe_to_enable"],
                "protection_reason": protection_status["safety_reason"],
                "environment": env_info,
                "protection": protection_status,
                "sources": sources_status,
                "authentication": auth_stats,
                "last_updated": datetime.now().isoformat(),
                "config_summary": {
                    "sources_configured": len(config.get("sources", {})),
                    "safety_settings": config.get("safety_settings", {}),
                    "config_last_updated": config.get("updated_at"),
                },
            }

        except Exception as e:
            logger.error(f"Error getting collection status: {e}")
            return {
                "error": str(e),
                "enabled": False,
                "safe_to_enable": False,
                "protection_reason": "상태 조회 오류: {e}",
                "last_updated": datetime.now().isoformat(),
            }

    def _get_environment_info(self) -> Dict[str, Any]:
        """환경변수 및 시스템 정보 조회"""
        return {
            "force_disable_collection": os.getenv("FORCE_DISABLE_COLLECTION", "true"),
            "collection_enabled": os.getenv("COLLECTION_ENABLED", "false"),
            "restart_protection": os.getenv("RESTART_PROTECTION", "true"),
            "max_auth_attempts": os.getenv("MAX_AUTH_ATTEMPTS", "10"),
            "regtech_configured": bool(os.getenv("REGTECH_USERNAME")),
            "secudium_configured": bool(os.getenv("SECUDIUM_USERNAME")),
        }

    def _get_sources_status(self) -> Dict[str, Any]:
        """소스별 상태 조회"""
        sources = ["regtech", "secudium"]
        sources_status = {}

        for source in sources:
            source_config = self.config_service.get_source_config(source)
            is_blocked, block_reason = self.auth_service.is_source_blocked(source)

            sources_status[source] = {
                "enabled": source_config.get("enabled", False),
                "last_collection": source_config.get("last_collection"),
                "blocked": is_blocked,
                "block_reason": block_reason if is_blocked else None,
                "credentials_configured": bool(os.getenv("{source.upper()}_USERNAME")),
            }

        return sources_status

    def get_detailed_status(self) -> Dict[str, Any]:
        """상세 수집 상태 조회 (디버깅용)"""
        basic_status = self.get_status()

        # 추가 상세 정보
        additional_info = {
            "recent_auth_attempts": self.auth_service.get_recent_auth_attempts(
                limit=20
            ),
            "protection_bypass": self.protection_service.check_protection_bypass(),
            "config_history": self._get_config_change_history(),
            "system_health": self._get_system_health_info(),
        }

        # 기본 상태에 상세 정보 추가
        basic_status.update(additional_info)

        return basic_status

    def _get_config_change_history(self) -> list:
        """설정 변경 이력 (간단한 버전)"""
        try:
            # 실제 구현에서는 DB에서 이력을 조회
            # 여기서는 기본 정보만 반환
            config = self.config_service.load_collection_config()
            return [
                {
                    "timestamp": config.get("updated_at", config.get("created_at")),
                    "action": "config_loaded",
                    "enabled": config.get("enabled", False),
                }
            ]
        except Exception as e:
            logger.warning(f"Could not load config history: {e}")
            return []

    def _get_system_health_info(self) -> Dict[str, Any]:
        """시스템 상태 정보"""
        try:
            import psutil

            return {
                "memory_usage_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage("/").percent,
                "cpu_usage_percent": psutil.cpu_percent(interval=1),
            }
        except ImportError:
            return {"note": "psutil not available - system metrics unavailable"}
        except Exception as e:
            return {"error": "System health check failed: {e}"}

    def is_collection_enabled(self, source: Optional[str] = None) -> bool:
        """수집 활성화 상태 확인"""
        try:
            # 1. 전체 수집 비활성화 검사
            config = self.config_service.load_collection_config()
            if not config.get("enabled", False):
                return False

            # 2. 보호 상태 검사
            safe, _ = self.protection_service.is_collection_safe_to_enable()
            if not safe:
                return False

            # 3. 특정 소스 검사
            if source:
                source_config = self.config_service.get_source_config(source)
                if not source_config.get("enabled", False):
                    return False

                # 소스별 인증 차단 검사
                is_blocked, _ = self.auth_service.is_source_blocked(source)
                if is_blocked:
                    return False

            return True

        except Exception as e:
            logger.error(f"Error checking collection enabled status: {e}")
            return False

    def get_collection_summary(self) -> Dict[str, Any]:
        """수집 상태 요약 정보"""
        status = self.get_status()

        return {
            "enabled": status["enabled"],
            "safe": status["safe_to_enable"],
            "reason": status["protection_reason"],
            "sources": {
                source: info["enabled"] and not info["blocked"]
                for source, info in status.get("sources", {}).items()
            },
            "last_check": status["last_updated"],
        }

    def validate_collection_requirements(self) -> Dict[str, Any]:
        """수집 요구사항 검증"""
        validation_results = {
            "valid": True,
            "issues": [],
            "warnings": [],
            "requirements": {},
        }

        # 환경변수 검사
        env_info = self._get_environment_info()

        # REGTECH 자격 증명 검사
        if not env_info["regtech_configured"]:
            validation_results["issues"].append("REGTECH 자격 증명이 설정되지 않음")
            validation_results["valid"] = False
        else:
            validation_results["requirements"]["regtech_auth"] = True

        # SECUDIUM 자격 증명 검사
        if not env_info["secudium_configured"]:
            validation_results["issues"].append("SECUDIUM 자격 증명이 설정되지 않음")
            validation_results["valid"] = False
        else:
            validation_results["requirements"]["secudium_auth"] = True

        # 강제 비활성화 검사
        if env_info["force_disable_collection"].lower() in ("true", "1", "yes"):
            validation_results["warnings"].append("환경변수에 의한 강제 비활성화 상태")

        # 보호 상태 검사
        protection_status = self.protection_service.get_protection_status()
        if not protection_status["safe_to_enable"]:
            validation_results["issues"].append(
                "보호 시스템 차단: {protection_status['safety_reason']}"
            )
            validation_results["valid"] = False
        else:
            validation_results["requirements"]["protection_safe"] = True

        return validation_results
