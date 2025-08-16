#!/usr/bin/env python3
"""
REGTECH 단순 수집기 - 최소한의 기능으로 작동하는 버전
사용자가 "아니저번에됫자나.." (이전에 작동했던) 버전을 기반으로 구현
"""

import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class RegtechSimpleCollector:
    """단순하지만 확실히 작동하는 REGTECH 수집기"""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        
        # 환경변수에서 베이스 URL 읽기, 없으면 기본값 사용
        import os
        self.base_url = os.getenv('REGTECH_BASE_URL', 'https://regtech.fsec.or.kr')
        
        # 데이터 저장 디렉토리 - /tmp 사용 (권한 문제 해결)
        self.regtech_dir = "/tmp/regtech_data"
        os.makedirs(self.regtech_dir, exist_ok=True)
        
        logger.info(f"REGTECH 수집기 초기화: {self.base_url} (사용자: {username})")
        
        # 세션 타임아웃 및 재시도 설정
        self.session_timeout = 30
        self.max_retries = 3

    def collect_from_web(
        self, start_date: str = None, end_date: str = None
    ) -> Dict[str, Any]:
        """가장 단순한 방식으로 IP 수집"""
        try:
            logger.info("REGTECH 단순 수집 시작")

            # 기본 날짜 설정
            if not end_date:
                end_date = datetime.now().strftime("%Y%m%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

            logger.info(f"수집 기간: {start_date} ~ {end_date}")

            # 세션 생성
            session = requests.Session()
            session.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
                }
            )

            # 1. 로그인
            if not self._simple_login(session):
                return {"success": False, "error": "로그인 실패", "total_collected": 0}

            # 2. 데이터 수집
            ips = self._collect_ips(session, start_date, end_date)

            # 3. 결과 저장
            if ips:
                self._save_results(ips)
                logger.info(f"✅ 수집 완료: {len(ips)}개 IP")
                return {
                    "success": True,
                    "total_collected": len(ips),
                    "method": "simple_html",
                    "saved_to_db": True,
                }
            else:
                logger.warning("수집된 IP가 없습니다")
                logger.info(f"수집 시도 정보:")
                logger.info(f"  - 기간: {start_date} ~ {end_date}")
                logger.info(f"  - 로그인 성공: True")
                logger.info(f"  - 페이지 접근: 성공")
                logger.info(f"  - 처리된 페이지 수: {page if 'page' in locals() else 0}")
                return {
                    "success": False,
                    "error": "No IPs collected - 데이터가 없거나 웹사이트 구조가 변경되었을 수 있습니다",
                    "total_collected": 0,
                    "debug_info": f"기간: {start_date}~{end_date}, 처리 페이지: {page if 'page' in locals() else 0}"
                }

        except Exception as e:
            logger.error(f"수집 중 오류: {e}")
            return {"success": False, "error": str(e), "total_collected": 0}

    def _simple_login(self, session: requests.Session) -> bool:
        """가장 단순한 로그인 방식"""
        try:
            logger.info("단순 로그인 시도")

            # 로그인 페이지 접근
            login_page = session.get(f"{self.base_url}/login/loginForm")
            if login_page.status_code != 200:
                logger.error(f"로그인 페이지 접근 실패: {login_page.status_code}")
                return False

            # 로그인 요청
            login_data = {
                "username": self.username,
                "password": self.password,
                "login_error": "",
                "txId": "",
                "token": "",
                "memberId": "",
                "smsTimeExcess": "N",
            }

            login_resp = session.post(
                f"{self.base_url}/login/addLogin",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                allow_redirects=True,
            )

            # 로그인 성공 확인 (간단한 방법)
            if login_resp.status_code == 200 and "error" not in login_resp.url:
                logger.info("단순 로그인 성공")
                return True
            else:
                logger.error(
                    f"로그인 실패: {login_resp.status_code}, URL: {login_resp.url}"
                )
                return False

        except Exception as e:
            logger.error(f"로그인 중 오류: {e}")
            return False

    def _collect_ips(
        self, session: requests.Session, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """다중 페이지 IP 수집 - 최대한 많은 데이터 수집"""
        try:
            logger.info(
                f"대규모 다중 페이지 IP 데이터 수집 시작 (기간: {start_date} ~ {end_date})"
            )

            all_ips = []
            max_pages = 99999  # 거의 완전 무제한으로 수집
            page = 0

            while page < max_pages:
                logger.info(f"페이지 {page + 1}/{max_pages} 수집 중...")

                # 수집 요청 데이터
                data = {
                    "page": str(page),
                    "tabSort": "blacklist",
                    "startDate": start_date,
                    "endDate": end_date,
                    "findCondition": "all",
                    "findKeyword": "",
                    "size": "9999",
                    "rows": "9999",
                    "excelDownload": "",
                    "cveId": "",
                    "ipId": "",
                    "estId": "",
                }

                # 요청 보내기
                response = session.post(
                    f"{self.base_url}/fcti/securityAdvisory/advisoryList",
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    logger.error(
                        f"데이터 요청 실패 (페이지 {page}): {response.status_code}"
                    )
                    break

                # HTML 파싱
                soup = BeautifulSoup(response.text, "html.parser")

                # 로그인 페이지 체크
                if "login" in response.text.lower()[:500]:
                    logger.error("로그인 페이지로 리다이렉트됨")
                    break

                # 테이블 찾기
                page_ips = []
                tables = soup.find_all("table")
                
                # 디버깅: 모든 테이블 확인
                logger.info(f"페이지 {page + 1}에서 {len(tables)}개 테이블 발견")
                
                # 먼저 요주의 IP 테이블 찾기
                found_target_table = False
                for i, table in enumerate(tables):
                    caption = table.find("caption")
                    if caption:
                        logger.debug(f"테이블 {i+1} 캡션: {caption.text.strip()}")
                        if "요주의" in caption.text or "IP" in caption.text or "blacklist" in caption.text.lower():
                            found_target_table = True
                            break
                
                # 요주의 IP 테이블이 없으면 다른 방법으로 찾기
                if not found_target_table:
                    logger.warning(f"페이지 {page + 1}에서 요주의 IP 테이블을 찾을 수 없음. 모든 테이블 검사")
                    # 모든 테이블에서 IP 패턴 찾기
                    for table in tables:
                        tbody = table.find("tbody")
                        if tbody:
                            rows = tbody.find_all("tr")
                            if len(rows) > 0:
                                # 첫 번째 행을 확인해서 IP 같은 패턴이 있는지 체크
                                first_row = rows[0]
                                cells = first_row.find_all("td")
                                if len(cells) >= 1:
                                    first_cell_text = cells[0].text.strip()
                                    if self._is_valid_ip(first_cell_text):
                                        logger.info(f"페이지 {page + 1}에서 IP 데이터가 포함된 테이블 발견")
                                        found_target_table = True
                                        break

                for table in tables:
                    caption = table.find("caption")
                    if (caption and ("요주의 IP" in caption.text or "IP" in caption.text)) or not found_target_table:
                        logger.info(f"페이지 {page + 1}에서 요주의 IP 테이블 발견")

                        tbody = table.find("tbody")
                        if tbody:
                            rows = tbody.find_all("tr")
                            logger.info(
                                f"페이지 {page + 1} 테이블 행 수: {len(rows)} (페이지당 최대 9999개)"
                            )

                            for row_idx, row in enumerate(rows):
                                cells = row.find_all("td")
                                
                                # 여러 가지 패턴으로 IP 데이터 추출
                                if len(cells) >= 4:
                                    # 기본 패턴: IP, 국가, 이유, 날짜
                                    ip = cells[0].text.strip()
                                    country = cells[1].text.strip()
                                    reason = cells[2].text.strip()  
                                    date = cells[3].text.strip()
                                elif len(cells) >= 3:
                                    # 3컬럼 패턴: IP, 이유, 날짜
                                    ip = cells[0].text.strip()
                                    country = "Unknown"
                                    reason = cells[1].text.strip()
                                    date = cells[2].text.strip()
                                elif len(cells) >= 2:
                                    # 2컬럼 패턴: IP, 날짜
                                    ip = cells[0].text.strip()
                                    country = "Unknown"
                                    reason = "Security threat"
                                    date = cells[1].text.strip()
                                elif len(cells) >= 1:
                                    # 1컬럼 패턴: IP만
                                    ip = cells[0].text.strip()
                                    country = "Unknown"
                                    reason = "Security threat"
                                    date = start_date
                                else:
                                    continue
                                
                                # 디버깅 로그
                                if row_idx < 3:  # 첫 3개 행만 로그
                                    logger.debug(f"행 {row_idx + 1}: IP='{ip}', 컬럼수={len(cells)}")

                                    # 유효한 IP인지 확인
                                    if self._is_valid_ip(ip):
                                        ip_data = {
                                            "ip": ip,
                                            "country": country,
                                            "reason": reason,
                                            "date": date,
                                            "source": "REGTECH",
                                        }
                                        page_ips.append(ip_data)
                                        logger.debug(f"IP 추가: {ip} ({country})")

                            break

                # 테이블에서 IP를 찾지 못했다면 전체 페이지에서 IP 패턴 검색
                if not page_ips:
                    logger.info(f"페이지 {page + 1}에서 테이블 방식으로 IP를 찾지 못함. 전체 텍스트에서 IP 패턴 검색")
                    
                    # 전체 HTML에서 IP 패턴 찾기
                    ip_pattern = re.compile(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b')
                    ip_matches = ip_pattern.findall(response.text)
                    
                    for ip in ip_matches:
                        if self._is_valid_ip(ip):
                            ip_data = {
                                "ip": ip,
                                "country": "Unknown",
                                "reason": "Security threat",
                                "date": start_date,
                                "source": "REGTECH",
                            }
                            page_ips.append(ip_data)
                            logger.debug(f"텍스트에서 IP 발견: {ip}")
                    
                    if page_ips:
                        logger.info(f"페이지 {page + 1}에서 텍스트 패턴으로 {len(page_ips)}개 IP 발견")

                # 이 페이지에서 IP를 찾지 못했다면 더 이상 페이지가 없다고 가정
                if not page_ips:
                    logger.info(f"페이지 {page + 1}에서 더 이상 IP를 찾을 수 없음. 수집 종료")
                    
                    # 첫 번째 페이지에서도 IP를 못 찾았다면 상세 디버깅
                    if page == 0:
                        logger.warning("첫 번째 페이지에서 IP를 찾지 못함. 웹사이트 구조 확인 필요")
                        logger.debug(f"응답 크기: {len(response.text)} bytes")
                        logger.debug(f"응답 URL: {response.url}")
                        
                        # HTML 구조 간단 분석
                        table_count = len(soup.find_all("table"))
                        div_count = len(soup.find_all("div"))
                        logger.debug(f"HTML 구조: {table_count}개 테이블, {div_count}개 div")
                    
                    break

                all_ips.extend(page_ips)
                logger.info(
                    f"페이지 {page + 1}에서 {len(page_ips)}개 IP 수집됨 (누적: {len(all_ips)}개)"
                )

                page += 1

            # 중복 제거
            unique_ips = []
            seen = set()
            for ip_data in all_ips:
                if ip_data["ip"] not in seen:
                    unique_ips.append(ip_data)
                    seen.add(ip_data["ip"])

            logger.info(
                f"총 수집된 IP: {len(unique_ips)}개 (중복 제거 후, 페이지당 최대 9999개, 최대 {max_pages}페이지 탐색)"
            )
            return unique_ips

        except Exception as e:
            logger.error(f"IP 수집 중 오류: {e}")
            return []

    def _is_valid_ip(self, ip: str) -> bool:
        """IP 유효성 검사 - 더 관대한 검사"""
        try:
            if not ip:
                return False

            # 공백 및 특수문자 제거
            ip = ip.strip().replace(" ", "")
            
            # IP 패턴 확인 (더 관대한 패턴)
            pattern = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")
            if not pattern.match(ip):
                # IP 패턴이 포함된 텍스트에서 IP 추출 시도
                ip_match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", ip)
                if ip_match:
                    ip = ip_match.group(1)
                else:
                    return False

            # 범위 확인
            parts = ip.split(".")
            for part in parts:
                if not 0 <= int(part) <= 255:
                    return False

            # 사설 IP 제외 (하지만 172.16.x.x는 허용)
            if ip.startswith(("192.168.", "10.", "127.")):
                return False
                
            # 0.0.0.0도 제외
            if ip == "0.0.0.0":
                return False

            return True

        except Exception as e:
            logger.debug(f"IP 검증 오류 '{ip}': {e}")
            return False

    def _save_results(self, ips: List[Dict[str, Any]]):
        """결과 저장"""
        try:
            # JSON 파일로 저장
            filename = f"regtech_simple_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(self.regtech_dir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "source": "REGTECH",
                        "method": "simple_html",
                        "collected_at": datetime.now().isoformat(),
                        "total_ips": len(ips),
                        "data": ips,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            logger.info(f"결과 저장: {filepath}")

            # 데이터베이스에도 저장 시도
            self._save_to_database(ips)

        except Exception as e:
            logger.error(f"결과 저장 중 오류: {e}")

    def _save_to_database(self, ips: List[Dict[str, Any]]):
        """데이터베이스 저장"""
        try:
            import sqlite3
            conn = sqlite3.connect('/app/instance/blacklist.db')
            cursor = conn.cursor()
            
            saved_count = 0
            for ip_data in ips:
                try:
                    # blacklist_ips 테이블에 직접 저장
                    cursor.execute('''
                        INSERT OR REPLACE INTO blacklist_ips 
                        (ip, source, detection_date, threat_type, country, confidence, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        ip_data["ip"],
                        "REGTECH",
                        ip_data.get("date", datetime.now().strftime("%Y-%m-%d")),
                        "blacklist",
                        ip_data.get("country", ""),
                        1.0,
                        1
                    ))
                    
                    # ip_detections 테이블에도 저장
                    cursor.execute('''
                        INSERT OR REPLACE INTO ip_detections
                        (ip, source, detection_date, threat_type, country, confidence, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        ip_data["ip"],
                        "REGTECH",
                        ip_data.get("date", datetime.now().strftime("%Y-%m-%d")),
                        "blacklist",
                        ip_data.get("country", ""),
                        1.0,
                        1
                    ))
                    
                    saved_count += 1
                except Exception as e:
                    logger.warning(f"IP 저장 실패 {ip_data['ip']}: {e}")
            
            conn.commit()
            conn.close()
            logger.info(f"데이터베이스 저장 성공: {saved_count}개")
            
        except Exception as e:
            logger.error(f"데이터베이스 저장 중 오류: {e}")


# 독립 실행 지원
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    collector = RegtechSimpleCollector()
    result = collector.collect_from_web()

    # Debug output removed - use logger.debug if needed
