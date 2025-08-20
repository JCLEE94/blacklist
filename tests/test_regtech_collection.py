#!/usr/bin/env python3
"""
REGTECH 실제 데이터 수집 테스트
"""

import json
import os
import sys
from datetime import datetime
from datetime import timedelta

import pandas as pd
import requests

# 환경 변수 설정
REGTECH_USERNAME = "nextrade"
REGTECH_PASSWORD = "Sprtmxm1@3"
REGTECH_BASE_URL = "https://regtech.fsec.or.kr"


class REGTECHCollector:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            }
        )

    def login(self):
        """REGTECH 로그인"""
        print("🔐 REGTECH 로그인 시도...")

        login_url = f"{REGTECH_BASE_URL}/api/v1/member/login"

        login_data = {"userId": REGTECH_USERNAME, "password": REGTECH_PASSWORD}

        try:
            response = self.session.post(
                login_url, json=login_data, verify=False, timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print("✅ 로그인 성공")
                    # 토큰 저장
                    if "token" in result:
                        self.session.headers["Authorization"] = (
                            f"Bearer {result['token']}"
                        )
                    return True
                else:
                    print(f"❌ 로그인 실패: {result.get('message')}")
            else:
                print(f"❌ 로그인 요청 실패: {response.status_code}")

        except Exception as e:
            print(f"❌ 로그인 오류: {e}")

        return False

    def collect_blacklist(self):
        """블랙리스트 데이터 수집"""
        print("\n📊 블랙리스트 데이터 수집 시작...")

        # 날짜 범위 설정 (최근 7일)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        params = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
            "pageSize": 1000,
            "page": 1,
        }

        # 여러 엔드포인트 시도
        endpoints = [
            "/api/v1/blacklist/search",
            "/api/v1/threat/blacklist",
            "/api/v1/security/blacklist",
            "/api/blacklist/list",
        ]

        collected_ips = []

        for endpoint in endpoints:
            url = f"{REGTECH_BASE_URL}{endpoint}"
            print(f"  시도: {endpoint}")

            try:
                response = self.session.get(
                    url, params=params, verify=False, timeout=30
                )

                if response.status_code == 200:
                    data = response.json()

                    # 데이터 추출
                    if "data" in data:
                        items = data["data"]
                    elif "items" in data:
                        items = data["items"]
                    elif "list" in data:
                        items = data["list"]
                    else:
                        items = data if isinstance(data, list) else []

                    if items:
                        for item in items:
                            # IP 추출
                            ip = None
                            if isinstance(item, dict):
                                ip = (
                                    item.get("ip")
                                    or item.get("ipAddress")
                                    or item.get("target_ip")
                                )
                            elif isinstance(item, str):
                                ip = item

                            if ip:
                                collected_ips.append(
                                    {
                                        "ip": ip,
                                        "date": datetime.now().strftime("%Y-%m-%d"),
                                        "source": "REGTECH",
                                        "threat_level": (
                                            item.get("threat_level", "medium")
                                            if isinstance(item, dict)
                                            else "medium"
                                        ),
                                    }
                                )

                        print(f"    ✅ {len(items)}개 항목 수집")
                        break
                    else:
                        print(f"    ⚠️ 데이터 없음")

                elif response.status_code == 401:
                    print(f"    ❌ 인증 필요 - 재로그인 시도")
                    if self.login():
                        continue
                else:
                    print(f"    ❌ 요청 실패: {response.status_code}")

            except Exception as e:
                print(f"    ❌ 오류: {e}")

        return collected_ips

    def save_results(self, ips):
        """결과 저장"""
        if not ips:
            print("\n⚠️ 수집된 데이터가 없습니다")
            return

        # JSON 저장
        output_file = (
            f"regtech_collection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(ips, f, indent=2, ensure_ascii=False)

        print(f"\n💾 결과 저장: {output_file}")
        print(f"   - 총 {len(ips)}개 IP 수집")

        # 통계 출력
        if ips:
            df = pd.DataFrame(ips)
            print(f"\n📊 수집 통계:")
            print(f"   - 고유 IP: {df['ip'].nunique()}개")
            print(f"   - 위협 레벨 분포:")
            if "threat_level" in df.columns:
                for level, count in df["threat_level"].value_counts().items():
                    print(f"     • {level}: {count}개")


def main():
    print("=" * 50)
    print("REGTECH 블랙리스트 수집 테스트")
    print("=" * 50)

    collector = REGTECHCollector()

    # 로그인
    if not collector.login():
        print("\n❌ 로그인 실패로 수집 중단")
        return

    # 데이터 수집
    ips = collector.collect_blacklist()

    # 결과 저장
    collector.save_results(ips)

    # 테스트 데이터 생성 (수집 실패 시)
    if not ips:
        print("\n📝 테스트 데이터 생성 중...")
        test_ips = []
        for i in range(50):
            test_ips.append(
                {
                    "ip": f"192.168.{i//10}.{i}",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "source": "REGTECH_TEST",
                    "threat_level": ["high", "medium", "low"][i % 3],
                }
            )

        with open("test_blacklist_data.json", "w", encoding="utf-8") as f:
            json.dump(test_ips, f, indent=2, ensure_ascii=False)

        print(f"✅ 테스트 데이터 생성 완료: test_blacklist_data.json")
        print(f"   - {len(test_ips)}개 테스트 IP 생성")


if __name__ == "__main__":
    # SSL 경고 무시
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    main()
