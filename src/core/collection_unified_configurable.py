#!/usr/bin/env python3
"""
설정 기반 통합 수집 시스템 - 하드코딩 제거
모든 설정은 config/collection_config.json에서 로드
"""

import json
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class ConfigurableCollectionSystem:
    """설정 기반 통합 수집 시스템 - 하드코딩 없음"""

    def __init__(self, config_path: str = "config/collection_config.json"):
        """설정 파일에서 모든 설정 로드"""
        self.config_path = Path(config_path)
        self.config = self._load_config()

        # 설정에서 경로들 가져오기
        storage_config = self.config.get("storage", {})
        self.credentials_file = Path(
            storage_config.get("credentials_file", "instance/credentials.enc")
        )
        self.collection_history_file = Path(
            storage_config.get("history_file", "instance/collection_history.json")
        )
        self.cipher_key_file = Path(
            storage_config.get("cipher_key_file", "instance/.cipher_key")
        )
        self.reports_dir = Path(storage_config.get("reports_dir", "instance/reports"))

        # 디렉토리 생성
        for path in [self.credentials_file.parent, self.reports_dir]:
            path.mkdir(exist_ok=True)

        # 암호화 시스템 초기화
        self.cipher_key = self._get_or_create_cipher_key()
        self.cipher = Fernet(self.cipher_key)

        # 수집 히스토리 로드
        self.collection_history = self._load_collection_history()

        logger.info(
            f"설정 기반 수집 시스템 초기화 완료: {len(self._get_enabled_sources())}개 소스 활성화"
        )

    def _load_config(self) -> Dict[str, Any]:
        """설정 파일 로드"""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"설정 파일 없음: {self.config_path}")

            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            logger.info(f"설정 파일 로드 완료: {self.config_path}")
            return config

        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            # 기본 설정 반환
            return {
                "sources": {},
                "collection": {"default_date_range": 7},
                "storage": {},
                "security": {},
            }

    def _get_enabled_sources(self) -> List[str]:
        """활성화된 소스 목록 반환"""
        sources = []
        for source_name, source_config in self.config.get("sources", {}).items():
            if source_config.get("enabled", False):
                sources.append(source_name)
        return sources

    def _get_source_config(self, source_name: str) -> Optional[Dict[str, Any]]:
        """특정 소스의 설정 반환"""
        return self.config.get("sources", {}).get(source_name)

    def _get_or_create_cipher_key(self) -> bytes:
        """암호화 키 생성 또는 로드"""
        if self.cipher_key_file.exists():
            return self.cipher_key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            self.cipher_key_file.write_bytes(key)
            # 설정에서 권한 가져오기
            permissions = self.config.get("security", {}).get(
                "file_permissions", "0o600"
            )
            self.cipher_key_file.chmod(int(permissions, 8))
            return key

    def save_credentials(
        self, username: str, password: str, source: str = "regtech"
    ) -> bool:
        """자격증명 안전하게 저장"""
        try:
            # 기존 자격증명 로드 (여러 소스 지원)
            all_credentials = self._load_all_credentials()

            # 새 자격증명 추가
            all_credentials[source] = {
                "username": username,
                "password": password,
                "saved_at": datetime.now().isoformat(),
                "source": source,
            }

            # 전체 자격증명 암호화 저장
            encrypted = self.cipher.encrypt(json.dumps(all_credentials).encode())
            self.credentials_file.write_bytes(encrypted)

            # 권한 설정
            permissions = self.config.get("security", {}).get(
                "file_permissions", "0o600"
            )
            self.credentials_file.chmod(int(permissions, 8))

            logger.info(f"{source} 자격증명 저장 완료")
            return True

        except Exception as e:
            logger.error(f"자격증명 저장 실패: {e}")
            return False

    def _load_all_credentials(self) -> Dict[str, Dict[str, str]]:
        """모든 자격증명 로드"""
        try:
            if self.credentials_file.exists():
                encrypted = self.credentials_file.read_bytes()
                decrypted = self.cipher.decrypt(encrypted)
                return json.loads(decrypted)
            return {}
        except Exception as e:
            logger.warning(f"자격증명 로드 실패: {e}")
            return {}

    def get_credentials(self, source: str = "regtech") -> Optional[Dict[str, str]]:
        """저장된 자격증명 로드"""
        try:
            # 환경변수 우선 확인
            env_username = os.getenv(f"{source.upper()}_USERNAME")
            env_password = os.getenv(f"{source.upper()}_PASSWORD")
            if env_username and env_password:
                return {"username": env_username, "password": env_password}

            # 암호화된 파일에서 로드
            all_credentials = self._load_all_credentials()
            if source in all_credentials:
                creds = all_credentials[source]
                return {"username": creds["username"], "password": creds["password"]}

            return None

        except Exception as e:
            logger.error(f"자격증명 로드 실패: {e}")
            return None

    def _load_collection_history(self) -> List[Dict[str, Any]]:
        """수집 히스토리 로드"""
        if self.collection_history_file.exists():
            try:
                with open(self.collection_history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)

                # 최대 기록 수 제한
                max_records = self.config.get("collection", {}).get(
                    "max_history_records", 100
                )
                if len(history) > max_records:
                    history = history[-max_records:]
                    self._save_collection_history(history)

                return history
            except Exception as e:
                logger.warning(f"히스토리 로드 실패: {e}")

        return []

    def _save_collection_history(self, history: Optional[List[Dict[str, Any]]] = None):
        """수집 히스토리 저장"""
        try:
            if history is None:
                history = self.collection_history

            with open(self.collection_history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, default=str, ensure_ascii=False)

        except Exception as e:
            logger.error(f"히스토리 저장 실패: {e}")

    def _add_to_history(self, result: Dict[str, Any]):
        """수집 결과를 히스토리에 추가"""
        self.collection_history.append(result)

        # 최대 기록 수 제한
        max_records = self.config.get("collection", {}).get("max_history_records", 100)
        if len(self.collection_history) > max_records:
            self.collection_history = self.collection_history[-max_records:]

        self._save_collection_history()

    def collect_from_source(
        self,
        source_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """특정 소스에서 데이터 수집"""

        # 소스 설정 가져오기
        source_config = self._get_source_config(source_name)
        if not source_config:
            return {
                "source": source_name,
                "success": False,
                "error": f"소스 설정 없음: {source_name}",
                "collected_at": datetime.now().isoformat(),
            }

        if not source_config.get("enabled", False):
            return {
                "source": source_name,
                "success": False,
                "error": f"소스 비활성화: {source_name}",
                "collected_at": datetime.now().isoformat(),
            }

        # 날짜 설정
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            default_range = self.config.get("collection", {}).get(
                "default_date_range", 7
            )
            start_date = (datetime.now() - timedelta(days=default_range)).strftime(
                "%Y-%m-%d"
            )

        result = {
            "source": source_name,
            "start_date": start_date,
            "end_date": end_date,
            "collected_at": datetime.now().isoformat(),
            "success": False,
            "count": 0,
            "ips": [],
            "error": None,
        }

        try:
            if source_name == "regtech":
                result = self._collect_regtech(
                    source_config, start_date, end_date, result
                )
            else:
                result["error"] = f"지원하지 않는 소스: {source_name}"

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"{source_name} 수집 실패: {e}")

        # 히스토리에 추가
        self._add_to_history(result)
        return result

    def _collect_regtech(
        self,
        config: Dict[str, Any],
        start_date: str,
        end_date: str,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """REGTECH 데이터 수집"""

        # 자격증명 가져오기
        creds = self.get_credentials("regtech")
        if not creds:
            result["error"] = "자격증명 없음"
            return result

        base_url = config["base_url"]
        endpoints = config["endpoints"]
        headers = config.get("headers", {})
        timeout = config.get("timeout", 30)

        # 세션 생성
        session = requests.Session()
        session.headers.update(headers)

        try:
            # 1. 로그인 페이지 접속
            login_url = f"{base_url}{endpoints['login']}"
            login_resp = session.get(login_url, timeout=timeout)

            if login_resp.status_code != 200:
                result["error"] = f"로그인 페이지 접속 실패: {login_resp.status_code}"
                return result

            # 2. 로그인 액션
            login_action_url = f"{base_url}{endpoints['login_action']}"
            login_data = {"userId": creds["username"], "userPw": creds["password"]}

            login_action_resp = session.post(
                login_action_url, data=login_data, timeout=timeout
            )

            if login_action_resp.status_code != 200:
                result["error"] = f"로그인 실패: {login_action_resp.status_code}"
                return result

            # 로그인 성공 확인
            if (
                "로그인" in login_action_resp.text
                or "login" in login_action_resp.text.lower()
            ):
                result["error"] = "로그인 실패: 인증 정보 오류"
                return result

            # 3. 데이터 검색
            search_url = f"{base_url}{endpoints['search']}"
            search_data = {
                "pageNum": "1",
                "searchFlag": "1",
                "searchStDt": start_date.replace("-", ""),
                "searchEdDt": end_date.replace("-", ""),
                "searchType": "ALL",
                "searchWord": "",
            }

            search_resp = session.post(search_url, data=search_data, timeout=timeout)

            if search_resp.status_code == 200:
                # HTML 파싱하여 IP 추출
                soup = BeautifulSoup(search_resp.text, "html.parser")
                ip_list = self._extract_ips_from_html(soup)

                result["success"] = True
                result["count"] = len(ip_list)
                result["ips"] = ip_list

                logger.info(f"REGTECH 수집 성공: {len(ip_list)}개 IP")
            else:
                result["error"] = f"데이터 검색 실패: {search_resp.status_code}"

        except requests.exceptions.Timeout:
            result["error"] = "요청 시간 초과"
        except requests.exceptions.ConnectionError:
            result["error"] = "연결 실패"
        except Exception as e:
            result["error"] = f"수집 오류: {str(e)}"

        return result

    def _extract_ips_from_html(self, soup: BeautifulSoup) -> List[str]:
        """HTML에서 IP 주소 추출"""
        ip_list = []
        ip_pattern = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")

        # 테이블에서 IP 찾기
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                for cell in row.find_all(["td", "th"]):
                    text = cell.get_text().strip()
                    ips = ip_pattern.findall(text)
                    for ip in ips:
                        if self._is_valid_ip(ip) and ip not in ip_list:
                            ip_list.append(ip)

        return ip_list

    def _is_valid_ip(self, ip: str) -> bool:
        """IP 주소 유효성 검증"""
        try:
            parts = ip.split(".")
            if len(parts) != 4:
                return False

            for part in parts:
                num = int(part)
                if not (0 <= num <= 255):
                    return False

            # 사설 IP나 특수 IP 제외
            if ip.startswith(("127.", "10.", "192.168.", "172.")):
                return False

            return True
        except:
            return False

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
            "enabled_sources": self._get_enabled_sources(),
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
                    source = record.get("source")
                    if (
                        source
                        and source not in calendar_data[collected_date]["sources"]
                    ):
                        calendar_data[collected_date]["sources"].append(source)

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


# 테스트 및 검증
if __name__ == "__main__":
    print("=" * 60)
    print("설정 기반 수집 시스템 테스트")
    print("=" * 60)

    # 시스템 초기화
    system = ConfigurableCollectionSystem()

    # 설정 확인
    print(f"\n활성화된 소스: {system._get_enabled_sources()}")

    # 자격증명 저장 및 테스트
    print("\n자격증명 저장...")
    system.save_credentials("regtech", "Sprtmxm1@3", "regtech")
    system.save_credentials("nextrade", "Sprtmxm1@3", "regtech")

    creds = system.get_credentials("regtech")
    if creds:
        print(f"저장된 사용자: {creds['username']}")

    # 수집 테스트 (자동 실행 - CI/CD 호환)
    print("\nREGTECH 수집 테스트 시작 (자동 모드)...")
    if True:  # 자동 실행
        print("수집 시작...")
        result = system.collect_from_source("regtech")

        if result["success"]:
            print(f"✅ 수집 성공: {result['count']}개 IP")
        else:
            print(f"❌ 수집 실패: {result.get('error', 'Unknown error')}")

    # 통계 확인
    stats = system.get_statistics()
    print(
        f"\n통계: {stats['total_collections']}회 수집, {stats['successful_collections']}회 성공"
    )

    print("\n✅ 설정 기반 시스템 테스트 완료")
