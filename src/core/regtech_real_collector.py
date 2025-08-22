#!/usr/bin/env python3
"""
Real REGTECH Data Collector - Correct Excel Download Implementation
Based on successful pattern from Docker logs
"""

import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
import requests
from dotenv import load_dotenv
from loguru import logger

load_dotenv()


class RealRegtechCollector:
    """Real REGTECH collector using correct Excel download path"""

    def __init__(self):
        self.base_url = "https://regtech.fsec.or.kr"
        self.username = os.getenv("REGTECH_USERNAME", "")
        self.password = os.getenv("REGTECH_PASSWORD", "")
        self.session = None

    def collect_real_data(self) -> Dict[str, Any]:
        """Collect real data from REGTECH using correct Excel download path"""
        try:
            # Step 1: Create session
            self.session = requests.Session()
            self.session.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
                    "Referer": f"{self.base_url}/main/main",
                }
            )

            # Step 2: Login
            logger.info(f"Logging in to REGTECH with username: {self.username}")
            login_resp = self.session.post(
                f"{self.base_url}/login/loginProcess",
                data={"loginId": self.username, "loginPw": self.password},
                allow_redirects=True,
            )

            if login_resp.status_code != 200:
                return {
                    "success": False,
                    "error": f"Login failed with status {login_resp.status_code}",
                }

            # Check if we got the session cookie
            if "regtech-front" not in self.session.cookies:
                return {
                    "success": False,
                    "error": "No session cookie received after login",
                }

            logger.info(
                f"Login successful, cookie: {self.session.cookies.get('regtech-front')[:20]}..."
            )

            # Step 3: Navigate to blacklist page (required for some sites)
            board_url = f"{self.base_url}/board/boardList"
            board_params = {"menuCode": "HPHB0620101"}  # 악성IP차단 menu code

            logger.info("Navigating to blacklist board page...")
            board_resp = self.session.get(board_url, params=board_params)
            logger.info(f"Board page status: {board_resp.status_code}")

            # Step 4: Download Excel file with correct path
            excel_url = f"{self.base_url}/board/excelDownload"
            excel_params = {
                "menuCode": "HPHB0620101",  # 악성IP차단 menu code
                "pageIndex": "1",
                "pageSize": "10000",  # Get all data
                "searchType": "",
                "searchKeyword": "",
            }

            logger.info(f"Downloading Excel from: {excel_url}")
            excel_resp = self.session.get(
                excel_url,
                params=excel_params,
                stream=True,
                headers={
                    "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel,*/*",
                    "Referer": f"{self.base_url}/board/boardList?menuCode=HPHB0620101",
                },
            )

            logger.info(f"Excel download status: {excel_resp.status_code}")
            logger.info(
                f"Content-Type: {excel_resp.headers.get('Content-Type', 'Unknown')}"
            )
            logger.info(
                f"Content-Length: {excel_resp.headers.get('Content-Length', 'Unknown')}"
            )

            if excel_resp.status_code != 200:
                return {
                    "success": False,
                    "error": f"Excel download failed with status {excel_resp.status_code}",
                }

            # Check if we got Excel content
            content_type = excel_resp.headers.get("Content-Type", "")
            if (
                "excel" not in content_type.lower()
                and "spreadsheet" not in content_type.lower()
            ):
                # Sometimes the content type is generic, check content
                if len(excel_resp.content) < 1000:
                    logger.warning(
                        f"Response too small ({len(excel_resp.content)} bytes), might be error page"
                    )
                    # Try to parse as text to see what we got
                    try:
                        text = excel_resp.content.decode("utf-8")
                        logger.debug(f"Response text (first 500 chars): {text[:500]}")
                    except BaseException:
                        pass

            # Step 5: Parse Excel file
            logger.info(f"Parsing Excel file ({len(excel_resp.content)} bytes)...")
            collected_ips = []

            try:
                # Save to temp file and parse
                with tempfile.NamedTemporaryFile(
                    suffix=".xlsx", delete=False
                ) as tmp_file:
                    tmp_file.write(excel_resp.content)
                    tmp_path = tmp_file.name

                # Try to read Excel
                df = pd.read_excel(tmp_path, engine="openpyxl")
                logger.info(f"Excel shape: {df.shape}")
                logger.info(f"Columns: {df.columns.tolist()}")

                # Look for IP column (various possible names)
                ip_columns = [
                    "IP",
                    "ip",
                    "IP주소",
                    "IP Address",
                    "악성IP",
                    "IP_ADDRESS",
                ]
                ip_col = None

                for col in ip_columns:
                    if col in df.columns:
                        ip_col = col
                        break

                if not ip_col:
                    # Try to find column with IP-like data
                    for col in df.columns:
                        sample = df[col].dropna().head(5).astype(str)
                        if any(
                            "." in str(val) and len(str(val).split(".")) == 4
                            for val in sample
                        ):
                            ip_col = col
                            break

                if ip_col:
                    logger.info(f"Found IP column: {ip_col}")

                    for idx, row in df.iterrows():
                        ip = str(row.get(ip_col, "")).strip()
                        if ip and "." in ip:
                            # Clean IP (remove /32 if present)
                            if "/" in ip:
                                ip = ip.split("/")[0]

                            ip_data = {
                                "ip": ip,
                                "source": "REGTECH",
                                "description": row.get(
                                    "설명",
                                    row.get("Description", "Malicious IP from REGTECH"),
                                ),
                                "detection_date": datetime.now().strftime("%Y-%m-%d"),
                                "confidence": "high",
                            }
                            collected_ips.append(ip_data)

                    logger.info(f"Extracted {len(collected_ips)} IPs from Excel")
                else:
                    logger.warning("Could not find IP column in Excel")
                    logger.info(f"First few rows:\n{df.head()}")

                # Clean up temp file
                try:
                    os.unlink(tmp_path)
                except BaseException:
                    pass

            except Exception as e:
                logger.error(f"Error parsing Excel: {e}")
                # Try alternative: maybe it's HTML disguised as Excel
                try:
                    text = excel_resp.content.decode("utf-8")
                    if "<html" in text.lower():
                        logger.warning(
                            "Response is HTML, not Excel. May need different approach."
                        )
                        # Could parse HTML table here if needed
                except BaseException:
                    pass

            # Step 6: Return results
            if collected_ips:
                logger.info(
                    f"Successfully collected {len(collected_ips)} real IPs from REGTECH"
                )
                return {
                    "success": True,
                    "data": collected_ips,
                    "count": len(collected_ips),
                    "source": "REGTECH",
                    "collection_time": datetime.now().isoformat(),
                }
            else:
                return {
                    "success": False,
                    "error": "No IPs found in Excel file",
                    "data": [],
                    "count": 0,
                }

        except Exception as e:
            logger.error(f"Collection failed: {e}")
            return {"success": False, "error": str(e), "data": [], "count": 0}
        finally:
            if self.session:
                try:
                    self.session.close()
                except BaseException:
                    pass


