#!/usr/bin/env python3
"""
통합 블랙리스트 서비스 - 수집 관련 기능
데이터 수집, 트리거, 활성화/비활성화 등의 수집 전용 기능
"""

import asyncio
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import Optional


# Collection service mixin for UnifiedBlacklistService
class CollectionServiceMixin:
    """
    수집 관련 기능을 제공하는 믹스인 클래스
    UnifiedBlacklistService에서 사용됨
    """

    async def collect_all_data(self, force: bool = False) -> Dict[str, Any]:
        """모든 소스에서 데이터 수집"""
        self.logger.info("🔄 전체 데이터 수집 시작...")

        results = {}
        total_success = 0
        total_failed = 0

        # REGTECH 수집
        if "regtech" in self._components:
            try:
                regtech_result = await self._collect_regtech_data(force)
                results["regtech"] = regtech_result
                if regtech_result.get("success"):
                    total_success += 1
                else:
                    total_failed += 1
            except Exception as e:
                self.logger.error(f"REGTECH 수집 실패: {e}")
                results["regtech"] = {"success": False, "error": str(e)}
                total_failed += 1

        # SECUDIUM 수집
        if "secudium" in self._components:
            try:
                secudium_result = await self._collect_secudium_data(force)
                results["secudium"] = secudium_result
                if secudium_result.get("success"):
                    total_success += 1
                else:
                    total_failed += 1
            except Exception as e:
                self.logger.error(f"SECUDIUM 수집 실패: {e}")
                results["secudium"] = {"success": False, "error": str(e)}
                total_failed += 1

        return {
            "success": total_success > 0,
            "results": results,
            "summary": {
                "successful_sources": total_success,
                "failed_sources": total_failed,
                "timestamp": datetime.now().isoformat(),
            },
        }

    async def _collect_regtech_data(self, force: bool = False) -> Dict[str, Any]:
        """REGTECH 데이터 수집"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._components["regtech"].auto_collect
        )

    async def _collect_regtech_data_with_date(
        self, start_date: str, end_date: str
    ) -> Dict[str, Any]:
        """REGTECH 데이터 수집 (날짜 지정)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._components["regtech"].collect_from_web,
            5,  # max_pages
            100,  # page_size
            1,  # parallel_workers
            start_date,
            end_date,
        )

    async def _collect_secudium_data(self, force: bool = False) -> Dict[str, Any]:
        """SECUDIUM 데이터 수집"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._components["secudium"].auto_collect
        )

    def search_ip(self, ip: str) -> Dict[str, Any]:
        """통합 IP 검색"""
        try:
            # 블랙리스트 매니저를 통한 통합 검색
            result = self.blacklist_manager.search_ip(ip)
            return {
                "success": True,
                "ip": ip,
                "result": result,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"IP 검색 실패 ({ip}): {e}")
            return {
                "success": False,
                "ip": ip,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def enable_collection(self) -> Dict[str, Any]:
        """수집 활성화"""
        try:
            # 기존 데이터 정리 후 수집 활성화
            clear_result = self.clear_all_database_data()

            self.collection_enabled = True
            self.daily_collection_enabled = True

            # CollectionManager와 동기화
            if self.collection_manager:
                self.collection_manager.collection_enabled = True

            # 로그 남기기
            self.add_collection_log(
                source="system",
                action="collection_enabled",
                details={"clear_result": clear_result},
            )

            return {
                "success": True,
                "message": "수집이 활성화되었습니다. 기존 데이터가 정리되었습니다.",
                "clear_result": clear_result,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"수집 활성화 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def disable_collection(self) -> Dict[str, Any]:
        """수집 비활성화"""
        try:
            self.collection_enabled = False
            self.daily_collection_enabled = False

            # CollectionManager와 동기화
            if self.collection_manager:
                self.collection_manager.collection_enabled = False

            # 로그 남기기
            self.add_collection_log(source="system", action="collection_disabled")

            return {
                "success": True,
                "message": "수집이 비활성화되었습니다.",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"수집 비활성화 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def get_collection_status(self) -> Dict[str, Any]:
        """수집 상태 조회"""
        try:
            # 기본 상태 정보
            status = {
                "collection_enabled": self.collection_enabled,
                "daily_collection_enabled": self.daily_collection_enabled,
                "last_collection_time": None,
                "next_collection_time": None,
                "sources": {},
                "recent_logs": [],
                "timestamp": datetime.now().isoformat(),
            }

            # CollectionManager 상태도 확인
            if self.collection_manager:
                status["collection_manager_status"] = {
                    "enabled": self.collection_manager.collection_enabled,
                    "last_run": getattr(self.collection_manager, "last_run", None),
                }

            # 최근 로그 추가
            try:
                status["recent_logs"] = self.get_collection_logs(limit=5)
            except Exception:
                status["recent_logs"] = []

            # 소스 상태 확인
            for source in ["regtech", "secudium"]:
                status["sources"][source] = {
                    "available": source in self._components,
                    "last_success": None,
                    "error_count": 0,
                }

            return status
        except Exception as e:
            self.logger.error(f"수집 상태 조회 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def trigger_collection(self, source: str = "all") -> str:
        """수집 트리거 (비동기 실행)"""
        if source == "all":
            asyncio.create_task(self.collect_all_data(force=True))
            return "전체 수집이 시작되었습니다."
        elif source == "regtech" and "regtech" in self._components:
            asyncio.create_task(self._collect_regtech_data(force=True))
            return "REGTECH 수집이 시작되었습니다."
        elif source == "secudium" and "secudium" in self._components:
            asyncio.create_task(self._collect_secudium_data(force=True))
            return "SECUDIUM 수집이 시작되었습니다."
        else:
            return f"알 수 없는 소스: {source}"

    def trigger_regtech_collection(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        force: bool = False,
    ) -> dict:
        """REGTECH 수집 트리거 (개선된 버전)"""
        try:
            # 수집이 비활성화된 경우 확인
            if not force and not self.collection_enabled:
                return {
                    "success": False,
                    "message": "수집이 비활성화되어 있습니다. 먼저 수집을 활성화해주세요.",
                    "collection_enabled": False,
                }

            # REGTECH 컴포넌트 확인
            if "regtech" not in self._components:
                return {
                    "success": False,
                    "message": "REGTECH 컴포넌트가 사용할 수 없습니다.",
                    "component_available": False,
                }

            self._components["regtech"]

            # 날짜 파라미터 처리
            if start_date or end_date:
                # 날짜가 지정된 경우
                if not start_date:
                    start_date = (datetime.now() - timedelta(days=7)).strftime(
                        "%Y-%m-%d"
                    )
                if not end_date:
                    end_date = datetime.now().strftime("%Y-%m-%d")

                # 비동기 작업으로 처리
                asyncio.create_task(
                    self._collect_regtech_data_with_date(start_date, end_date)
                )

                # 로그 남기기
                self.add_collection_log(
                    source="regtech",
                    action="manual_trigger_with_dates",
                    details={
                        "start_date": start_date,
                        "end_date": end_date,
                        "force": force,
                    },
                )

                return {
                    "success": True,
                    "message": f"REGTECH 수집이 시작되었습니다 ({start_date} ~ {end_date})",
                    "start_date": start_date,
                    "end_date": end_date,
                    "triggered_at": datetime.now().isoformat(),
                }
            else:
                # 기본 수집
                asyncio.create_task(self._collect_regtech_data(force=force))

                # 로그 남기기
                self.add_collection_log(
                    source="regtech", action="manual_trigger", details={"force": force}
                )

                return {
                    "success": True,
                    "message": "REGTECH 수집이 시작되었습니다",
                    "triggered_at": datetime.now().isoformat(),
                }
        except Exception as e:
            self.logger.error(f"REGTECH 수집 트리거 실패: {e}")
            return {
                "success": False,
                "message": f"REGTECH 수집 트리거 실패: {str(e)}",
                "error": str(e),
            }

    def trigger_secudium_collection(self) -> dict:
        """SECUDIUM 수집 트리거"""
        try:
            # 수집이 비활성화된 경우 확인
            if not self.collection_enabled:
                return {
                    "success": False,
                    "message": "수집이 비활성화되어 있습니다. 먼저 수집을 활성화해주세요.",
                    "collection_enabled": False,
                }

            # SECUDIUM 컴포넌트 확인
            if "secudium" not in self._components:
                return {
                    "success": False,
                    "message": "SECUDIUM 컴포넌트가 사용할 수 없습니다.",
                    "component_available": False,
                }

            # 비동기 수집 시작
            asyncio.create_task(self._collect_secudium_data(force=True))

            # 로그 남기기
            self.add_collection_log(source="secudium", action="manual_trigger")

            return {
                "success": True,
                "message": "SECUDIUM 수집이 시작되었습니다",
                "triggered_at": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"SECUDIUM 수집 트리거 실패: {e}")
            return {
                "success": False,
                "message": f"SECUDIUM 수집 트리거 실패: {str(e)}",
                "error": str(e),
            }

    def get_missing_dates_for_collection(self, source: str, days_back: int) -> list:
        """수집되지 않은 날짜 목록 조회"""
        try:
            missing_dates = []
            current_date = datetime.now()

            for i in range(days_back):
                check_date = current_date - timedelta(days=i)
                date_str = check_date.strftime("%Y-%m-%d")

                # 해당 날짜의 데이터가 있는지 확인
                if not self._has_data_for_date(source, date_str):
                    missing_dates.append(date_str)

            return missing_dates
        except Exception as e:
            self.logger.error(f"누락 날짜 조회 실패: {e}")
            return []

    def _has_data_for_date(self, source: str, date_str: str) -> bool:
        """특정 날짜에 데이터가 있는지 확인"""
        try:
            if not self.blacklist_manager:
                return False

            # 간단한 데이터 존재 확인
            # 실제 구현에서는 데이터베이스 쿼리 필요
            return False  # 임시로 False 반환
        except Exception:
            return False
