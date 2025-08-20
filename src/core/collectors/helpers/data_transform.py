#!/usr/bin/env python3
"""
REGTECH 데이터 변환 모듈
데이터 변환, 날짜 처리 등의 기능을 제공
"""

import logging
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import List

logger = logging.getLogger(__name__)


class RegtechDataTransform:
    """
    REGTECH 데이터 변환 전담 클래스
    """

    def transform_data(self, raw_data: dict) -> dict:
        """
        원시 데이터를 표준 형식으로 변환 (탐지일 기준 3개월 만료)

        Args:
            raw_data: 원시 수집 데이터

        Returns:
            변환된 데이터 딕셔너리 (expires_at 포함)
        """
        try:
            # 탐지일 파싱
            detection_date_str = raw_data.get(
                "date", datetime.now().strftime("%Y-%m-%d")
            )

            # 다양한 날짜 형식 처리
            detection_date = None
            try:
                if len(detection_date_str.replace("-", "").replace(".", "")) == 8:
                    # YYYYMMDD, YYYY-MM-DD, YYYY.MM.DD 형식
                    clean_date = detection_date_str.replace("-", "").replace(".", "")
                    detection_date = datetime.strptime(clean_date, "%Y%m%d")
                else:
                    # 기본적으로 ISO 형식 시도
                    detection_date = datetime.fromisoformat(detection_date_str)
            except:
                # 파싱 실패 시 현재 날짜 사용
                detection_date = datetime.now()
                logger.warning(f"날짜 파싱 실패, 현재 날짜 사용: {detection_date_str}")

            # 수집일 기준 3개월 후 만료 설정 (탐지일 아님)
            collection_date = datetime.now()  # 실제 수집한 날짜
            expires_at = collection_date + timedelta(days=90)  # 수집일 + 3개월 = 90일

            # 기본 변환
            transformed = {
                "ip": raw_data.get("ip", ""),
                "country": raw_data.get("country", "Unknown"),
                "reason": raw_data.get("reason", "Unknown threat"),
                "source": "REGTECH",
                "detection_date": detection_date.strftime(
                    "%Y-%m-%d"
                ),  # 실제 탐지일 유지
                "collection_date": collection_date.strftime("%Y-%m-%d"),  # 수집일 추가
                "expires_at": expires_at.isoformat(),  # 수집일 기준 만료
                "threat_level": raw_data.get("threat_level", "medium"),
                "category": raw_data.get("category", "malware"),
                "confidence": raw_data.get("confidence", 0.8),
            }

            # 추가 필드 처리
            if "additional_info" in raw_data:
                transformed["additional_info"] = raw_data["additional_info"]

            return transformed

        except Exception as e:
            logger.error(f"Data transformation error: {e}")
            # 최소한의 데이터 반환 (수집일 기준 3개월 만료)
            fallback_collection = datetime.now()
            fallback_expires = fallback_collection + timedelta(days=90)
            return {
                "ip": raw_data.get("ip", "0.0.0.0"),
                "source": "REGTECH",
                "country": "Unknown",
                "reason": "Transform error",
                "detection_date": fallback_collection.strftime(
                    "%Y-%m-%d"
                ),  # 에러 시 수집일로 설정
                "collection_date": fallback_collection.strftime("%Y-%m-%d"),  # 수집일
                "expires_at": fallback_expires.isoformat(),  # 수집일 기준 만료
            }

    def get_date_range(self, config=None) -> tuple[str, str]:
        """수집 날짜 범위 계산"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)  # 기본 30일

        # 설정에서 날짜 범위 override 가능
        if config and hasattr(config, "settings"):
            days = config.settings.get("collection_days", 30)
            start_date = end_date - timedelta(days=days)

        return start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d")

    def remove_duplicates(self, ips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """중복 IP 제거 (최신 데이터 우선)"""
        seen = {}
        unique_ips = []

        # 역순으로 순회하여 최신 데이터를 우선 보존
        for ip_data in reversed(ips):
            ip_addr = ip_data.get("ip")
            if ip_addr and ip_addr not in seen:
                seen[ip_addr] = True
                unique_ips.append(ip_data)

        # 원래 순서로 복원
        unique_ips.reverse()
        return unique_ips
