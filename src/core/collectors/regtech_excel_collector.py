#!/usr/bin/env python3
"""
REGTECH Excel 다운로드 전용 수집기
쿠키 인증 후 Excel 파일 다운로드 및 파싱
"""

import logging
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()


class RegtechExcelCollector:
    """REGTECH Excel 다운로드 수집기"""

    def __init__(self):
        self.base_url = "https://regtech.fsec.or.kr"
        self.username = os.getenv("REGTECH_USERNAME", "")
        self.password = os.getenv("REGTECH_PASSWORD", "")

    def collect_excel_data(self) -> Dict[str, Any]:
        """Excel 파일 다운로드 및 데이터 수집"""

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            }
        )

        try:
            # Step 1: 로그인
            logger.info(f"Logging in as {self.username}")
            login_resp = session.post(
                f"{self.base_url}/login/loginProcess",
                data={"loginId": self.username, "loginPw": self.password},
            )

            if "regtech-front" not in session.cookies:
                return {"success": False, "error": "Login failed", "data": []}

            logger.info("✅ Login successful")

            # Step 2: 게시판 페이지 접근 (쿠키 설정을 위해)
            board_url = f"{self.base_url}/board/boardList"
            board_params = {"menuCode": "HPHB0620101"}

            board_resp = session.get(board_url, params=board_params)
            logger.info(f"Board page status: {board_resp.status_code}")

            # Step 3: Excel 다운로드 - POST 요청으로 시도
            excel_url = f"{self.base_url}/board/excelDownload"

            # POST 파라미터 설정
            excel_data = {
                "menuCode": "HPHB0620101",
                "pageIndex": "1",
                "pageSize": "10000",
                "searchType": "",
                "searchKeyword": "",
                "startDate": (datetime.now().replace(day=1)).strftime("%Y%m%d"),
                "endDate": datetime.now().strftime("%Y%m%d"),
            }

            logger.info(f"Downloading Excel with POST request...")
            excel_resp = session.post(
                excel_url,
                data=excel_data,
                headers={
                    "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": f"{self.base_url}/board/boardList?menuCode=HPHB0620101",
                },
                stream=True,
            )

            logger.info(f"Excel response status: {excel_resp.status_code}")
            logger.info(
                f"Content-Type: {excel_resp.headers.get('Content-Type', 'Unknown')}"
            )
            logger.info(f"Content-Length: {len(excel_resp.content)} bytes")

            # Step 4: Excel 파일인지 확인
            content_type = excel_resp.headers.get("Content-Type", "")

            # Excel 파일이 아니면 다른 방법 시도
            if (
                "excel" not in content_type.lower()
                and "spreadsheet" not in content_type.lower()
            ):
                logger.warning("Not an Excel file, trying alternative method...")

                # Alternative: selectIpPoolList API 시도
                api_url = f"{self.base_url}/board/selectIpPoolList"
                api_resp = session.post(
                    api_url,
                    data={"menuCode": "HPHB0620101"},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if api_resp.status_code == 200:
                    try:
                        data = api_resp.json()
                        logger.info(f"API response: {type(data)}")

                        # JSON 데이터에서 IP 추출
                        collected_ips = []
                        if isinstance(data, dict) and "list" in data:
                            for item in data["list"]:
                                if "ip" in item or "ipAddress" in item:
                                    ip = item.get("ip") or item.get("ipAddress")
                                    collected_ips.append(
                                        {
                                            "ip": ip,
                                            "source": "REGTECH",
                                            "description": item.get(
                                                "description", "Malicious IP"
                                            ),
                                            "detection_date": datetime.now().strftime(
                                                "%Y-%m-%d"
                                            ),
                                            "confidence": "high",
                                        }
                                    )

                        if collected_ips:
                            logger.info(
                                f"✅ Collected {len(collected_ips)} IPs from API"
                            )
                            return {
                                "success": True,
                                "data": collected_ips,
                                "count": len(collected_ips),
                            }
                    except BaseException:
                        pass

            # Step 5: Excel 파일 파싱
            if len(excel_resp.content) > 1000:  # 최소 크기 확인
                logger.info("Parsing Excel file...")

                with tempfile.NamedTemporaryFile(
                    suffix=".xlsx", delete=False
                ) as tmp_file:
                    tmp_file.write(excel_resp.content)
                    tmp_path = tmp_file.name

                try:
                    df = pd.read_excel(tmp_path, engine="openpyxl")
                    logger.info(f"Excel shape: {df.shape}")
                    logger.info(f"Columns: {df.columns.tolist()}")

                    # IP 컬럼 찾기
                    collected_ips = []
                    ip_columns = ["IP", "ip", "IP주소", "악성IP", "IP_ADDRESS"]

                    ip_col = None
                    for col in ip_columns:
                        if col in df.columns:
                            ip_col = col
                            break

                    if not ip_col:
                        # 첫 번째 컬럼이 IP일 가능성
                        first_col = df.columns[0]
                        sample = df[first_col].dropna().head(5).astype(str)
                        if any("." in val for val in sample):
                            ip_col = first_col

                    if ip_col:
                        for idx, row in df.iterrows():
                            ip = str(row[ip_col]).strip()
                            if ip and "." in ip and ip != "nan":
                                if "/" in ip:
                                    ip = ip.split("/")[0]

                                collected_ips.append(
                                    {
                                        "ip": ip,
                                        "source": "REGTECH",
                                        "description": "Malicious IP from REGTECH",
                                        "detection_date": datetime.now().strftime(
                                            "%Y-%m-%d"
                                        ),
                                        "confidence": "high",
                                    }
                                )

                        logger.info(f"✅ Extracted {len(collected_ips)} IPs from Excel")
                        return {
                            "success": True,
                            "data": collected_ips,
                            "count": len(collected_ips),
                        }

                finally:
                    try:
                        os.unlink(tmp_path)
                    except BaseException:
                        pass

            logger.warning("No data collected")
            return {"success": False, "error": "No data found", "data": []}

        except Exception as e:
            logger.error(f"Collection failed: {e}")
            return {"success": False, "error": str(e), "data": []}
        finally:
            session.close()


# 기존 collect_from_web 메서드를 대체
async def collect_from_web_with_excel(
    self, start_date: str = None, end_date: str = None
) -> Dict[str, Any]:
    """Excel 다운로드 방식으로 수집"""
    collector = RegtechExcelCollector()
    result = collector.collect_excel_data()

    if result.get("success"):
        return {
            "success": True,
            "data": result.get("data", []),
            "count": result.get("count", 0),
            "message": f"REGTECH Excel에서 {result.get('count', 0)}개 IP 수집",
        }
    else:
        return {
            "success": False,
            "data": [],
            "count": 0,
            "error": result.get("error", "Unknown error"),
        }


if __name__ == "__main__":
    """테스트"""
    import sys

    collector = RegtechExcelCollector()
    result = collector.collect_excel_data()

    if result.get("success"):
        print(f"✅ 성공! {result.get('count')}개 IP 수집")
        if result.get("data"):
            print("\n처음 5개 IP:")
            for i, ip_data in enumerate(result["data"][:5], 1):
                print(f"  {i}. {ip_data['ip']}")
        sys.exit(0)
    else:
        print(f"❌ 실패: {result.get('error')}")
        sys.exit(1)
