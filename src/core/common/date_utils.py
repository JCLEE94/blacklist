"""
통합 날짜 및 월별 데이터 처리 유틸리티
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class DateUtils:
    """날짜 관련 유틸리티 클래스"""

    MONTH_FORMAT = "%Y-%m"

    @classmethod
    def validate_month_format(cls, month: str) -> bool:
        """
        월 형식 검증 (YYYY-MM)

        Args:
            month: 검증할 월 문자열

        Returns:
            유효한 형식인 경우 True
        """
        try:
            datetime.strptime(month, cls.MONTH_FORMAT)
            return True
        except ValueError:
            return False

    @classmethod
    def parse_month(cls, month: str) -> Optional[datetime]:
        """
        월 문자열을 datetime 객체로 변환

        Args:
            month: 월 문자열 (YYYY-MM)

        Returns:
            datetime 객체 또는 None
        """
        try:
            return datetime.strptime(month, cls.MONTH_FORMAT)
        except ValueError:
            logger.warning(f"Invalid month format: {month}")
            return None

    @classmethod
    def get_active_months(cls, months_back: int = 3) -> List[str]:
        """
        최근 N개월의 월 목록 반환

        Args:
            months_back: 포함할 개월 수

        Returns:
            월 문자열 목록 (YYYY-MM 형식)
        """
        now = datetime.now()
        months = []

        for i in range(months_back):
            month_date = now - timedelta(days=30 * i)
            months.append(month_date.strftime(cls.MONTH_FORMAT))

        return sorted(months)

    @classmethod
    def is_month_active(cls, month: str, retention_days: int = 90) -> bool:
        """
        월이 활성 기간 내에 있는지 확인

        Args:
            month: 확인할 월 (YYYY-MM)
            retention_days: 보관 기간 (일)

        Returns:
            활성 기간 내면 True
        """
        month_date = cls.parse_month(month)
        if not month_date:
            return False

        cutoff_date = datetime.now() - timedelta(days=retention_days)
        return month_date >= cutoff_date

    @classmethod
    def get_month_range(cls, month: str) -> Tuple[datetime, datetime]:
        """
        월의 시작일과 종료일 반환

        Args:
            month: 월 문자열 (YYYY-MM)

        Returns:
            (시작일, 종료일) 튜플
        """
        month_date = cls.parse_month(month)
        if not month_date:
            raise ValueError(f"Invalid month format: {month}")

        # 월의 첫날
        start_date = month_date.replace(day=1)

        # 다음 달의 첫날에서 하루 빼기
        if month_date.month == 12:
            end_date = month_date.replace(
                year=month_date.year + 1, month=1, day=1
            ) - timedelta(days=1)
        else:
            end_date = month_date.replace(
                month=month_date.month + 1, day=1
            ) - timedelta(days=1)

        return start_date, end_date


class MonthlyDataManager:
    """월별 데이터 디렉토리 관리 클래스"""

    def __init__(self, base_dir: Union[str, Path]):
        self.base_dir = Path(base_dir)
        self.detection_dir = self.base_dir / "by_detection_month"
        self.detection_dir.mkdir(parents=True, exist_ok=True)

    def get_all_months(self, sorted_desc: bool = True) -> List[Dict[str, Any]]:
        """
        모든 월별 디렉토리 정보 조회

        Args:
            sorted_desc: 내림차순 정렬 여부

        Returns:
            월별 정보 딕셔너리 리스트
        """
        months_info = []

        for month_dir in self.detection_dir.iterdir():
            if not month_dir.is_dir():
                continue

            month_name = month_dir.name
            if not DateUtils.validate_month_format(month_name):
                logger.warning(f"Invalid month directory: {month_name}")
                continue

            # 기본 정보
            info = {
                "month": month_name,
                "path": str(month_dir),
                "is_active": DateUtils.is_month_active(month_name),
                "has_ips": (month_dir / "ips.txt").exists(),
                "has_details": (month_dir / "details.json").exists(),
            }

            # IP 수 계산 (파일이 있는 경우)
            if info["has_ips"]:
                try:
                    with open(month_dir / "ips.txt", "r") as f:
                        info["ip_count"] = sum(1 for line in f if line.strip())
                except Exception as e:
                    logger.error(f"Error counting IPs for {month_name}: {e}")
                    info["ip_count"] = 0
            else:
                info["ip_count"] = 0

            months_info.append(info)

        # 정렬
        months_info.sort(key=lambda x: x["month"], reverse=sorted_desc)

        return months_info

    def get_active_months(self, retention_days: int = 90) -> List[Dict[str, Any]]:
        """
        활성 월별 디렉토리 정보 조회

        Args:
            retention_days: 보관 기간 (일)

        Returns:
            활성 월별 정보 딕셔너리 리스트
        """
        all_months = self.get_all_months()
        return [m for m in all_months if m["is_active"]]

    def get_month_path(self, month: str) -> Path:
        """
        월별 디렉토리 경로 반환

        Args:
            month: 월 문자열 (YYYY-MM)

        Returns:
            디렉토리 Path 객체
        """
        return self.detection_dir / month

    def ensure_month_directory(self, month: str) -> Path:
        """
        월별 디렉토리 생성 보장

        Args:
            month: 월 문자열 (YYYY-MM)

        Returns:
            생성된 디렉토리 Path 객체
        """
        month_dir = self.get_month_path(month)
        month_dir.mkdir(parents=True, exist_ok=True)
        return month_dir

    def cleanup_expired_months(self, retention_days: int = 90) -> List[str]:
        """
        만료된 월별 디렉토리 정리

        Args:
            retention_days: 보관 기간 (일)

        Returns:
            삭제된 월 목록
        """
        import shutil

        removed_months = []
        all_months = self.get_all_months()

        for month_info in all_months:
            if not month_info["is_active"]:
                try:
                    shutil.rmtree(month_info["path"])
                    removed_months.append(month_info["month"])
                    logger.info(f"Removed expired month: {month_info['month']}")
                except Exception as e:
                    logger.error(f"Error removing month {month_info['month']}: {e}")

        return removed_months