if __name__ == "__main__":
    """Test real REGTECH collection"""
    import sys

    # Test validation
    all_validation_failures = []
    total_tests = 0

    # Test 1: Collector initialization
    total_tests += 1
    try:
        collector = RealRegtechCollector()
        if not collector.username or not collector.password:
            all_validation_failures.append("No REGTECH credentials in .env")
        else:
            print(f"✅ Credentials loaded: {collector.username}")
    except Exception as e:
        all_validation_failures.append(f"Collector initialization failed: {e}")

    # Test 2: Real data collection
    total_tests += 1
    try:
        print("\n🔄 Starting real data collection from REGTECH...")
        result = collector.collect_real_data()

        if result.get("success"):
            print(f"✅ Collection successful!")
            print(f"   - IPs collected: {result.get('count', 0)}")

            # Show first 5 IPs as proof
            if result.get("data"):
                print(f"\n📋 First 5 real IPs collected:")
                for i, ip_data in enumerate(result["data"][:5], 1):
                    print(
                        f"   {i}. {ip_data['ip']} - {ip_data.get('description', 'N/A')}"
                    )
        else:
            all_validation_failures.append(f"Collection failed: {result.get('error')}")
            print(f"❌ Collection failed: {result.get('error')}")

    except Exception as e:
        all_validation_failures.append(f"Collection test failed: {e}")
        print(f"❌ Collection test failed: {e}")

    # Final validation result
    if all_validation_failures:
        print(
            f"\n❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"\n✅ VALIDATION PASSED - Successfully collected real data from REGTECH")
        print("Real IPs are now available for storage in PostgreSQL")
        sys.exit(0)
