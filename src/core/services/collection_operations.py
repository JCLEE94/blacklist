"""
수집 작업 관리 모듈 (< 300 lines)
데이터 수집, 활성화/비활성화, IP 검색 등
"""

import asyncio
from datetime import datetime
from typing import Any
from typing import Dict


class CollectionOperationsMixin:
    """수집 작업 관리 믹스인"""

    def __init__(self):
        """Initialize collection operations"""
        self.status = {
            "enabled": False,
            "sources": {
                "REGTECH": {"enabled": False, "last_collection": None},
                "SECUDIUM": {"enabled": False, "last_collection": None},
            },
        }
        self.collection_enabled = False
        self.daily_collection_enabled = False

    async def collect_all_data(self, force: bool = False) -> Dict[str, Any]:
        """모든 소스에서 데이터 수집 (중복 제거 포함)"""
        self.logger.info("🔄 전체 데이터 수집 시작...")

        results = {}
        total_success = 0
        total_failed = 0
        all_collected_ips = set()  # 중복 제거를 위한 IP 집합

        # REGTECH 수집
        if "regtech" in self._components:
            try:
                regtech_result = await self._collect_regtech_data(force)
                results["regtech"] = regtech_result

                # 수집된 IP들을 중복 제거 집합에 추가
                if regtech_result.get("success") and regtech_result.get("ips"):
                    regtech_ips = set(regtech_result["ips"])
                    before_count = len(all_collected_ips)
                    all_collected_ips.update(regtech_ips)
                    after_count = len(all_collected_ips)

                    regtech_result["duplicates_removed"] = len(regtech_ips) - (
                        after_count - before_count
                    )
                    regtech_result["unique_ips"] = after_count - before_count

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

                # 수집된 IP들을 중복 제거 집합에 추가
                if secudium_result.get("success") and secudium_result.get("ips"):
                    secudium_ips = set(secudium_result["ips"])
                    before_count = len(all_collected_ips)
                    all_collected_ips.update(secudium_ips)
                    after_count = len(all_collected_ips)

                    secudium_result["duplicates_removed"] = len(secudium_ips) - (
                        after_count - before_count
                    )
                    secudium_result["unique_ips"] = after_count - before_count

                    total_success += 1
                else:
                    total_failed += 1
            except Exception as e:
                self.logger.error(f"SECUDIUM 수집 실패: {e}")
                results["secudium"] = {"success": False, "error": str(e)}
                total_failed += 1

        # 중복 제거 통계 추가
        total_duplicates = sum(
            [
                r.get("duplicates_removed", 0)
                for r in results.values()
                if isinstance(r, dict)
            ]
        )

        return {
            "success": total_success > 0,
            "results": results,
            "summary": {
                "successful_sources": total_success,
                "failed_sources": total_failed,
                "total_unique_ips": len(all_collected_ips),
                "total_duplicates_removed": total_duplicates,
                "timestamp": datetime.now().isoformat(),
            },
        }

    async def _collect_regtech_data(self, force: bool = False) -> Dict[str, Any]:
        """REGTECH 데이터 수집"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._components["regtech"].auto_collect
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
            if hasattr(self, "collection_manager") and self.collection_manager:
                self.collection_manager.collection_enabled = True

            # 로그 남기기
            if hasattr(self, "add_collection_log"):
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
            if hasattr(self, "collection_manager") and self.collection_manager:
                self.collection_manager.collection_enabled = False

            # 로그 남기기
            if hasattr(self, "add_collection_log"):
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
