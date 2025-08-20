#!/usr/bin/env python3
"""
Data Processing Pipeline
수집기에서 DB로 데이터 정제 및 처리 파이프라인

SECUDIUM, REGTECH 수집기의 원시 데이터를 정제하여
통합 블랙리스트 DB에 저장하는 파이프라인입니다.
"""
import hashlib
import ipaddress
import logging
import re
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

logger = logging.getLogger(__name__)


class DataCleaningPipeline:
    """데이터 정제 및 처리 파이프라인"""

    def __init__(self, blacklist_manager=None):
        """
        초기화

        Args:
            blacklist_manager: UnifiedBlacklistManager 인스턴스
        """
        self.blacklist_manager = blacklist_manager
        self.processed_ips = set()  # 중복 방지용
        self.validation_stats = {
            "total_processed": 0,
            "valid_ips": 0,
            "invalid_ips": 0,
            "duplicates": 0,
            "enriched": 0,
            "saved": 0,
            "errors": 0,
        }

        logger.info("데이터 정제 파이프라인 초기화 완료")

    def process_collector_data(
        self, raw_data: List[Dict[str, Any]], source: str = "UNKNOWN"
    ) -> Dict[str, Any]:
        """
        수집기 원시 데이터를 정제하여 DB에 저장

        Args:
            raw_data: 수집기에서 가져온 원시 IP 데이터
            source: 데이터 소스 (REGTECH, SECUDIUM 등)

        Returns:
            처리 결과 통계
        """
        logger.info(f"{source} 데이터 정제 시작: {len(raw_data)}개 항목")

        # 통계 초기화
        self.validation_stats = {key: 0 for key in self.validation_stats.keys()}
        self.validation_stats["total_processed"] = len(raw_data)

        cleaned_data = []

        for raw_entry in raw_data:
            try:
                # 1. 기본 검증
                validated_entry = self._validate_ip_entry(raw_entry, source)
                if not validated_entry:
                    self.validation_stats["invalid_ips"] += 1
                    continue

                # 2. 중복 검사
                ip_hash = self._generate_ip_hash(validated_entry["ip"])
                if ip_hash in self.processed_ips:
                    self.validation_stats["duplicates"] += 1
                    logger.debug(f"중복 IP 스킵: {validated_entry['ip']}")
                    continue

                self.processed_ips.add(ip_hash)

                # 3. 데이터 정제 및 정규화
                cleaned_entry = self._clean_and_normalize(validated_entry, source)

                # 4. 메타데이터 보강
                enriched_entry = self._enrich_metadata(cleaned_entry, source)
                self.validation_stats["enriched"] += 1

                cleaned_data.append(enriched_entry)
                self.validation_stats["valid_ips"] += 1

            except Exception as e:
                logger.error(f"데이터 처리 중 오류: {e}, 데이터: {raw_entry}")
                self.validation_stats["errors"] += 1

        # 5. 벌크 저장
        if cleaned_data and self.blacklist_manager:
            save_result = self._bulk_save_to_db(cleaned_data, source)
            self.validation_stats["saved"] = save_result.get("imported_count", 0)

        logger.info(f"{source} 데이터 정제 완료: {len(cleaned_data)}개 정제됨")
        return {
            "success": True,
            "source": source,
            "processed_count": len(cleaned_data),
            "stats": self.validation_stats,
            "cleaned_data": cleaned_data,
        }

    def _validate_ip_entry(
        self, entry: Dict[str, Any], source: str
    ) -> Optional[Dict[str, Any]]:
        """
        IP 엔트리 기본 검증

        Args:
            entry: 원시 IP 데이터
            source: 데이터 소스

        Returns:
            검증된 엔트리 또는 None
        """
        try:
            # IP 주소 추출
            ip_str = entry.get("ip", "").strip()
            if not ip_str:
                logger.debug(f"IP 주소 누락: {entry}")
                return None

            # IP 주소 형식 검증
            if not self._is_valid_public_ip(ip_str):
                logger.debug(f"유효하지 않은 IP: {ip_str}")
                return None

            # 기본 엔트리 구조 생성
            validated = {
                "ip": ip_str,
                "source": entry.get("source", source),
                "detection_date": entry.get("detection_date"),
                "description": entry.get("description", ""),
                "threat_type": entry.get("threat_type", "blacklist"),
                "confidence": entry.get("confidence", "medium"),
                "source_file": entry.get("source_file", ""),
                "raw_data": entry,  # 원본 데이터 보존
            }

            return validated

        except Exception as e:
            logger.error(f"IP 엔트리 검증 오류: {e}")
            return None

    def _is_valid_public_ip(self, ip_str: str) -> bool:
        """
        공인 IP 주소 검증

        Args:
            ip_str: IP 주소 문자열

        Returns:
            유효한 공인 IP 여부
        """
        try:
            # ipaddress 모듈로 기본 검증
            ip_obj = ipaddress.ip_address(ip_str)

            # 사설 IP, 루프백, 멀티캐스트 제외
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_multicast:
                return False

            # 특수 IP 주소 제외
            special_ips = {
                "0.0.0.0",
                "255.255.255.255",
                "127.0.0.1",
                "::1",
                "224.0.0.0",
                "239.255.255.255",  # 멀티캐스트 범위
            }

            if ip_str in special_ips:
                return False

            # IP 클래스 확인 (A, B, C 클래스만 허용)
            first_octet = int(ip_str.split(".")[0])
            if first_octet == 0 or first_octet >= 224:
                return False

            return True

        except (ValueError, AttributeError):
            return False

    def _clean_and_normalize(
        self, entry: Dict[str, Any], source: str
    ) -> Dict[str, Any]:
        """
        데이터 정제 및 정규화

        Args:
            entry: 검증된 IP 엔트리
            source: 데이터 소스

        Returns:
            정제된 엔트리
        """
        cleaned = entry.copy()

        # IP 주소 정규화 (앞뒤 공백 제거, 소문자 변환)
        cleaned["ip"] = cleaned["ip"].strip().lower()

        # 소스 정규화
        cleaned["source"] = source.upper()

        # 설명 정제 (HTML 태그 제거, 특수 문자 정리)
        if cleaned.get("description"):
            desc = str(cleaned["description"])
            # HTML 태그 제거
            desc = re.sub(r"<[^>]+>", "", desc)
            # 여러 공백을 하나로
            desc = re.sub(r"\s+", " ", desc)
            # 앞뒤 공백 제거
            cleaned["description"] = desc.strip()[:500]  # 최대 500자

        # 날짜 정규화
        if not cleaned.get("detection_date"):
            cleaned["detection_date"] = datetime.now().strftime("%Y-%m-%d")
        elif isinstance(cleaned["detection_date"], datetime):
            cleaned["detection_date"] = cleaned["detection_date"].strftime("%Y-%m-%d")

        # 신뢰도 정규화
        confidence_map = {
            "high": "high",
            "medium": "medium",
            "low": "low",
            "very_high": "high",
            "very_low": "low",
        }
        cleaned["confidence"] = confidence_map.get(
            cleaned.get("confidence", "").lower(), "medium"
        )

        # 위협 유형 정규화
        threat_types = ["blacklist", "malware", "phishing", "spam", "botnet", "exploit"]
        if cleaned.get("threat_type", "").lower() not in threat_types:
            cleaned["threat_type"] = "blacklist"

        return cleaned

    def _enrich_metadata(self, entry: Dict[str, Any], source: str) -> Dict[str, Any]:
        """
        메타데이터 보강

        Args:
            entry: 정제된 IP 엔트리
            source: 데이터 소스

        Returns:
            메타데이터가 보강된 엔트리
        """
        enriched = entry.copy()

        # 고유 해시 생성
        enriched["entry_hash"] = self._generate_ip_hash(entry["ip"])

        # 처리 시간 추가
        enriched["processed_at"] = datetime.now().isoformat()

        # 소스별 특성 정보 추가
        if source.upper() == "REGTECH":
            enriched["source_category"] = "financial_security"
            enriched["authority"] = "FSI_KOREA"
            enriched["update_frequency"] = "daily"
        elif source.upper() == "SECUDIUM":
            enriched["source_category"] = "threat_intelligence"
            enriched["authority"] = "SECUDIUM"
            enriched["update_frequency"] = "realtime"

        # 지역 정보 추가 (간단한 IP 지역 분석)
        enriched["region_info"] = self._analyze_ip_region(entry["ip"])

        # 위험도 점수 계산
        enriched["risk_score"] = self._calculate_risk_score(enriched)

        return enriched

    def _generate_ip_hash(self, ip: str) -> str:
        """IP 주소 해시 생성"""
        return hashlib.sha256(ip.encode("utf-8")).hexdigest()

    def _analyze_ip_region(self, ip: str) -> Dict[str, str]:
        """
        IP 주소 지역 분석 (간단한 분석)

        Args:
            ip: IP 주소

        Returns:
            지역 정보
        """
        try:
            first_octet = int(ip.split(".")[0])

            # 간단한 지역 분류 (실제로는 GeoIP 데이터베이스 사용 권장)
            if 1 <= first_octet <= 126:
                return {"class": "A", "estimated_region": "unknown"}
            elif 128 <= first_octet <= 191:
                return {"class": "B", "estimated_region": "unknown"}
            elif 192 <= first_octet <= 223:
                return {"class": "C", "estimated_region": "unknown"}
            else:
                return {"class": "unknown", "estimated_region": "unknown"}

        except (ValueError, IndexError):
            return {"class": "unknown", "estimated_region": "unknown"}

    def _calculate_risk_score(self, entry: Dict[str, Any]) -> int:
        """
        위험도 점수 계산 (0-100)

        Args:
            entry: IP 엔트리

        Returns:
            위험도 점수 (0-100)
        """
        score = 50  # 기본 점수

        # 신뢰도에 따른 점수 조정
        confidence_scores = {"high": 30, "medium": 20, "low": 10}
        score += confidence_scores.get(entry.get("confidence", "medium"), 20)

        # 소스에 따른 점수 조정
        if entry.get("source") == "REGTECH":
            score += 15  # 정부 기관 소스
        elif entry.get("source") == "SECUDIUM":
            score += 10  # 상용 위협 인텔리전스

        # 최근 탐지일수록 높은 점수
        try:
            detection_date = datetime.strptime(
                entry.get("detection_date", ""), "%Y-%m-%d"
            )
            days_ago = (datetime.now() - detection_date).days
            if days_ago <= 7:
                score += 10
            elif days_ago <= 30:
                score += 5
        except Exception as e:
            pass

        return min(max(score, 0), 100)  # 0-100 범위로 제한

    def _bulk_save_to_db(
        self, cleaned_data: List[Dict[str, Any]], source: str
    ) -> Dict[str, Any]:
        """
        정제된 데이터를 DB에 벌크 저장

        Args:
            cleaned_data: 정제된 IP 데이터 목록
            source: 데이터 소스

        Returns:
            저장 결과
        """
        try:
            if not self.blacklist_manager:
                logger.error("BlacklistManager가 초기화되지 않음")
                return {"success": False, "error": "No blacklist manager"}

            logger.info(f"{source} 데이터 벌크 저장 시작: {len(cleaned_data)}개")

            # UnifiedBlacklistManager의 bulk_import_ips 사용
            result = self.blacklist_manager.bulk_import_ips(
                ips_data=cleaned_data, source="{source}_CLEANED"
            )

            if result.get("success", False):
                imported = result.get("imported_count", 0)
                skipped = result.get("skipped_count", 0)
                errors = result.get("error_count", 0)

                logger.info(
                    "{source} 벌크 저장 완료: {imported}개 저장, {skipped}개 스킵, {errors}개 오류"
                )
                return result
            else:
                logger.error(
                    f"{source} 벌크 저장 실패: {result.get('error', 'Unknown')}"
                )
                return result

        except Exception as e:
            logger.error(f"벌크 저장 중 오류: {e}")
            return {"success": False, "error": str(e)}

    def get_processing_stats(self) -> Dict[str, Any]:
        """
        처리 통계 반환

        Returns:
            처리 통계 정보
        """
        return {
            "validation_stats": self.validation_stats,
            "processed_ips_count": len(self.processed_ips),
            "last_processed": datetime.now().isoformat(),
        }

    def reset_stats(self):
        """통계 및 상태 초기화"""
        self.processed_ips.clear()
        self.validation_stats = {key: 0 for key in self.validation_stats.keys()}
        logger.info("데이터 파이프라인 통계 초기화 완료")


