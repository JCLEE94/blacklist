#!/usr/bin/env python3
"""
DB 기반 수집기 시스템
UI에서 저장된 DB 설정을 활용하여 데이터 수집
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

try:
    from .database.collection_settings import CollectionSettingsDB
except ImportError:
    from src.core.database.collection_settings import CollectionSettingsDB

logger = logging.getLogger(__name__)


class DatabaseCollectionSystem:
    """데이터베이스 기반 수집 시스템"""

    def __init__(self, db_path: str = "instance/blacklist.db"):
        """DB 연결 초기화"""
        self.db = CollectionSettingsDB(db_path)
        logger.info("DB 기반 수집 시스템 초기화 완료")

    def get_enabled_sources(self) -> List[Dict[str, Any]]:
        """활성화된 수집 소스 목록"""
        sources = self.db.get_all_sources()
        return [s for s in sources if s["enabled"]]

    def collect_from_source(
        self,
        source_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """특정 소스에서 데이터 수집"""

        # 소스 설정 조회
        source_config = self.db.get_source_config(source_name)
        if not source_config:
            error_msg = f"소스 설정 없음: {source_name}"
            logger.error(error_msg)
            return self._create_error_result(source_name, error_msg)

        # 자격증명 조회
        credentials = self.db.get_credentials(source_name)
        if not credentials:
            error_msg = f"자격증명 없음: {source_name}"
            logger.error(error_msg)
            return self._create_error_result(source_name, error_msg)

        # 날짜 설정
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            default_range = self.db.get_setting("default_date_range", 7)
            start_date = (datetime.now() - timedelta(days=default_range)).strftime(
                "%Y-%m-%d"
            )

        # 수집 실행
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
                    source_config, credentials, start_date, end_date, result
                )
            else:
                result["error"] = f"지원하지 않는 소스: {source_name}"

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"{source_name} 수집 실패: {e}")

        # 수집 결과를 DB에 저장
        self.db.save_collection_result(
            source_name=source_name,
            start_date=start_date,
            end_date=end_date,
            success=result["success"],
            collected_count=result["count"],
            error_message=result.get("error", ""),
            metadata={
                "ips": result["ips"][:10] if result["ips"] else [],  # 샘플만 저장
                "collection_time": result["collected_at"],
            },
        )

        return result

    def _create_error_result(self, source_name: str, error_msg: str) -> Dict[str, Any]:
        """에러 결과 생성"""
        return {
            "source": source_name,
            "start_date": "",
            "end_date": "",
            "collected_at": datetime.now().isoformat(),
            "success": False,
            "count": 0,
            "ips": [],
            "error": error_msg,
        }

    def _collect_regtech(
        self,
        source_config: Dict[str, Any],
        credentials: Dict[str, str],
        start_date: str,
        end_date: str,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """REGTECH 데이터 수집"""

        base_url = source_config["base_url"]
        config = source_config["config"]
        endpoints = config.get("endpoints", {})
        headers = config.get("headers", {})
        timeout = config.get("timeout", 30)

        # 세션 생성
        session = requests.Session()
        if headers:
            session.headers.update(headers)

        try:
            # 1. 로그인 페이지 접속
            login_url = f"{base_url}{endpoints.get('login', '/login/loginForm')}"
            logger.info(f"로그인 페이지 접속: {login_url}")

            login_resp = session.get(login_url, timeout=timeout)

            if login_resp.status_code != 200:
                result["error"] = f"로그인 페이지 접속 실패: {login_resp.status_code}"
                return result

            # 2. 로그인 실행
            login_action_url = (
                f"{base_url}{endpoints.get('login_action', '/login/loginAction')}"
            )
            login_data = {
                "userId": credentials["username"],
                "userPw": credentials["password"],
            }

            logger.info(f"로그인 시도: {credentials['username']}")
            login_action_resp = session.post(
                login_action_url, data=login_data, timeout=timeout
            )

            if login_action_resp.status_code != 200:
                result["error"] = f"로그인 실패: {login_action_resp.status_code}"
                return result

            # 로그인 성공 확인 (리다이렉트 또는 성공 페이지 확인)
            if (
                "로그인" in login_action_resp.text
                or "login" in login_action_resp.text.lower()
            ):
                result["error"] = "로그인 실패: 인증 정보 오류"
                return result

            logger.info("로그인 성공")

            # 3. 데이터 검색
            search_url = (
                f"{base_url}{endpoints.get('search', '/mipam/miPamBoard013.do')}"
            )
            search_data = {
                "pageNum": "1",
                "searchFlag": "1",
                "searchStDt": start_date.replace("-", ""),
                "searchEdDt": end_date.replace("-", ""),
                "searchType": "ALL",
                "searchWord": "",
            }

            logger.info(f"데이터 검색: {start_date} ~ {end_date}")
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
            if ip.startswith(("127.", "10.", "192.168.", "172.", "0.", "255.")):
                return False

            return True
        except Exception as e:
            logger.warning(f"IP validation error: {e}")
            return False

    def collect_all_enabled_sources(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """모든 활성화된 소스에서 수집"""

        enabled_sources = self.get_enabled_sources()
        results = {}

        total_success = 0
        total_failed = 0
        total_ips = 0

        for source in enabled_sources:
            source_name = source["name"]
            logger.info(f"수집 시작: {source_name}")

            result = self.collect_from_source(source_name, start_date, end_date)
            results[source_name] = result

            if result["success"]:
                total_success += 1
                total_ips += result["count"]
            else:
                total_failed += 1

        return {
            "summary": {
                "total_sources": len(enabled_sources),
                "successful_sources": total_success,
                "failed_sources": total_failed,
                "total_ips_collected": total_ips,
            },
            "results": results,
            "collected_at": datetime.now().isoformat(),
        }

    def get_statistics(self) -> Dict[str, Any]:
        """수집 통계 조회 (DB에서)"""
        return self.db.get_collection_statistics()

    def get_collection_calendar(self, year: int, month: int) -> Dict[str, Any]:
        """수집 캘린더 조회 (DB에서)"""
        return self.db.get_collection_calendar(year, month)


# 테스트 코드
if __name__ == "__main__":
    print("=" * 60)
    print("DB 기반 수집 시스템 테스트")
    print("=" * 60)

    # 시스템 초기화
    collector = DatabaseCollectionSystem()

    # 활성화된 소스 확인
    enabled_sources = collector.get_enabled_sources()
    print(f"\n활성화된 소스: {[s['name'] for s in enabled_sources]}")

    # 수집 테스트 (자동 실행 - CI/CD 호환)
    if enabled_sources:
        print(f"\n{enabled_sources[0]['name']} 수집 테스트 시작 (자동 모드)...")
        if True:  # 자동 실행
            source_name = enabled_sources[0]["name"]
            print(f"{source_name} 수집 시작...")

            result = collector.collect_from_source(source_name)

            if result["success"]:
                print(f"✅ 수집 성공: {result['count']}개 IP")
                if result["ips"]:
                    print(f"샘플 IP: {result['ips'][:5]}")
            else:
                print(f"❌ 수집 실패: {result.get('error', 'Unknown error')}")

    # 통계 확인
    stats = collector.get_statistics()
    print("\n통계:")
    print(f"  - 전체 수집: {stats['total_collections']}회")
    print(f"  - 성공: {stats['successful_collections']}회")
    print(f"  - 총 IP: {stats['total_ips_collected']}개")

    print("\n✅ DB 기반 수집 시스템 테스트 완료")
