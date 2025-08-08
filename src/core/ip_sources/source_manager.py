"""
IP 소스 관리자
여러 IP 소스들을 통합적으로 관리하고 데이터를 수집
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..database import DatabaseManager

from .base_source import BaseIPSource, IPEntry, SourceConfig
from .source_registry import registry

logger = logging.getLogger(__name__)


class IPSourceManager:
    """다중 IP 소스 관리자"""

    def __init__(
        self, db_manager: DatabaseManager, config_file: str = "config/sources.json"
    ):
        self.db_manager = db_manager
        self.config_file = config_file
        self.sources: Dict[str, BaseIPSource] = {}
        self.update_stats = {}

        # 레지스트리 초기화
        registry.auto_discover_sources()

        # 소스 설정 로드
        self.load_sources_config()

    def load_sources_config(self):
        """소스 설정 파일 로드"""
        config_path = Path(self.config_file)

        if not config_path.exists():
            # 기본 설정 생성
            default_config = {
                "sources": {
                    "secudium": {
                        "enabled": True,
                        "priority": 1,
                        "update_interval": 3600,
                        "settings": {
                            "username": "${BLACKLIST_USERNAME}",
                            "password": "${BLACKLIST_PASSWORD}",
                            "api_url": "https://secudium.co.kr/api/blacklist",
                        },
                    }
                }
            }

            # 디렉토리 생성
            config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)

            logger.info(f"Created default sources config: {config_path}")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            # 소스 인스턴스 생성
            for source_name, source_config in config_data.get("sources", {}).items():
                try:
                    self.add_source(source_name, source_config)
                except Exception as e:
                    logger.error(f"Failed to add source {source_name}: {e}")

            logger.info(f"Loaded {len(self.sources)} IP sources from config")

        except Exception as e:
            logger.error(f"Failed to load sources config: {e}")

    def add_source(self, name: str, config_data: Dict[str, Any]):
        """
        새로운 소스 추가

        Args:
            name: 소스 이름
            config_data: 소스 설정 데이터
        """
        try:
            # 환경변수 치환
            settings = self._substitute_env_vars(config_data.get("settings", {}))

            config = SourceConfig(
                name=name,
                enabled=config_data.get("enabled", True),
                priority=config_data.get("priority", 5),
                update_interval=config_data.get("update_interval", 3600),
                settings=settings,
            )

            # 레지스트리에서 소스 클래스 가져오기
            source_class = registry.get_source_class(name)
            source_instance = source_class(config)

            # 설정 유효성 검사
            if not source_instance.validate_config():
                raise ValueError(f"Invalid configuration for source {name}")

            self.sources[name] = source_instance
            logger.info(f"Added IP source: {name}")

        except Exception as e:
            logger.error(f"Failed to add source {name}: {e}")
            raise

    def _substitute_env_vars(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """환경변수 치환"""
        import os
        import re

        def substitute_value(value):
            if isinstance(value, str):
                # ${VAR_NAME} 패턴 치환
                def replace_var(match):
                    var_name = match.group(1)
                    return os.environ.get(var_name, match.group(0))

                return re.sub(r"\$\{([^}]+)\}", replace_var, value)
            elif isinstance(value, dict):
                return {k: substitute_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute_value(item) for item in value]
            else:
                return value

        return substitute_value(settings)

    def update_all_sources(self, max_workers: int = 5) -> Dict[str, Any]:
        """
        모든 소스에서 데이터 업데이트

        Args:
            max_workers: 최대 동시 실행 스레드 수

        Returns:
            Dict: 전체 업데이트 결과
        """
        start_time = datetime.utcnow()
        results = {}
        total_entries = 0

        logger.info(f"Starting update for {len(self.sources)} sources")

        # 우선순위별로 소스 정렬
        sorted_sources = sorted(
            self.sources.items(), key=lambda x: x[1].config.priority
        )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 비동기 작업 제출
            future_to_source = {
                executor.submit(source.update): name for name, source in sorted_sources
            }

            # 결과 수집
            for future in as_completed(future_to_source):
                source_name = future_to_source[future]
                try:
                    result = future.result()
                    results[source_name] = result

                    # 성공한 경우 데이터베이스에 저장
                    if result["status"] == "success":
                        self._save_entries_to_db(result["entries"], source_name)
                        total_entries += result["entries_count"]

                except Exception as e:
                    logger.error(f"Error updating source {source_name}: {e}")
                    results[source_name] = {
                        "status": "error",
                        "error": str(e),
                        "source": source_name,
                    }

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        # 전체 결과 정리
        summary = {
            "status": "completed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration,
            "total_sources": len(self.sources),
            "successful_sources": len(
                [r for r in results.values() if r["status"] == "success"]
            ),
            "total_entries": total_entries,
            "results": results,
        }

        # 통계 업데이트
        self.update_stats = summary

        logger.info(
            f"Update completed: {summary['successful_sources']}/{summary['total_sources']} sources, {total_entries} entries"
        )

        return summary

    def _save_entries_to_db(self, entries: List[IPEntry], source_name: str):
        """IP 엔트리들을 데이터베이스에 저장"""
        try:
            # 기존 데이터베이스 스키마와 호환되도록 변환
            for entry in entries:
                self.db_manager.add_ip_to_blacklist(
                    ip_address=entry.ip_address,
                    source=source_name,
                    category=entry.category,
                    confidence=entry.confidence,
                    detection_date=entry.detection_date,
                    metadata=entry.metadata,
                )

            logger.info(f"Saved {len(entries)} entries from {source_name} to database")

        except Exception as e:
            logger.error(f"Failed to save entries from {source_name}: {e}")

    def get_source_status(self) -> Dict[str, Any]:
        """모든 소스의 상태 정보 반환"""
        status = {}

        for name, source in self.sources.items():
            try:
                health = source.health_check()
                metadata = source.get_metadata()

                status[name] = {
                    **health,
                    **metadata,
                    "priority": source.config.priority,
                }
            except Exception as e:
                status[name] = {"healthy": False, "error": str(e), "source": name}

        return status

    def enable_source(self, source_name: str):
        """소스 활성화"""
        if source_name in self.sources:
            self.sources[source_name].config.enabled = True
            logger.info(f"Enabled source: {source_name}")

    def disable_source(self, source_name: str):
        """소스 비활성화"""
        if source_name in self.sources:
            self.sources[source_name].config.enabled = False
            logger.info(f"Disabled source: {source_name}")

    def get_available_sources(self) -> List[str]:
        """사용 가능한 모든 소스 목록"""
        return registry.list_sources()

    def get_registry_info(self) -> Dict[str, Any]:
        """레지스트리 정보 반환"""
        return registry.get_source_info()

    def get_last_update_stats(self) -> Dict[str, Any]:
        """마지막 업데이트 통계 반환"""
        return self.update_stats or {"status": "no_updates_yet"}
