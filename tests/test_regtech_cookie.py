#!/usr/bin/env python3
"""
REGTECH 쿠키 기반 데이터 수집
브라우저에서 로그인 후 쿠키를 사용한 자동화 수집
"""

import json
import re
import time
from datetime import datetime, timedelta

import requests

# SSL 경고 무시
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class REGTECHCookieCollector:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://regtech.fsec.or.kr"

        # 브라우저와 동일한 헤더 설정
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            }
        )

    def manual_cookie_setup(self):
        """수동으로 브라우저에서 복사한 쿠키 설정"""
        print("=" * 60)
        print("🍪 REGTECH 쿠키 기반 수집")
        print("=" * 60)

        print("\n📋 수동 쿠키 설정 안내:")
        print("1. 브라우저에서 https://regtech.fsec.or.kr/login/loginForm 접속")
        print("2. nextrade / Sprtmxm1@3 로 로그인")
        print("3. 개발자 도구(F12) → Network 탭")
        print("4. 요청 헤더에서 Cookie 값 복사")
        print("5. 아래에 붙여넣기")

        # 예시 쿠키 (실제 사용할 때는 브라우저에서 복사)
        example_cookies = {
            "regtech-front": "13D9F03D3FD8E4DCA4EC3E1D8D2260FD",
            "JSESSIONID": "ABCD1234567890",
            "loginToken": "sample-token-123",
        }

        print(f"\n📝 예시 쿠키 형식:")
        for name, value in example_cookies.items():
            print(f"   {name}={value}")

        # 실제 프로덕션에서는 사용자 입력 받기
        print(f"\n⚠️ 실제 쿠키 설정 필요 - 현재는 테스트 모드")
        return example_cookies

    def set_cookies_from_string(self, cookie_string):
        """브라우저에서 복사한 쿠키 문자열 파싱"""
        cookies = {}

        if cookie_string:
            for item in cookie_string.split(";"):
                if "=" in item:
                    name, value = item.strip().split("=", 1)
                    cookies[name] = value
                    self.session.cookies.set(name, value)

        return cookies

    def test_cookie_access(self):
        """쿠키를 사용한 접근 테스트"""
        print("\n🔍 쿠키 기반 접근 테스트...")

        # 1. 메인 페이지 접근
        try:
            response = self.session.get(
                f"{self.base_url}/main", verify=False, timeout=30
            )

            print(f"   메인 페이지 상태: {response.status_code}")

            if response.status_code == 200:
                if "login" not in response.url.lower():
                    print("   ✅ 인증된 접근 성공")
                    return True
                else:
                    print("   ❌ 로그인 페이지로 리다이렉트")

        except Exception as e:
            print(f"   ❌ 접근 오류: {e}")

        return False

    def collect_blacklist_data(self):
        """블랙리스트 데이터 수집"""
        print("\n📊 블랙리스트 데이터 수집...")

        # 다양한 블랙리스트 URL 시도
        blacklist_urls = [
            "/board/boardList?menuCode=HPHB0620101",  # 악성IP차단
            "/threat/blacklist/list",
            "/security/blacklist",
            "/api/blacklist/search",
            "/board/excelDownload?menuCode=HPHB0620101",
        ]

        collected_data = []

        for path in blacklist_urls:
            url = f"{self.base_url}{path}"
            print(f"\n   🔍 시도: {path}")

            try:
                # GET 요청
                response = self.session.get(url, verify=False, timeout=30)

                print(f"      상태: {response.status_code}")

                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "")

                    # Excel 파일 체크
                    if "excel" in content_type or "spreadsheet" in content_type:
                        print(f"      📥 Excel 파일 다운로드 ({len(response.content)} bytes)")

                        filename = f"regtech_blacklist_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                        with open(filename, "wb") as f:
                            f.write(response.content)
                        print(f"      💾 저장: {filename}")

                        # Excel 파싱 시도
                        try:
                            import pandas as pd

                            df = pd.read_excel(filename)

                            # IP 컬럼 찾기
                            ip_columns = [
                                col
                                for col in df.columns
                                if "ip" in col.lower() or "아이피" in col or "IP" in col
                            ]

                            if ip_columns:
                                ips = df[ip_columns[0]].dropna().tolist()
                                print(f"      ✅ Excel에서 {len(ips)}개 IP 추출")

                                for ip in ips[:10]:  # 처음 10개
                                    collected_data.append(
                                        {
                                            "ip": str(ip),
                                            "source": "REGTECH",
                                            "date": datetime.now().strftime("%Y-%m-%d"),
                                            "method": "excel_download",
                                        }
                                    )
                                break
                        except ImportError:
                            print(f"      ⚠️ pandas 없음 - Excel 파싱 불가")
                        except Exception as e:
                            print(f"      ⚠️ Excel 파싱 오류: {e}")

                    # HTML 페이지 체크
                    elif "text/html" in content_type:
                        # IP 패턴 찾기
                        ip_pattern = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
                        ips = re.findall(ip_pattern, response.text)

                        if ips:
                            unique_ips = list(set(ips))
                            print(f"      ✅ HTML에서 {len(unique_ips)}개 고유 IP 발견")

                            for ip in unique_ips[:20]:  # 처음 20개
                                collected_data.append(
                                    {
                                        "ip": ip,
                                        "source": "REGTECH",
                                        "date": datetime.now().strftime("%Y-%m-%d"),
                                        "method": "html_parsing",
                                    }
                                )

                            if len(unique_ips) > 5:
                                break
                        else:
                            print(f"      ⚠️ IP 데이터 없음")

                    # JSON 응답 체크
                    elif "application/json" in content_type:
                        try:
                            data = response.json()
                            print(
                                f"      📋 JSON 응답: {list(data.keys()) if isinstance(data, dict) else 'array'}"
                            )

                            # JSON에서 IP 추출 시도
                            if isinstance(data, dict):
                                # 다양한 키 시도
                                for key in [
                                    "data",
                                    "items",
                                    "list",
                                    "blacklist",
                                    "ips",
                                ]:
                                    if key in data and isinstance(data[key], list):
                                        items = data[key]
                                        for item in items[:10]:
                                            if isinstance(item, dict):
                                                ip = (
                                                    item.get("ip")
                                                    or item.get("ipAddress")
                                                    or item.get("target_ip")
                                                )
                                                if ip:
                                                    collected_data.append(
                                                        {
                                                            "ip": ip,
                                                            "source": "REGTECH",
                                                            "date": datetime.now().strftime(
                                                                "%Y-%m-%d"
                                                            ),
                                                            "method": "json_api",
                                                        }
                                                    )

                                        if collected_data:
                                            break
                        except Exception as e:
                            print(f"      ⚠️ JSON 파싱 오류: {e}")

                # POST 요청도 시도 (일부 API는 POST 필요)
                if not collected_data and "api" in path:
                    print(f"      🔄 POST 요청 시도...")

                    post_data = {
                        "startDate": (datetime.now() - timedelta(days=7)).strftime(
                            "%Y%m%d"
                        ),
                        "endDate": datetime.now().strftime("%Y%m%d"),
                        "pageSize": 100,
                        "page": 1,
                    }

                    try:
                        response = self.session.post(
                            url, data=post_data, verify=False, timeout=30
                        )

                        if response.status_code == 200:
                            print(f"      ✅ POST 응답 성공")
                            # 위와 동일한 파싱 로직...

                    except Exception as e:
                        print(f"      ❌ POST 요청 오류: {e}")

            except Exception as e:
                print(f"      ❌ 요청 오류: {e}")

        return collected_data

    def save_results(self, data):
        """수집 결과 저장"""
        if not data:
            print("\n⚠️ 수집된 데이터가 없습니다")
            return

        # JSON 저장
        result = {
            "source": "REGTECH",
            "collected_at": datetime.now().isoformat(),
            "total_count": len(data),
            "unique_ips": len(set(item["ip"] for item in data)),
            "data": data,
        }

        filename = (
            f"regtech_cookie_collection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"\n💾 결과 저장: {filename}")
        print(f"   📊 통계:")
        print(f"   - 총 레코드: {len(data)}개")
        print(f"   - 고유 IP: {result['unique_ips']}개")

        # 샘플 출력
        print(f"\n📋 샘플 데이터:")
        for item in data[:5]:
            print(f"   • {item['ip']} ({item['method']})")


def main():
    """메인 실행 함수"""
    collector = REGTECHCookieCollector()

    # 1. 쿠키 설정 안내
    cookies = collector.manual_cookie_setup()

    print(f"\n🔧 실제 수집을 위한 단계:")
    print(f"1. 브라우저에서 REGTECH에 로그인")
    print(f"2. 개발자 도구에서 쿠키 복사")
    print(f"3. 이 스크립트에 쿠키 설정")
    print(f"4. 자동 수집 실행")

    # 예시: 수동 쿠키 설정
    print(f"\n💡 쿠키 설정 예시:")
    cookie_string = input("브라우저 쿠키 문자열 입력 (또는 Enter로 테스트 모드): ")

    if cookie_string.strip():
        collector.set_cookies_from_string(cookie_string)
        print("✅ 쿠키 설정 완료")

        # 접근 테스트
        if collector.test_cookie_access():
            # 데이터 수집
            data = collector.collect_blacklist_data()
            collector.save_results(data)
        else:
            print("❌ 쿠키 인증 실패")
    else:
        print("⚠️ 테스트 모드 - 실제 쿠키 필요")


if __name__ == "__main__":
    main()
