# !/usr/bin/env python3
"""
데이터 처리 및 품질 개선 시스템
수집된 데이터의 정제, 검증, 저장을 담당
"""

import ipaddress
import json
import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class DataProcessor:
    """수집된 데이터 처리 및 품질 관리"""

    def __init__(self, db_path: str = "instance/blacklist.db"):
        self.db_path = db_path
        self.regtech_dir = Path("/tmp/regtech_data")

        # IP 유효성 검증 패턴
        self.ip_pattern = re.compile(
            r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
            r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        )

        # 위협 레벨 매핑
        self.threat_mapping = {
            "WordPress": "HIGH",
            "Apache": "HIGH",
            "SQL": "CRITICAL",
            "RCE": "CRITICAL",
            "XSS": "MEDIUM",
            "RADMIN": "HIGH",
            "RDP": "HIGH",
            "Tomcat": "HIGH",
            "Oracle": "HIGH",
            "PHPUnit": "CRITICAL",
            "Log4j": "CRITICAL",
            "Solr": "HIGH",
            "xmlRPC": "HIGH",
            "default": "MEDIUM",
        }

    def validate_ip(self, ip: str) -> bool:
        """IP 주소 유효성 검증"""
        try:
            # ipaddress 모듈을 사용한 검증
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    def classify_threat_level(self, reason: str) -> str:
        """공격 유형에 따른 위험도 분류"""
        reason_upper = reason.upper()

        for keyword, level in self.threat_mapping.items():
            if keyword.upper() in reason_upper:
                return level

        return self.threat_mapping["default"]

    def process_collected_data(self) -> Dict[str, Any]:
        """수집된 모든 데이터 파일 처리"""
        total_processed = 0
        total_valid = 0
        total_duplicates = 0
        total_saved = 0

        results = {
            "processed_files": [],
            "total_processed": 0,
            "total_valid": 0,
            "total_duplicates": 0,
            "total_saved": 0,
            "errors": [],
        }

        try:
            if not self.regtech_dir.exists():
                results["errors"].append("수집 데이터 디렉토리가 없습니다")
                return results

            # 모든 JSON 파일 처리
            json_files = list(self.regtech_dir.glob("*.json"))
            logger.info(f"처리할 파일 수: {len(json_files)}")

            for file_path in json_files:
                try:
                    file_result = self._process_single_file(file_path)
                    results["processed_files"].append(file_result)

                    total_processed += file_result["processed"]
                    total_valid += file_result["valid"]
                    total_duplicates += file_result["duplicates"]
                    total_saved += file_result["saved"]

                except Exception as e:
                    error_msg = f"파일 처리 오류 {file_path.name}: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)

            results.update(
                {
                    "total_processed": total_processed,
                    "total_valid": total_valid,
                    "total_duplicates": total_duplicates,
                    "total_saved": total_saved,
                }
            )

            logger.info(f"데이터 처리 완료: {total_saved}/{total_processed} 저장됨")

        except Exception as e:
            logger.error(f"데이터 처리 중 오류: {e}")
            results["errors"].append(str(e))

        return results

    def _process_single_file(self, file_path: Path) -> Dict[str, Any]:
        """단일 파일 처리"""
        result = {
            "filename": file_path.name,
            "processed": 0,
            "valid": 0,
            "duplicates": 0,
            "saved": 0,
            "errors": [],
        }

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict) or "data" not in data:
                result["errors"].append("잘못된 데이터 형식")
                return result

            ip_data_list = data["data"]
            result["processed"] = len(ip_data_list)

            # 중복 제거를 위한 세트
            seen_ips = set()
            valid_entries = []

            for item in ip_data_list:
                if not isinstance(item, dict) or "ip" not in item:
                    continue

                ip = item["ip"]

                # IP 유효성 검증
                if not self.validate_ip(ip):
                    continue

                result["valid"] += 1

                # 중복 체크
                if ip in seen_ips:
                    result["duplicates"] += 1
                    continue

                seen_ips.add(ip)

                # 데이터 정제 및 표준화
                processed_entry = self._standardize_entry(item)
                valid_entries.append(processed_entry)

            # 데이터베이스 저장
            saved_count = self._save_to_database(valid_entries)
            result["saved"] = saved_count

        except Exception as e:
            result["errors"].append(str(e))
            logger.error(f"파일 처리 오류 {file_path.name}: {e}")

        return result

    def _standardize_entry(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """데이터 항목 표준화"""
        ip = item.get("ip", "")
        country = item.get("country", "UNKNOWN")
        reason = item.get("reason", "알 수 없는 공격")
        date = item.get("date", datetime.now().strftime("%Y-%m-%d"))
        source = item.get("source", "REGTECH")

        # 위험도 분류
        threat_level = self.classify_threat_level(reason)

        # 신뢰도 계산 (기본값)
        confidence_level = 0.8 if country != "UNKNOWN" else 0.6

        return {
            "ip_address": ip,
            "source": source,
            "country": country,
            "reason": reason,
            "threat_level": threat_level,
            "detection_date": date,
            "collection_date": datetime.now().strftime("%Y-%m-%d"),
            "confidence_level": confidence_level,
            "is_active": True,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

    def _save_to_database(self, entries: List[Dict[str, Any]]) -> int:
        """데이터베이스에 항목들 저장"""
        saved_count = 0

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for entry in entries:
                try:
                    # 중복 체크
                    cursor.execute(
                        "SELECT id FROM blacklist_entries WHERE ip_address = ?",
                        (entry["ip_address"],),
                    )

                    if cursor.fetchone():
                        # 기존 항목 업데이트
                        cursor.execute(
                            """
                            UPDATE blacklist_entries
                            SET last_seen = ?, updated_at = ?,
                                country = ?, reason = ?, threat_level = ?
                            WHERE ip_address = ?
                        """,
                            (
                                entry["detection_date"],
                                entry["updated_at"],
                                entry["country"],
                                entry["reason"],
                                entry["threat_level"],
                                entry["ip_address"],
                            ),
                        )
                    else:
                        # 새 항목 삽입
                        cursor.execute(
                            """
                            INSERT INTO blacklist_entries (
                                ip_address, source, country, reason, threat_level,
                                detection_date, collection_date, confidence_level,
                                is_active, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                entry["ip_address"],
                                entry["source"],
                                entry["country"],
                                entry["reason"],
                                entry["threat_level"],
                                entry["detection_date"],
                                entry["collection_date"],
                                entry["confidence_level"],
                                entry["is_active"],
                                entry["created_at"],
                                entry["updated_at"],
                            ),
                        )
                        saved_count += 1

                except sqlite3.Error as e:
                    logger.error(f"DB 저장 오류 {entry['ip_address']}: {e}")

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"데이터베이스 연결 오류: {e}")

        return saved_count

    def get_processing_statistics(self) -> Dict[str, Any]:
        """처리 통계 정보 반환"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 전체 통계
            cursor.execute("SELECT COUNT(*) FROM blacklist_entries")
            total_ips = cursor.fetchone()[0]

            # 소스별 통계
            cursor.execute(
                """
                SELECT source, COUNT(*)
                FROM blacklist_entries
                GROUP BY source
            """
            )
            sources = dict(cursor.fetchall())

            # 국가별 통계 (상위 10개)
            cursor.execute(
                """
                SELECT country, COUNT(*)
                FROM blacklist_entries
                GROUP BY country
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """
            )
            countries = dict(cursor.fetchall())

            # 위험도별 통계
            cursor.execute(
                """
                SELECT threat_level, COUNT(*)
                FROM blacklist_entries
                GROUP BY threat_level
            """
            )
            threat_levels = dict(cursor.fetchall())

            # 일별 수집 통계
            cursor.execute(
                """
                SELECT collection_date, COUNT(*)
                FROM blacklist_entries
                GROUP BY collection_date
                ORDER BY collection_date DESC
                LIMIT 7
            """
            )
            daily_collection = dict(cursor.fetchall())

            conn.close()

            return {
                "total_ips": total_ips,
                "sources": sources,
                "countries": countries,
                "threat_levels": threat_levels,
                "daily_collection": daily_collection,
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"통계 조회 오류: {e}")
            return {}


if __name__ == "__main__":
    # 데이터 처리 테스트
    processor = DataProcessor()

    print("🔄 수집된 데이터 처리 시작...")
    results = processor.process_collected_data()

    print("📊 처리 결과:")
    print(f"  - 처리된 파일: {len(results['processed_files'])}")
    print(f"  - 총 처리된 항목: {results['total_processed']}")
    print(f"  - 유효한 IP: {results['total_valid']}")
    print(f"  - 중복 제거: {results['total_duplicates']}")
    print(f"  - 저장된 항목: {results['total_saved']}")

    if results["errors"]:
        print(f"❌ 오류: {len(results['errors'])}개")
        for error in results["errors"][:3]:
            print(f"    - {error}")

    print("\n📈 데이터베이스 통계:")
    stats = processor.get_processing_statistics()
    if stats:
        print(f"  - 총 IP 수: {stats.get('total_ips', 0)}")
        print(f"  - 소스별: {stats.get('sources', {})}")
        print(f"  - 위험도별: {stats.get('threat_levels', {})}")
