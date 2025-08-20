"""
수집 트리거 관리 모듈 (< 300 lines)
수동 트리거, 스케줄링, 비동기 실행 등
"""

import asyncio
import threading
from datetime import datetime, timedelta
from typing import Optional


class CollectionTriggersMixin:
    """수집 트리거 관리 믹스인"""

    def trigger_collection(self, source: str = "all") -> str:
        """수집 트리거 (비동기 실행)"""
        try:
            # Check if there's a running event loop
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop, create task in new thread
                def run_async_task(coro):
                    """Run async task in new event loop in separate thread"""
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        new_loop.run_until_complete(coro)
                    finally:
                        new_loop.close()

                if source == "all":
                    thread = threading.Thread(
                        target=run_async_task, args=(self.collect_all_data(force=True),)
                    )
                    thread.daemon = True
                    thread.start()
                    return "전체 수집이 시작되었습니다."
                elif source == "regtech" and "regtech" in self._components:
                    thread = threading.Thread(
                        target=run_async_task,
                        args=(self._collect_regtech_data(force=True),),
                    )
                    thread.daemon = True
                    thread.start()
                    return "REGTECH 수집이 시작되었습니다."
                elif source == "secudium" and "secudium" in self._components:
                    thread = threading.Thread(
                        target=run_async_task,
                        args=(self._collect_secudium_data(force=True),),
                    )
                    thread.daemon = True
                    thread.start()
                    return "SECUDIUM 수집이 시작되었습니다."
                else:
                    return f"알 수 없는 소스: {source}"

            # If there's a running loop, create task normally
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
        except Exception as e:
            self.logger.error(f"Collection trigger error: {e}")
            return f"수집 시작 중 오류 발생: {e}"

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

            # 날짜 파라미터 처리
            if start_date or end_date:
                # 날짜가 지정된 경우
                if not start_date:
                    start_date = (datetime.now() - timedelta(days=7)).strftime(
                        "%Y-%m-%d"
                    )
                if not end_date:
                    end_date = datetime.now().strftime("%Y-%m-%d")

                # 직접 동기 수집 실행
                try:
                    result = self._components["regtech"].collect_from_web(
                        start_date=start_date.replace("-", ""),
                        end_date=end_date.replace("-", ""),
                    )
                    if not result.get("success"):
                        return {
                            "success": False,
                            "message": f"REGTECH 수집 실패: {result.get('error', 'Unknown error')}",
                        }

                    # 데이터 저장 추가!
                    collected_data = result.get("data", [])
                    self.logger.info(f"🔍 Debug: result keys = {result.keys()}")
                    self.logger.info(
                        f"🔍 Debug: collected_data length = {len(collected_data)}"
                    )
                    self.logger.info(
                        f"🔍 Debug: collected_data type = {type(collected_data)}"
                    )
                    if collected_data and len(collected_data) > 0:
                        self.logger.info(f"🔍 Debug: first item = {collected_data[0]}")
                    if collected_data:
                        self.logger.info(
                            f"REGTECH에서 {len(collected_data)}개 IP 수집됨, 저장 시작..."
                        )

                        # PostgreSQL에 저장
                        try:
                            from src.core.data_storage_fixed import FixedDataStorage

                            storage = FixedDataStorage()
                            storage_result = storage.store_ips(
                                collected_data, "REGTECH"
                            )

                            if storage_result.get("success"):
                                self.logger.info(
                                    f"✅ {storage_result.get('imported_count', 0)}개 IP 저장 완료"
                                )
                                return {
                                    "success": True,
                                    "message": f"REGTECH 수집 및 저장 완료: {storage_result.get('imported_count', 0)}개 IP",
                                    "collected": len(collected_data),
                                    "stored": storage_result.get("imported_count", 0),
                                    "duplicates": storage_result.get(
                                        "duplicate_count", 0
                                    ),
                                }
                            else:
                                self.logger.error(
                                    f"저장 실패: {storage_result.get('error')}"
                                )
                                return {
                                    "success": False,
                                    "message": f"데이터 저장 실패: {storage_result.get('error')}",
                                }
                        except ImportError:
                            self.logger.warning("Data storage module not available")
                            return {
                                "success": True,
                                "message": f"REGTECH 수집 완료: {len(collected_data)}개 IP (저장 모듈 없음)",
                                "collected": len(collected_data),
                            }
                except Exception as collect_e:
                    return {
                        "success": False,
                        "message": f"REGTECH 수집 중 오류: {str(collect_e)}",
                    }

                # 로그 남기기
                if hasattr(self, "add_collection_log"):
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
                # 기본 수집 - 직접 실행
                try:
                    result = self._components["regtech"].collect_from_web()
                    if not result.get("success"):
                        return {
                            "success": False,
                            "message": f"REGTECH 수집 실패: {result.get('error', 'Unknown error')}",
                        }
                except Exception as collect_e:
                    return {
                        "success": False,
                        "message": f"REGTECH 수집 중 오류: {str(collect_e)}",
                    }

                # 로그 남기기
                if hasattr(self, "add_collection_log"):
                    self.add_collection_log(
                        source="regtech",
                        action="manual_trigger",
                        details={"force": force},
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
            if hasattr(self, "add_collection_log"):
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