# 편의 함수들
def process_regtech_data(
    regtech_data: List[Dict[str, Any]], blacklist_manager=None
) -> Dict[str, Any]:
    """REGTECH 데이터 처리 편의 함수"""
    pipeline = DataCleaningPipeline(blacklist_manager)
    return pipeline.process_collector_data(regtech_data, "REGTECH")


def process_secudium_data(
    secudium_data: List[Dict[str, Any]], blacklist_manager=None
) -> Dict[str, Any]:
    """SECUDIUM 데이터 처리 편의 함수"""
    pipeline = DataCleaningPipeline(blacklist_manager)
    return pipeline.process_collector_data(secudium_data, "SECUDIUM")


def process_mixed_data(
    mixed_data: List[Dict[str, Any]], blacklist_manager=None
) -> Dict[str, Any]:
    """혼합 소스 데이터 처리 편의 함수"""
    pipeline = DataCleaningPipeline(blacklist_manager)
    return pipeline.process_collector_data(mixed_data, "MIXED")


# 테스트용 함수
def test_data_pipeline():
    """데이터 파이프라인 테스트"""

    # 테스트 데이터
    test_data = [
        {
            "ip": "8.8.8.8",
            "source": "TEST",
            "description": "Test IP 1",
            "threat_type": "blacklist",
            "confidence": "high",
        },
        {
            "ip": "1.1.1.1",
            "source": "TEST",
            "description": "Test IP 2",
            "threat_type": "malware",
            "confidence": "medium",
        },
    ]

    # 파이프라인 테스트
    pipeline = DataCleaningPipeline()
    result = pipeline.process_collector_data(test_data, "TEST")

    print("✅ 데이터 파이프라인 테스트 결과:")
    print(f"   - 처리된 데이터: {result['processed_count']}개")
    print(f"   - 통계: {result['stats']}")

    return result


if __name__ == "__main__":
    test_data_pipeline()
