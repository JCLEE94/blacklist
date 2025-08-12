#!/usr/bin/env python3
"""
핵심 시스템 운영 기능

서비스 초기화, 상태 관리, 헬스 체크 등 핵심 운영 기능을 제공합니다.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict

from ..regtech_simple_collector import RegtechSimpleCollector as RegtechCollector

logger = logging.getLogger(__name__)


@dataclass
class ServiceHealth:
    status: str
    components: Dict[str, str]
    timestamp: datetime
    version: str


class CoreOperationsMixin:
    """핵심 시스템 운영 기능을 제공하는 믹스인"""

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
            self.logger.error("❌ 서비스 시작 실패: {e}")
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
            self._components["regtech"] = RegtechCollector("data")
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
                            three_months_ago.strftime("%Y%m%d")
                            today.strftime("%Y%m%d")

                            self.logger.info(
                                "📅 수집 기간: {three_months_ago.strftime('%Y-%m-%d')} ~ {today.strftime('%Y-%m-%d')}"
                            )

                # 다음 체크까지 대기 (1시간)
                await asyncio.sleep(3600)

            except Exception as e:
                self.logger.error("❌ 주기적 수집 오류: {e}")
                await asyncio.sleep(60)  # 오류 시 1분 후 재시도

    async def _cleanup_components(self):
        """컴포넌트 정리"""
        self.logger.info("🧹 컴포넌트 정리 중...")

        for name, component in self._components.items():
            try:
                if hasattr(component, "cleanup"):
                    await component.cleanup()
            except Exception as e:
                self.logger.warning("컴포넌트 {name} 정리 중 오류: {e}")

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
            self.logger.error("Failed to get system health: {e}")
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

    def get_active_blacklist_ips(self) -> list[str]:
        """활성 블랙리스트 IP 목록 조회"""
        try:
            if not self.blacklist_manager:
                return []

            # 블랙리스트 매니저에서 활성 IP 목록 조회
            result = self.blacklist_manager.get_active_ips()

            # 결과가 튜플인 경우와 리스트인 경우 모두 처리
            if isinstance(result, tuple):
                ips = result[0] if result else []
            else:
                ips = result if result else []

            return ips

        except Exception as e:
            self.logger.error("Failed to get active blacklist IPs: {e}")
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
            self.logger.error("Failed to clear database: {e}")
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
                component_status[name] = "error: {e}"

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
            cache_key = "active_blacklist_{format_type}_v2"

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
            self.logger.error("활성 블랙리스트 조회 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

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
            self.logger.error("초기 설정 오류: {e}")
            # 오류가 있어도 완료 표시 (무한 루프 방지)
            self.collection_manager.mark_initial_collection_done()
