"""
수집 상태 관리 모듈 (< 200 lines)
상태 조회, 로그 관리, 비밀 날짜 처리 등
"""

from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Dict


class CollectionStatusMixin:
    """수집 상태 관리 믹스인"""

    def get_collection_status(self) -> Dict[str, Any]:
        """수집 상태 조회"""
        try:
            # 기본 상태 정보
            status = {
                "collection_enabled": getattr(self, "collection_enabled", False),
                "daily_collection_enabled": getattr(
                    self, "daily_collection_enabled", False
                ),
                "last_collection_time": None,
                "next_collection_time": None,
                "sources": {},
                "recent_logs": [],
                "timestamp": datetime.now().isoformat(),
            }

            # CollectionManager 상태도 확인
            if hasattr(self, "collection_manager") and self.collection_manager:
                status["collection_manager_status"] = {
                    "enabled": self.collection_manager.collection_enabled,
                    "last_run": getattr(self.collection_manager, "last_run", None),
                }

            # 최근 로그 추가
            try:
                if hasattr(self, "get_collection_logs"):
                    status["recent_logs"] = self.get_collection_logs(limit=5)
            except Exception as e:
                status["recent_logs"] = []

            # 소스 상태 확인
            if hasattr(self, "_components"):
                for source in ["regtech", "secudium"]:
                    status["sources"][source] = {
                        "available": source in self._components,
                        "last_success": None,
                        "error_count": 0,
                    }

            return status
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"수집 상태 조회 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
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
            if hasattr(self, "logger"):
                self.logger.error(f"누락 날짜 조회 실패: {e}")
            return []

    def _has_data_for_date(self, source: str, date_str: str) -> bool:
        """특정 날짜에 데이터가 있는지 확인"""
        try:
            if not hasattr(self, "blacklist_manager") or not self.blacklist_manager:
                return False

            # 간단한 데이터 존재 확인
            # 실제 구현에서는 데이터베이스 쿼리 필요
            return False  # 임시로 False 반환
        except Exception as e:
            return False

    def get_collection_summary(self) -> Dict[str, Any]:
        """수집 요약 정보"""
        try:
            status = self.get_collection_status()

            # 요약 통계 계산
            total_sources = len(status.get("sources", {}))
            available_sources = sum(
                1
                for source_data in status.get("sources", {}).values()
                if source_data.get("available", False)
            )

            return {
                "collection_enabled": status.get("collection_enabled", False),
                "total_sources": total_sources,
                "available_sources": available_sources,
                "recent_activity": len(status.get("recent_logs", [])),
                "last_update": status.get("timestamp"),
                "health_status": "healthy" if available_sources > 0 else "warning",
            }
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"수집 요약 조회 실패: {e}")
            return {
                "collection_enabled": False,
                "total_sources": 0,
                "available_sources": 0,
                "recent_activity": 0,
                "health_status": "error",
                "error": str(e),
            }
