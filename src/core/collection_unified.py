#!/usr/bin/env python3
"""
통합 수집 시스템 - 중복 제거 및 시각화
모든 수집 기능을 하나로 통합하고 날짜별 시각화 제공
"""

import json
import logging
import os
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

import pandas as pd
import requests
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class UnifiedCollectionSystem:
    """통합 수집 시스템 - 모든 수집 기능을 하나로"""

    def __init__(self, db_path: str = "instance/blacklist.db"):
        self.db_path = db_path
        self.credentials_file = Path("instance/credentials.enc")
        self.collection_history_file = Path("instance/collection_history.json")

        # 암호화 키 생성 또는 로드
        self.cipher_key = self._get_or_create_cipher_key()
        self.cipher = Fernet(self.cipher_key)

        # 수집 히스토리 초기화
        self.collection_history = self._load_collection_history()

        # REGTECH 설정
        self.regtech_base_url = "https://regtech.fsec.or.kr"

        logger.info("통합 수집 시스템 초기화 완료")

    def _get_or_create_cipher_key(self) -> bytes:
        """암호화 키 생성 또는 로드"""
        key_file = Path("instance/.cipher_key")
        key_file.parent.mkdir(exist_ok=True)

        if key_file.exists():
            return key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            key_file.chmod(0o600)  # 소유자만 읽기 가능
            return key

    def save_credentials(
        self, username: str, password: str, source: str = "regtech"
    ) -> bool:
        """자격증명 안전하게 저장"""
        try:
            credentials = {
                "source": source,
                "username": username,
                "password": password,
                "saved_at": datetime.now().isoformat(),
            }

            # 암호화
            encrypted = self.cipher.encrypt(json.dumps(credentials).encode())

            # 파일 저장
            self.credentials_file.parent.mkdir(exist_ok=True)
            self.credentials_file.write_bytes(encrypted)
            self.credentials_file.chmod(0o600)

            logger.info(f"{source} 자격증명 저장 완료")
            return True

        except Exception as e:
            logger.error(f"자격증명 저장 실패: {e}")
            return False

    def get_credentials(self, source: str = "regtech") -> Optional[Dict[str, str]]:
        """저장된 자격증명 로드"""
        try:
            # 환경변수 우선 확인
            if source == "regtech":
                username = os.getenv("REGTECH_USERNAME")
                password = os.getenv("REGTECH_PASSWORD")
                if username and password:
                    return {"username": username, "password": password}

            # 암호화된 파일에서 로드
            if self.credentials_file.exists():
                encrypted = self.credentials_file.read_bytes()
                decrypted = self.cipher.decrypt(encrypted)
                credentials = json.loads(decrypted)

                if credentials.get("source") == source:
                    return {
                        "username": credentials["username"],
                        "password": credentials["password"],
                    }

            return None

        except Exception as e:
            logger.error(f"자격증명 로드 실패: {e}")
            return None

    def _load_collection_history(self) -> List[Dict[str, Any]]:
        """수집 히스토리 로드"""
        if self.collection_history_file.exists():
            try:
                return json.loads(self.collection_history_file.read_text())
            except:
                return []
        return []

    def _save_collection_history(self):
        """수집 히스토리 저장"""
        try:
            self.collection_history_file.parent.mkdir(exist_ok=True)
            self.collection_history_file.write_text(
                json.dumps(self.collection_history, indent=2, default=str)
            )
        except Exception as e:
            logger.error(f"히스토리 저장 실패: {e}")

    def collect_regtech(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """REGTECH 데이터 수집 (단순화된 버전)"""

        # 날짜 설정
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        result = {
            "source": "regtech",
            "start_date": start_date,
            "end_date": end_date,
            "collected_at": datetime.now().isoformat(),
            "success": False,
            "count": 0,
            "ips": [],
            "error": None,
        }

        try:
            # 자격증명 가져오기
            creds = self.get_credentials("regtech")
            if not creds:
                result["error"] = "자격증명 없음"
                self._add_to_history(result)
                return result

            # 세션 생성
            session = requests.Session()
            session.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )

            # 로그인
            login_url = f"{self.regtech_base_url}/isap_svc/loginAction.do"
            login_data = {"userId": creds["username"], "userPw": creds["password"]}

            login_resp = session.post(login_url, data=login_data)
            if login_resp.status_code != 200:
                result["error"] = f"로그인 실패: {login_resp.status_code}"
                self._add_to_history(result)
                return result

            # 데이터 조회
            search_url = f"{self.regtech_base_url}/mipam/miPamBoard013.do"
            search_data = {
                "pageNum": "1",
                "searchFlag": "1",
                "searchStDt": start_date.replace("-", ""),
                "searchEdDt": end_date.replace("-", ""),
                "searchType": "ALL",
                "searchWord": "",
            }

            resp = session.post(search_url, data=search_data)
            if resp.status_code == 200:
                # HTML 파싱하여 IP 추출 (간단 예시)
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(resp.text, "html.parser")

                # 테이블에서 IP 추출 로직
                ip_list = []
                for row in soup.find_all("tr"):
                    cells = row.find_all("td")
                    if len(cells) > 3:  # IP가 있는 컬럼 확인
                        for cell in cells:
                            text = cell.get_text().strip()
                            # IP 패턴 매칭
                            if self._is_valid_ip(text):
                                ip_list.append(text)

                result["success"] = True
                result["count"] = len(ip_list)
                result["ips"] = ip_list

                logger.info(f"REGTECH 수집 성공: {len(ip_list)}개 IP")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"REGTECH 수집 실패: {e}")

        # 히스토리에 추가
        self._add_to_history(result)
        return result

    def _is_valid_ip(self, text: str) -> bool:
        """IP 주소 유효성 검증"""
        import re

        ip_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
        if re.match(ip_pattern, text):
            parts = text.split(".")
            return all(0 <= int(part) <= 255 for part in parts)
        return False

    def _add_to_history(self, result: Dict[str, Any]):
        """수집 결과를 히스토리에 추가"""
        self.collection_history.append(result)
        # 최근 100개만 유지
        if len(self.collection_history) > 100:
            self.collection_history = self.collection_history[-100:]
        self._save_collection_history()

    def get_collection_calendar(self, year: int, month: int) -> Dict[str, Any]:
        """특정 월의 수집 캘린더 데이터 생성"""
        calendar_data = {}

        # 해당 월의 모든 날짜 생성
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)

        current = start_date
        while current <= end_date:
            date_str = current.strftime("%Y-%m-%d")
            calendar_data[date_str] = {"collected": False, "count": 0, "sources": []}
            current += timedelta(days=1)

        # 히스토리에서 해당 월 데이터 추출
        for record in self.collection_history:
            if record.get("success"):
                collected_date = record.get("collected_at", "")[:10]
                if collected_date in calendar_data:
                    calendar_data[collected_date]["collected"] = True
                    calendar_data[collected_date]["count"] += record.get("count", 0)
                    calendar_data[collected_date]["sources"].append(
                        record.get("source")
                    )

        return {
            "year": year,
            "month": month,
            "calendar": calendar_data,
            "summary": {
                "total_days": len(calendar_data),
                "collected_days": sum(
                    1 for d in calendar_data.values() if d["collected"]
                ),
                "total_ips": sum(d["count"] for d in calendar_data.values()),
            },
        }

    def get_statistics(self) -> Dict[str, Any]:
        """수집 통계 생성"""
        stats = {
            "total_collections": len(self.collection_history),
            "successful_collections": sum(
                1 for h in self.collection_history if h.get("success")
            ),
            "failed_collections": sum(
                1 for h in self.collection_history if not h.get("success")
            ),
            "total_ips_collected": sum(
                h.get("count", 0) for h in self.collection_history if h.get("success")
            ),
            "sources": {},
            "recent_collections": (
                self.collection_history[-10:] if self.collection_history else []
            ),
        }

        # 소스별 통계
        for record in self.collection_history:
            source = record.get("source", "unknown")
            if source not in stats["sources"]:
                stats["sources"][source] = {
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "total_ips": 0,
                }

            stats["sources"][source]["total"] += 1
            if record.get("success"):
                stats["sources"][source]["success"] += 1
                stats["sources"][source]["total_ips"] += record.get("count", 0)
            else:
                stats["sources"][source]["failed"] += 1

        return stats


