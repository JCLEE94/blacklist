#!/usr/bin/env python3
"""
REGTECH 간단한 수집기
환경변수 문제를 피하기 위한 독립 실행 수집기
"""
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import requests


class SimpleRegtechCollector:
    def __init__(self):
        self.base_url = "https://regtech.fsec.or.kr"
        self.username = os.getenv("REGTECH_USERNAME", "nextrade")
        self.password = os.getenv("REGTECH_PASSWORD", "Sprtmxm1@3")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )

    def collect(self):
        """데이터 수집"""
        print("REGTECH 수집 시작...")

        # 로그인
        login_data = {
            "memberId": self.username,
            "memberPw": self.password,
            "userType": "1",
        }

        login_resp = self.session.post(
            f"{self.base_url}/login/addLogin", data=login_data, timeout=30
        )

        if "error=true" in login_resp.url:
            print("로그인 실패")
            return []

        # 데이터 수집
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)

        post_data = {
            "page": "0",
            "tabSort": "blacklist",
            "startDate": start_date.strftime("%Y%m%d"),
            "endDate": end_date.strftime("%Y%m%d"),
            "size": "5000",
        }

        resp = self.session.post(
            f"{self.base_url}/fcti/securityAdvisory/advisoryList",
            data=post_data,
            timeout=30,
        )

        # IP 추출
        ip_pattern = r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
        ips = list(set(re.findall(ip_pattern, resp.text)))

        print(f"수집된 IP: {len(ips)}개")
        return ips


if __name__ == "__main__":
    collector = SimpleRegtechCollector()
    ips = collector.collect()

    # 결과 저장
    Path("data").mkdir(exist_ok=True)
    with open("data/regtech_ips.json", "w") as f:
        json.dump({"ips": ips, "collected_at": datetime.now().isoformat()}, f, indent=2)
