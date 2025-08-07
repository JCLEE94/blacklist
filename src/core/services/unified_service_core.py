#!/usr/bin/env python3
"""
통합 블랙리스트 관리 서비스 - 핵심 클래스
모든 블랙리스트 운영을 하나로 통합한 서비스의 핵심 기능
"""

import asyncio
import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..blacklist_unified import UnifiedBlacklistManager
from ..collection_manager import CollectionManager
from ..container import get_container
from ..regtech_simple_collector import RegtechSimpleCollector as RegtechCollector
from .collection_service import CollectionServiceMixin
from .statistics_service import StatisticsServiceMixin

logger = logging.getLogger(__name__)


@dataclass
class ServiceHealth:
    status: str
    components: Dict[str, str]
    timestamp: datetime
    version: str


class UnifiedBlacklistService(CollectionServiceMixin, StatisticsServiceMixin):
    """
    통합 블랙리스트 서비스 - 모든 기능을 하나로 통합
    REGTECH, SECUDIUM 수집부터 API 서빙까지 단일 서비스로 처리
    """

    def __init__(self):
        self.container = get_container()
        self.logger = logging.getLogger(__name__)

        # 서비스 상태
        self._running = False
        self._components = {}

        # 통합 설정
        self.config = {
            "regtech_enabled": os.getenv("REGTECH_ENABLED", "true").lower() == "true",
            "auto_collection": os.getenv("AUTO_COLLECTION", "true").lower() == "true",
            "collection_interval": int(os.getenv("COLLECTION_INTERVAL", 3600)),
            "service_name": "blacklist-unified",
            "version": "3.0.3-cicd-test",
        }

        # 수집 로그 저장 (메모리, 최대 1000개)
        self.collection_logs = []
        self.max_logs = 1000

        # 수집 상태 관리 (메모리) - 기본값 False
        self.collection_enabled = False
        self.daily_collection_enabled = False

        # Initialize core services immediately
        try:
            self.blacklist_manager = self.container.resolve("blacklist_manager")
            self.cache = self.container.resolve("cache_manager")
            # Try to get collection_manager
            try:
                self.collection_manager = self.container.resolve("collection_manager")
                # CollectionManager의 상태와 동기화
                if self.collection_manager:
                    self.collection_enabled = self.collection_manager.collection_enabled
            except Exception as e:
                self.logger.warning(f"Collection Manager not available: {e}")
                self.collection_manager = None
        except Exception as e:
            self.logger.error(f"Failed to initialize core services: {e}")
            self.blacklist_manager = None
            self.cache = None
            self.collection_manager = None

        # 로그 테이블 초기화
        self._ensure_log_table()

        # 데이터베이스에서 기존 로그 로드
        try:
            existing_logs = self._load_logs_from_db(100)
            self.collection_logs = existing_logs
        except Exception as e:
            self.logger.warning(f"Failed to load existing logs: {e}")

        # Mark as running for basic health checks
        self._running = True

        # 최초 실행 시 자동 수집 수행 (즉시 실행)
        if (
            self.collection_manager
            and self.collection_manager.is_initial_collection_needed()
        ):
            self.logger.info("🔥 최초 실행 - 즉시 수집 시작")
            self._perform_initial_collection_now()

    def _perform_initial_collection_now(self):
        """최초 실행 - 수집은 수동으로 진행"""
        try:
            self.logger.info("🔥 최초 실행 감지 - 수집은 수동으로 활성화해주세요")
            self.logger.info(
                "📋 웹 UI (http://localhost:8541)에서 수집 활성화 후 데이터 수집을 시작할 수 있습니다"
            )
            self.logger.info(
                "🔧 환경 변수 REGTECH_USERNAME, REGTECH_PASSWORD, SECUDIUM_USERNAME, SECUDIUM_PASSWORD를 설정하세요"
            )

            # 수집은 활성화하지 않음 - 수동 제어
            self.logger.info("⚠️ 자동 수집이 비활성화되었습니다. 수동으로 수집을 시작하세요.")

            # 완료 표시 (자동 수집 시도 방지)
            self.collection_manager.mark_initial_collection_done()
            self.logger.info("✅ 초기 설정 완료 - 수집은 수동으로 진행하세요")

        except Exception as e:
            self.logger.error(f"초기 설정 오류: {e}")
            # 오류가 있어도 완료 표시 (무한 루프 방지)
            self.collection_manager.mark_initial_collection_done()

    async def start(self) -> None:
        """통합 서비스 시작"""
        self.logger.info("🚀 통합 블랙리스트 서비스 시작...")

        try:
            # 1. 의존성 컨테이너 초기화
            await self._initialize_container()

            # 2. 핵심 컴포넌트 초기화
            await self._initialize_components()

            # 3. 백그라운드 작업 시작
            if self.config["auto_collection"]:
                await self._start_background_tasks()

            self._running = True
            self.logger.info("✅ 통합 블랙리스트 서비스 시작 완료")

        except Exception as e:
            self.logger.error(f"❌ 서비스 시작 실패: {e}")
            raise

    async def stop(self) -> None:
        """통합 서비스 정지"""
        self.logger.info("🛑 통합 블랙리스트 서비스 정지...")

        # 백그라운드 작업 정지
        if hasattr(self, "_background_tasks"):
            for task in self._background_tasks:
                task.cancel()

        # 컴포넌트 정리
        await self._cleanup_components()

        self._running = False
        self.logger.info("✅ 통합 블랙리스트 서비스 정지 완료")

    async def _initialize_container(self):
        """의존성 컨테이너 초기화"""
        self.logger.info("📦 의존성 컨테이너 초기화 중...")

        # Already initialized in __init__, just verify they exist
        if not self.blacklist_manager:
            self.logger.error("blacklist_manager not initialized")
            raise RuntimeError("Required service 'blacklist_manager' not available")

        if not self.cache:
            self.logger.error("cache not initialized")
            raise RuntimeError("Required service 'cache' not available")

        self.logger.info("✅ 의존성 컨테이너 초기화 완료")

    async def _initialize_components(self):
        """핵심 컴포넌트 초기화"""
        self.logger.info("⚙️ 핵심 컴포넌트 초기화 중...")

        # REGTECH 수집기 초기화
        if self.config["regtech_enabled"]:
            self._components["regtech"] = RegtechCollector("data", self.cache)
            self.logger.info("✅ REGTECH 수집기 초기화 완료")

        self.logger.info("✅ 모든 컴포넌트 초기화 완료")

    async def _start_background_tasks(self):
        """백그라운드 자동 수집 작업 시작"""
        self.logger.info("🔄 자동 수집 작업 시작...")

        self._background_tasks = []

        # 주기적 수집 작업
        collection_task = asyncio.create_task(self._periodic_collection())
        self._background_tasks.append(collection_task)

        self.logger.info("✅ 백그라운드 작업 시작 완료")

    async def _periodic_collection(self):
        """주기적 데이터 수집 - 3개월 범위의 데이터 자동 수집"""
        while self._running:
            try:
                # 일일 자동 수집이 활성화된 경우만 실행
                if self.collection_manager and hasattr(
                    self.collection_manager, "daily_collection_enabled"
                ):
                    if self.collection_manager.daily_collection_enabled:
                        # 마지막 수집이 오늘이 아니면 수집 실행
                        last_collection = self.collection_manager.last_daily_collection
                        if not last_collection or not last_collection.startswith(
                            datetime.now().strftime("%Y-%m-%d")
                        ):
                            self.logger.info("🔄 3개월 범위 자동 수집 시작...")

                            # 3개월 전부터 오늘까지 수집
                            today = datetime.now()
                            three_months_ago = today - timedelta(days=90)

                            # 날짜 범위 설정 (3개월 전 ~ 오늘)
                            start_date = three_months_ago.strftime("%Y%m%d")
                            end_date = today.strftime("%Y%m%d")

                            self.logger.info(
                                f"📅 수집 기간: {three_months_ago.strftime('%Y-%m-%d')} ~ {today.strftime('%Y-%m-%d')}"
                            )

                # 다음 체크까지 대기 (1시간)
                await asyncio.sleep(3600)

            except Exception as e:
                self.logger.error(f"❌ 주기적 수집 오류: {e}")
                await asyncio.sleep(60)  # 오류 시 1분 후 재시도

    async def _cleanup_components(self):
        """컴포넌트 정리"""
        self.logger.info("🧹 컴포넌트 정리 중...")

        for name, component in self._components.items():
            try:
                if hasattr(component, "cleanup"):
                    await component.cleanup()
            except Exception as e:
                self.logger.warning(f"컴포넌트 {name} 정리 중 오류: {e}")

    def _ensure_log_table(self):
        """수집 로그 테이블 생성 확인"""
        try:
            import sqlite3

            db_path = "/app/instance/blacklist.db"
            if not os.path.exists(os.path.dirname(db_path)):
                os.makedirs(os.path.dirname(db_path), exist_ok=True)

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS collection_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.warning(f"Failed to ensure log table: {e}")

    def _load_logs_from_db(self, limit: int = 100) -> List[Dict]:
        """데이터베이스에서 로그 로드"""
        try:
            import json
            import sqlite3

            db_path = "/app/instance/blacklist.db"
            if not os.path.exists(db_path):
                return []

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT timestamp, source, action, details FROM collection_logs ORDER BY id DESC LIMIT ?",
                (limit,),
            )

            logs = []
            for row in cursor.fetchall():
                log_entry = {
                    "timestamp": row[0],
                    "source": row[1],
                    "action": row[2],
                    "details": json.loads(row[3]) if row[3] else {},
                    "message": f"[{row[1]}] {row[2]}",
                }
                logs.append(log_entry)

            conn.close()
            return logs

        except Exception as e:
            self.logger.warning(f"Failed to load logs from database: {e}")
            return []

    def add_collection_log(
        self, source: str, action: str, details: Optional[Dict] = None
    ):
        """수집 로그 추가 (메모리 + 데이터베이스)"""
        try:
            timestamp = datetime.now().isoformat()
            log_entry = {
                "timestamp": timestamp,
                "source": source,
                "action": action,
                "details": details or {},
                "message": f"[{source}] {action}",
            }

            # 메모리에 추가
            self.collection_logs.insert(0, log_entry)  # 최신 로그를 앞에 추가

            # 최대 개수 제한
            if len(self.collection_logs) > self.max_logs:
                self.collection_logs = self.collection_logs[: self.max_logs]

            # 데이터베이스에 저장
            self._save_log_to_db(log_entry)

        except Exception as e:
            self.logger.warning(f"Failed to add collection log: {e}")

    def _save_log_to_db(self, log_entry: Dict):
        """로그를 데이터베이스에 저장"""
        try:
            import json
            import sqlite3

            db_path = "/app/instance/blacklist.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO collection_logs (timestamp, source, action, details) VALUES (?, ?, ?, ?)",
                (
                    log_entry["timestamp"],
                    log_entry["source"],
                    log_entry["action"],
                    json.dumps(log_entry["details"]),
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.warning(f"Failed to save log to database: {e}")

    def get_collection_logs(self, limit: int = 50) -> List[Dict]:
        """수집 로그 조회"""
        try:
            # 메모리에서 최신 로그 반환
            return self.collection_logs[:limit]
        except Exception as e:
            self.logger.warning(f"Failed to get collection logs: {e}")
            return []

    def is_running(self) -> bool:
        """서비스 실행 상태 확인"""
        return self._running

    def get_system_health(self) -> Dict[str, Any]:
        """시스템 상태 정보 조회"""
        try:
            if not self.blacklist_manager:
                return {
                    "status": "error",
                    "message": "Blacklist manager not available",
                    "total_ips": 0,
                    "active_ips": 0,
                    "regtech_count": 0,
                    "secudium_count": 0,
                    "public_count": 0,
                }

            # 블랙리스트 매니저에서 통계 조회
            stats = self.blacklist_manager.get_system_stats()

            return {
                "status": "healthy",
                "total_ips": stats.get("total_ips", 0),
                "active_ips": stats.get("active_ips", 0),
                "regtech_count": stats.get("regtech_count", 0),
                "secudium_count": stats.get("secudium_count", 0),
                "public_count": stats.get("public_count", 0),
                "last_update": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Failed to get system health: {e}")
            return {
                "status": "error",
                "message": str(e),
                "total_ips": 0,
                "active_ips": 0,
                "regtech_count": 0,
                "secudium_count": 0,
                "public_count": 0,
            }

    def get_system_stats(self) -> Dict[str, Any]:
        """시스템 통계 조회 (get_system_health의 별칭)"""
        return self.get_system_health()

    def get_active_blacklist_ips(self) -> List[str]:
        """활성 블랙리스트 IP 목록 조회"""
        try:
            if not self.blacklist_manager:
                return []

            # 블랙리스트 매니저에서 활성 IP 목록 조회
            ips, _ = self.blacklist_manager.get_active_ips()
            return ips

        except Exception as e:
            self.logger.error(f"Failed to get active blacklist IPs: {e}")
            return []

    def clear_all_database_data(self) -> Dict[str, Any]:
        """모든 데이터베이스 데이터 클리어"""
        try:
            if not self.blacklist_manager:
                return {"success": False, "error": "Blacklist manager not available"}

            # 블랙리스트 매니저를 통해 데이터 클리어
            result = self.blacklist_manager.clear_all_data()

            # 성공시 로그 추가
            if result.get("success"):
                self.add_collection_log(
                    "system",
                    "database_cleared",
                    {"timestamp": datetime.now().isoformat()},
                )

            return result

        except Exception as e:
            self.logger.error(f"Failed to clear database: {e}")
            return {"success": False, "error": str(e)}

    def get_health(self) -> ServiceHealth:
        """서비스 헬스 체크"""
        component_status = {}

        for name, component in self._components.items():
            try:
                # 각 컴포넌트의 상태 확인
                if hasattr(component, "get_health"):
                    component_status[name] = component.get_health()
                else:
                    component_status[name] = "healthy"
            except Exception as e:
                component_status[name] = f"error: {e}"

        # 전체 상태 결정
        overall_status = "healthy" if self._running else "stopped"
        if any("error" in status for status in component_status.values()):
            overall_status = "degraded"

        return ServiceHealth(
            status=overall_status,
            components=component_status,
            timestamp=datetime.now(),
            version=self.config["version"],
        )

    async def get_active_blacklist(self, format_type: str = "json") -> Dict[str, Any]:
        """활성 블랙리스트 조회 - 성능 최적화 버전"""
        try:
            # 성능 캐시 키 생성
            cache_key = f"active_blacklist_{format_type}_v2"

            # 캐시에서 먼저 확인
            if self.cache:
                try:
                    cached_result = self.cache.get(cache_key)
                    if cached_result:
                        return cached_result
                except Exception:
                    pass

            # 활성 아이피 조회
            active_ips = self.get_active_blacklist_ips()

            if format_type == "fortigate":
                result = self.format_for_fortigate(active_ips)
            elif format_type == "text":
                result = {
                    "success": True,
                    "ips": "\n".join(active_ips),
                    "count": len(active_ips),
                    "timestamp": datetime.now().isoformat(),
                }
            else:  # json (default)
                result = {
                    "success": True,
                    "ips": active_ips,
                    "count": len(active_ips),
                    "timestamp": datetime.now().isoformat(),
                }

            # 캐시에 저장 (5분)
            if self.cache:
                try:
                    self.cache.set(cache_key, result, ttl=300)
                except Exception:
                    pass

            return result
        except Exception as e:
            self.logger.error(f"활성 블랙리스트 조회 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def initialize_database_tables(self) -> Dict[str, Any]:
        """데이터베이스 테이블 강제 초기화"""
        try:
            # Use blacklist_manager's database path
            if hasattr(self.blacklist_manager, "db_path"):
                db_path = self.blacklist_manager.db_path
            else:
                db_path = os.path.join(
                    "/app" if os.path.exists("/app") else ".", "instance/blacklist.db"
                )

            self.logger.info(f"Initializing database tables at: {db_path}")

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Create blacklist_ip table if not exists
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS blacklist_ip (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    detection_date TEXT,
                    attack_type TEXT,
                    country TEXT,
                    source TEXT,
                    is_active INTEGER DEFAULT 1,
                    updated_at TEXT
                )
                """
            )

            # Create collection_logs table if not exists
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS collection_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

            conn.commit()
            conn.close()

            return {
                "success": True,
                "message": "Database tables initialized successfully",
                "db_path": db_path,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def clear_collection_logs(self):
        """수집 로그 클리어"""
        try:
            self.collection_logs.clear()
            # 데이터베이스에서도 삭제
            if self.blacklist_manager and hasattr(self.blacklist_manager, "db_path"):
                conn = sqlite3.connect(self.blacklist_manager.db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM collection_logs")
                conn.commit()
                conn.close()

            self.logger.info("수집 로그가 클리어되었습니다")
        except Exception as e:
            self.logger.error(f"로그 클리어 실패: {e}")
