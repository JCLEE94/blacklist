#!/usr/bin/env python3
"""
REGTECH 데이터 처리 모듈
Excel, HTML, JSON 응답 처리 및 IP 추출
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class RegtechDataProcessor:
    """
    REGTECH 데이터 처리 전담 클래스
    다양한 응답 형식에서 IP 추출 및 데이터 변환
    """

    def __init__(self, validation_utils=None):
        self.validation_utils = validation_utils
        self.ip_pattern = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"

    async def process_excel_response(self, response) -> List[Dict[str, Any]]:
        """Excel 응답 처리"""
        try:
            from io import BytesIO

            import pandas as pd

            # Excel 파일 저장
            filename = (
                f"regtech_blacklist_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )
            with open(filename, "wb") as f:
                f.write(response.content)

            # Excel 파일 읽기
            df = pd.read_excel(BytesIO(response.content))

            # IP 컴럼 찾기
            ip_columns = [
                col
                for col in df.columns
                if "ip" in str(col).lower() or "IP" in str(col)
            ]

            if not ip_columns:
                # 첫 번째 컴럼이 IP일 가능성
                ip_columns = [df.columns[0]]

            ips = []
            for _, row in df.iterrows():
                for ip_col in ip_columns:
                    ip_value = str(row[ip_col]).strip()
                    if self._is_valid_ip(ip_value):
                        ips.append(
                            {
                                "ip": ip_value,
                                "source": "REGTECH",
                                "threat_level": "medium",
                                "detection_date": datetime.now().strftime("%Y-%m-%d"),
                                "method": "excel_download",
                                "description": "Blacklisted IP from REGTECH Excel export",
                            }
                        )
                        break

            logger.info(f"Processed Excel file: {filename}, extracted {len(ips)} IPs")
            return ips

        except ImportError:
            logger.warning("pandas not available - cannot process Excel files")
            return []
        except Exception as e:
            logger.error(f"Error processing Excel response: {e}")
            return []

    async def process_html_response(self, response) -> List[Dict[str, Any]]:
        """HTML 응답 처리"""
        try:
            # IP 패턴으로 추출
            ips_found = re.findall(self.ip_pattern, response.text)

            ips = []
            for ip in set(ips_found):  # 중복 제거
                if self._is_valid_ip(ip):
                    ips.append(
                        {
                            "ip": ip,
                            "source": "REGTECH",
                            "threat_level": "medium",
                            "detection_date": datetime.now().strftime("%Y-%m-%d"),
                            "method": "html_parsing",
                            "description": "Blacklisted IP from REGTECH web page",
                        }
                    )

            # BeautifulSoup로 테이블 파싱 시도
            try:
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(response.text, "html.parser")

                # 테이블에서 IP 추출
                tables = soup.find_all("table")
                for table in tables:
                    rows = table.find_all("tr")
                    for row in rows[1:]:  # 헤더 제외
                        cells = row.find_all(["td", "th"])
                        for cell in cells:
                            text = cell.get_text().strip()
                            if re.match(self.ip_pattern, text) and self._is_valid_ip(
                                text
                            ):
                                # 중복 확인
                                if not any(ip_data["ip"] == text for ip_data in ips):
                                    ips.append(
                                        {
                                            "ip": text,
                                            "source": "REGTECH",
                                            "threat_level": "medium",
                                            "detection_date": datetime.now().strftime(
                                                "%Y-%m-%d"
                                            ),
                                            "method": "table_parsing",
                                            "description": f"Blacklisted IP from REGTECH table",
                                        }
                                    )
            except BaseException:
                pass  # BeautifulSoup 파싱 실패해도 기본 regex 결과 사용

            return ips[:100]  # 최대 100개로 제한

        except Exception as e:
            logger.error(f"Error processing HTML response: {e}")
            return []

    async def process_json_response(self, response) -> List[Dict[str, Any]]:
        """JSON 응답 처리"""
        try:
            data = response.json()
            ips = []

            # 다양한 JSON 구조 처리
            if isinstance(data, dict):
                # 데이터 배열 찾기
                items = None
                for key in ["data", "items", "list", "blacklist", "ips", "results"]:
                    if key in data and isinstance(data[key], list):
                        items = data[key]
                        break

                if items:
                    for item in items:
                        if isinstance(item, dict):
                            # IP 필드 찾기
                            ip_value = None
                            for ip_key in [
                                "ip",
                                "ipAddress",
                                "target_ip",
                                "source_ip",
                                "addr",
                            ]:
                                if ip_key in item:
                                    ip_value = str(item[ip_key]).strip()
                                    break

                            if ip_value and self._is_valid_ip(ip_value):
                                ips.append(
                                    {
                                        "ip": ip_value,
                                        "source": "REGTECH",
                                        "threat_level": item.get(
                                            "threat_level", "medium"
                                        ),
                                        "detection_date": item.get(
                                            "date", datetime.now().strftime("%Y-%m-%d")
                                        ),
                                        "method": "json_api",
                                        "description": item.get(
                                            "description",
                                            "Blacklisted IP from REGTECH API",
                                        ),
                                    }
                                )
                        elif isinstance(item, str) and self._is_valid_ip(item):
                            ips.append(
                                {
                                    "ip": item,
                                    "source": "REGTECH",
                                    "threat_level": "medium",
                                    "detection_date": datetime.now().strftime(
                                        "%Y-%m-%d"
                                    ),
                                    "method": "json_api",
                                    "description": "Blacklisted IP from REGTECH API",
                                }
                            )

            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, str) and self._is_valid_ip(item):
                        ips.append(
                            {
                                "ip": item,
                                "source": "REGTECH",
                                "threat_level": "medium",
                                "detection_date": datetime.now().strftime("%Y-%m-%d"),
                                "method": "json_api",
                                "description": "Blacklisted IP from REGTECH API",
                            }
                        )

            return ips

        except Exception as e:
            logger.error(f"Error processing JSON response: {e}")
            return []

    def _is_valid_ip(self, ip_str: str) -> bool:
        """기본 IP 유효성 검사"""
        if self.validation_utils and hasattr(self.validation_utils, "is_valid_ip"):
            return self.validation_utils.is_valid_ip(ip_str)

        # 기본 IP 패턴 검사
        if not re.match(self.ip_pattern, ip_str):
            return False

        try:
            parts = ip_str.split(".")
            if len(parts) != 4:
                return False

            for part in parts:
                if not part.isdigit() or not 0 <= int(part) <= 255:
                    return False

            return True
        except (ValueError, AttributeError, TypeError):
            return False

    def remove_duplicates(self, ip_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """중복 IP 제거"""
        seen_ips = set()
        unique_ips = []

        for ip_data in ip_list:
            ip = ip_data.get("ip")
            if ip and ip not in seen_ips:
                seen_ips.add(ip)
                unique_ips.append(ip_data)

        return unique_ips

    def validate_and_transform_data(
        self, raw_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """데이터 유효성 검사 및 변환"""
        validated_data = []

        for item in raw_data:
            # 필수 필드 확인
            if not item.get("ip"):
                continue

            # IP 유효성 검사
            if not self._is_valid_ip(item["ip"]):
                continue

            # 기본값 설정
            validated_item = {
                "ip": item["ip"],
                "source": item.get("source", "REGTECH"),
                "threat_level": item.get("threat_level", "medium"),
                "detection_date": item.get(
                    "detection_date", datetime.now().strftime("%Y-%m-%d")
                ),
                "method": item.get("method", "unknown"),
                "description": item.get("description", "Blacklisted IP from REGTECH"),
            }

            validated_data.append(validated_item)

        return validated_data


if __name__ == "__main__":
    # 데이터 처리기 테스트
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: 기본 데이터 처리기 생성
    total_tests += 1
    try:
        processor = RegtechDataProcessor()
        if not hasattr(processor, "ip_pattern"):
            all_validation_failures.append("기본 속성 누락")
    except Exception as e:
        all_validation_failures.append(f"데이터 처리기 생성 실패: {e}")

    # Test 2: IP 유효성 검사
    total_tests += 1
    try:
        processor = RegtechDataProcessor()
        valid_ip = "192.168.1.1"
        invalid_ip = "999.999.999.999"

        if not processor._is_valid_ip(valid_ip):
            all_validation_failures.append("유효한 IP를 무효로 판단")

        if processor._is_valid_ip(invalid_ip):
            all_validation_failures.append("무효한 IP를 유효로 판단")
    except Exception as e:
        all_validation_failures.append(f"IP 유효성 검사 테스트 실패: {e}")

    # Test 3: 중복 제거
    total_tests += 1
    try:
        processor = RegtechDataProcessor()
        test_data = [
            {"ip": "192.168.1.1", "source": "REGTECH"},
            {"ip": "192.168.1.2", "source": "REGTECH"},
            {"ip": "192.168.1.1", "source": "REGTECH"},  # 중복
        ]
        unique_data = processor.remove_duplicates(test_data)
        if len(unique_data) != 2:
            all_validation_failures.append(f"중복 제거 실패: {len(unique_data)} != 2")
    except Exception as e:
        all_validation_failures.append(f"중복 제거 테스트 실패: {e}")

    # Test 4: 데이터 변환 및 유효성 검사
    total_tests += 1
    try:
        processor = RegtechDataProcessor()
        test_data = [
            {"ip": "192.168.1.1"},
            {"ip": "invalid_ip"},
            {"source": "test"},  # IP 없음
        ]
        validated_data = processor.validate_and_transform_data(test_data)
        if len(validated_data) != 1:  # 유효한 IP 하나만 남아야 함
            all_validation_failures.append(
                f"데이터 변환 실패: {len(validated_data)} != 1"
            )
    except Exception as e:
        all_validation_failures.append(f"데이터 변환 테스트 실패: {e}")

    # 최종 검증 결과
    if all_validation_failures:
        print(
            f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print("RegtechDataProcessor module is validated and ready for use")
        sys.exit(0)