# 테스트 및 검증
if __name__ == "__main__":
    # 통합 시스템 초기화
    system = UnifiedCollectionSystem()

    # 실제 자격증명 저장 (제공된 정보 사용)
    print("자격증명 저장 중...")
    saved = system.save_credentials("regtech", "Sprtmxm1@3", "regtech")
    print(f"저장 결과: {saved}")

    # nextrade 계정도 저장
    saved2 = system.save_credentials("nextrade", "Sprtmxm1@3", "regtech")
    print(f"nextrade 저장 결과: {saved2}")

    # 자격증명 확인
    creds = system.get_credentials("regtech")
    if creds:
        print(f"저장된 자격증명: 사용자={creds['username']}")

    # 수집 테스트
    print("\n수집 테스트 시작...")
    result = system.collect_regtech()
    print(f"수집 결과: 성공={result['success']}, IP 수={result['count']}")

    # 통계 조회
    stats = system.get_statistics()
    print(
        f"\n통계: 전체={stats['total_collections']}, 성공={stats['successful_collections']}"
    )

    # 캘린더 데이터
    now = datetime.now()
    calendar = system.get_collection_calendar(now.year, now.month)
    print(f"\n{now.year}년 {now.month}월 수집 현황:")
    print(
        f"  - 수집일: {calendar['summary']['collected_days']}일/{calendar['summary']['total_days']}일"
    )
    print(f"  - 총 IP: {calendar['summary']['total_ips']}개")
