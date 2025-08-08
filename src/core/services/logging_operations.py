#!/usr/bin/env python3
"""
로깅 및 모니터링 기능

수집 로그 관리, 이벤트 기록, 로그 조회 등의 기능을 제공합니다.
"""

from datetime import datetime
from typing import Dict, List, Optional


class LoggingOperationsMixin:
    """로깅 및 모니터링 기능을 제공하는 믹스인"""

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

    def get_collection_logs(self, limit: int = 50) -> List[Dict]:
        """수집 로그 조회"""
        try:
            # 메모리에서 최신 로그 반환
            return self.collection_logs[:limit]
        except Exception as e:
            self.logger.warning(f"Failed to get collection logs: {e}")
            return []
