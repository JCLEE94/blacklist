"""
SECUDIUM 수집기 더미 구현
실제 SECUDIUM 계정 문제로 비활성화 상태
"""

import logging
from typing import Any
from typing import Dict
from typing import List

logger = logging.getLogger(__name__)


class SecudiumCollector:
    """SECUDIUM 수집기 더미 클래스"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.enabled = False
        logger.info("SECUDIUM Collector initialized (disabled due to account issues)")

    def collect_from_web(self, **kwargs) -> List[Dict[str, Any]]:
        """웹 수집 더미 메서드"""
        logger.warning("SECUDIUM collection is disabled due to account issues")
        return []

    def get_status(self) -> Dict[str, Any]:
        """상태 반환"""
        return {
            "enabled": False,
            "reason": "Account issues - disabled",
            "last_collection": None,
        }
