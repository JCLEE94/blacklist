#!/usr/bin/env python3
"""
통합 수집 관리자 (Unified Collection Manager) - DB 설정 연동 버전
REGTECH, SECUDIUM 등 다양한 소스의 데이터 수집을 통합 관리
수집 ON/OFF 기능 및 데이터 클리어 기능 포함
"""
import os
import logging
import json
import sqlite3
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import traceback

logger = logging.getLogger(__name__)


class CollectionManager:
    """통합 수집 관리자 - 수집 ON/OFF 및 데이터 관리"""

    def __init__(
        self,
        db_path: str = "instance/blacklist.db",
        config_path: str = "instance/collection_config.json",
    ):
        """
        초기화

        Args:
            db_path: 데이터베이스 경로
            config_path: 수집 설정 파일 경로
        """
        self.db_path = db_path
        self.config_path = Path(config_path)

        # 설정 디렉토리 생성
        self.config_path.parent.mkdir(exist_ok=True)

        # DB 기반 설정 관리자 가져오기
        try:
            from src.models.settings import get_settings_manager

            self.settings_manager = get_settings_manager()
        except Exception as e:
            logger.warning(f"DB 설정 관리자 로드 실패: {e}")
            self.settings_manager = None

        # 수집 설정 로드 (DB 우선, 파일 폴백)
        self.config = self._load_collection_config()

        # collection_enabled 속성 설정 (DB 우선)
        self.collection_enabled = self._get_collection_enabled()

        # 일일 자동 수집 설정
        self.daily_collection_enabled = self._get_setting(
            "daily_collection_enabled", False
        )
        self.last_daily_collection = self._get_setting("last_daily_collection", None)

        self.sources = {
            "regtech": {
                "name": "REGTECH (금융보안원)",
                "status": "inactive",
                "last_collection": None,
                "total_ips": 0,
                "manual_only": True,
                "enabled": self._get_regtech_enabled(),
            },
            "secudium": {
                "name": "SECUDIUM (에스케이인포섹)",
                "status": "disabled",
                "last_collection": None,
                "total_ips": 0,
                "manual_only": True,
                "enabled": self._get_secudium_enabled(),
            },
        }

    def _get_collection_enabled(self) -> bool:
        """수집 활성화 상태 확인 (DB 우선)"""
        if self.settings_manager:
            try:
                return self.settings_manager.get_setting("collection_enabled", True)
            except:
                pass
        return self.config.get("collection_enabled", False)

    def _get_regtech_enabled(self) -> bool:
        """REGTECH 활성화 상태 확인 (DB 우선)"""
        if self.settings_manager:
            try:
                return self.settings_manager.get_setting("regtech_enabled", True)
            except:
                pass
        return self.config.get("sources", {}).get("regtech", False)

    def _get_secudium_enabled(self) -> bool:
        """SECUDIUM 활성화 상태 확인 (DB 우선)"""
        if self.settings_manager:
            try:
                return self.settings_manager.get_setting("secudium_enabled", False)
            except:
                pass
        return False  # SECUDIUM은 항상 비활성화

    def _get_setting(self, key: str, default: Any) -> Any:
        """설정값 가져오기 (DB 우선)"""
        if self.settings_manager:
            try:
                return self.settings_manager.get_setting(key, default)
            except:
                pass
        return self.config.get(key, default)

    def _load_collection_config(self) -> Dict[str, Any]:
        """수집 설정 로드"""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    # 최초 실행 확인
                    if not config.get("initial_collection_done", False):
                        logger.info("🔥 최초 실행 감지 - 자동 수집 활성화")
                        config["collection_enabled"] = True
                        config["sources"] = {"regtech": True, "secudium": False}
                        config["initial_collection_needed"] = True
                    return config
            else:
                # 설정 파일이 없으면 최초 실행
                logger.info("🔥 최초 실행 - 자동 수집 활성화")
                return {
                    "collection_enabled": True,
                    "sources": {"regtech": True, "secudium": False},
                    "last_enabled_at": datetime.now().isoformat(),
                    "last_disabled_at": None,
                    "daily_collection_enabled": False,
                    "last_daily_collection": None,
                    "initial_collection_done": False,
                    "initial_collection_needed": True,
                }
        except Exception as e:
            logger.error(f"설정 로드 실패: {e}")
            return {
                "collection_enabled": True,
                "sources": {"regtech": True, "secudium": False},
                "last_enabled_at": datetime.now().isoformat(),
                "last_disabled_at": None,
                "daily_collection_enabled": False,
                "last_daily_collection": None,
                "initial_collection_done": False,
                "initial_collection_needed": True,
            }

    def _save_collection_config(self):
        """수집 설정 저장 (파일 및 DB)"""
        try:
            # 파일에 저장
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            logger.info(f"설정 파일 저장됨: {self.config_path}")

            # DB에도 저장
            if self.settings_manager:
                self.settings_manager.set_setting(
                    "collection_enabled",
                    self.collection_enabled,
                    "boolean",
                    "collection",
                )
                self.settings_manager.set_setting(
                    "regtech_enabled",
                    self.sources["regtech"]["enabled"],
                    "boolean",
                    "collection",
                )
                self.settings_manager.set_setting(
                    "secudium_enabled",
                    self.sources["secudium"]["enabled"],
                    "boolean",
                    "collection",
                )
                logger.info("설정 DB 저장됨")

        except Exception as e:
            logger.error(f"설정 저장 실패: {e}")

    def enable_collection(
        self, sources: Optional[Dict[str, bool]] = None
    ) -> Dict[str, Any]:
        """수집 활성화 - 기존 데이터 클리어 후 신규 수집 시작"""
        try:
            # 기존 데이터 클리어
            clear_result = self.clear_all_data()
            if not clear_result.get("success", False):
                return {
                    "success": False,
                    "message": f'데이터 클리어 실패: {clear_result.get("message")}',
                }

            # 수집 활성화
            self.config["collection_enabled"] = True
            self.collection_enabled = True
            self.config["last_enabled_at"] = datetime.now().isoformat()

            if sources:
                self.config["sources"].update(sources)
            else:
                # 기본적으로 REGTECH만 활성화
                self.config["sources"] = {"regtech": True, "secudium": False}

            # 소스 상태 업데이트
            self.sources["regtech"]["enabled"] = self.config["sources"].get(
                "regtech", False
            )
            self.sources["secudium"]["enabled"] = False  # SECUDIUM은 항상 비활성화

            self._save_collection_config()

            logger.info("수집이 활성화되었습니다. 모든 기존 데이터가 삭제되었습니다.")

            return {
                "success": True,
                "message": "수집이 활성화되었습니다. 기존 데이터가 클리어되었습니다.",
                "collection_enabled": True,
                "sources": self.config["sources"],
                "enabled_at": self.config["last_enabled_at"],
                "cleared_items": clear_result.get("cleared_items", []),
            }

        except Exception as e:
            logger.error(f"수집 활성화 실패: {e}")
            return {"success": False, "message": f"수집 활성화 실패: {str(e)}"}

    def disable_collection(self) -> Dict[str, Any]:
        """수집 비활성화"""
        try:
            self.config["collection_enabled"] = False
            self.collection_enabled = False
            self.config["last_disabled_at"] = datetime.now().isoformat()

            # 모든 소스 비활성화
            for source in self.config["sources"]:
                self.config["sources"][source] = False

            # 소스 상태 업데이트
            for source_key in self.sources:
                self.sources[source_key]["enabled"] = False

            self._save_collection_config()

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

    def get_collection_status(self) -> Dict[str, Any]:
        """현재 수집 상태 조회"""
        # DB에서 최신 상태 다시 로드
        self.collection_enabled = self._get_collection_enabled()
        self.sources["regtech"]["enabled"] = self._get_regtech_enabled()
        self.sources["secudium"]["enabled"] = self._get_secudium_enabled()

        return {
            "collection_enabled": self.collection_enabled,
            "sources": {
                source_key: {
                    "name": source_info["name"],
                    "enabled": source_info["enabled"],
                    "status": source_info["status"],
                    "last_collection": source_info["last_collection"],
                    "total_ips": source_info["total_ips"],
                }
                for source_key, source_info in self.sources.items()
            },
            "last_enabled_at": self.config.get("last_enabled_at"),
            "last_disabled_at": self.config.get("last_disabled_at"),
            "daily_collection_enabled": self.daily_collection_enabled,
            "last_daily_collection": self.last_daily_collection,
        }

    def clear_all_data(self) -> Dict[str, Any]:
        """모든 데이터 클리어"""
        try:
            cleared_items = []

            # 1. 데이터베이스 클리어
            if Path(self.db_path).exists():
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # 각 테이블별로 삭제 수행
                tables = ["blacklist_ip", "blacklist_raw", "blacklist_history"]
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        if count > 0:
                            cursor.execute(f"DELETE FROM {table}")
                            cleared_items.append(f"{table}: {count}개 삭제")
                            logger.info(f"{table} 테이블에서 {count}개 레코드 삭제")
                    except Exception as e:
                        logger.warning(f"{table} 처리 중 오류: {e}")

                conn.commit()
                conn.close()

            # 2. 캐시 클리어
            try:
                from src.core.container import get_container

                container = get_container()
                cache_manager = container.resolve("cache_manager")
                if cache_manager and hasattr(cache_manager.cache, "flush"):
                    cache_manager.cache.flush()
                    cleared_items.append("캐시: 전체 클리어")
                    logger.info("캐시 클리어 완료")
            except Exception as e:
                logger.warning(f"캐시 클리어 중 오류: {e}")

            # 3. 임시 파일 정리
            try:
                temp_dirs = ["temp", "downloads", "exports"]
                for temp_dir in temp_dirs:
                    temp_path = Path(temp_dir)
                    if temp_path.exists():
                        shutil.rmtree(temp_path)
                        temp_path.mkdir(exist_ok=True)
                        cleared_items.append(f"{temp_dir}: 디렉토리 정리")
            except Exception as e:
                logger.warning(f"임시 파일 정리 중 오류: {e}")

            return {
                "success": True,
                "message": "모든 데이터가 클리어되었습니다.",
                "cleared_items": cleared_items,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"데이터 클리어 실패: {e}")
            return {
                "success": False,
                "message": f"데이터 클리어 실패: {str(e)}",
                "error": traceback.format_exc(),
            }

    def trigger_collection(self, source: str, force: bool = False) -> Dict[str, Any]:
        """특정 소스의 수집 트리거"""
        if source not in self.sources:
            return {"success": False, "message": f"알 수 없는 소스: {source}"}

        if not self.collection_enabled and not force:
            return {"success": False, "message": "수집이 비활성화되어 있습니다."}

        if not self.sources[source]["enabled"] and not force:
            return {"success": False, "message": f"{source} 수집이 비활성화되어 있습니다."}

        # 실제 수집은 각 collector에서 수행
        self.sources[source]["last_collection"] = datetime.now().isoformat()
        self._save_collection_config()

        return {
            "success": True,
            "message": f"{source} 수집이 트리거되었습니다.",
            "source": source,
            "triggered_at": self.sources[source]["last_collection"],
        }

    def update_source_status(self, source: str, status: Dict[str, Any]):
        """소스 상태 업데이트"""
        if source in self.sources:
            self.sources[source].update(status)
            if "last_collection" in status:
                self.config[f"{source}_last_collection"] = status["last_collection"]
            self._save_collection_config()
