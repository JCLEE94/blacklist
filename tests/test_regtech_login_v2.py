#!/usr/bin/env python3
"""
REGTECH 실제 로그인 테스트 - 개선된 버전
"""

import json
import re
import time
from datetime import datetime
from datetime import timedelta

import requests

# SSL 경고 무시
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class REGTECHLoginTest:
    def __init__(self):
        self.session = requests.Session()
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
                "Cache-Control": "max-age=0",
            }
        )
        self.base_url = "https://regtech.fsec.or.kr"

    def test_login(self):
        """REGTECH 로그인 테스트"""
        print("=" * 60)
        print("REGTECH 로그인 테스트 시작")
        print("=" * 60)

        # 1. 메인 페이지 접속 (쿠키 획득)
        print("\n1️⃣ 메인 페이지 접속...")
        try:
            main_response = self.session.get(
                self.base_url, verify=False, timeout=30, allow_redirects=True
            )
            print(f"   상태: {main_response.status_code}")
            print(f"   쿠키: {dict(self.session.cookies)}")
            time.sleep(1)  # 딜레이 추가
        except Exception as e:
            print(f"   ❌ 오류: {e}")

        # 2. 로그인 페이지 접속
        print("\n2️⃣ 로그인 페이지 접속...")
        login_page_url = f"{self.base_url}/login/loginForm"

        try:
            # Referer 추가
            self.session.headers["Referer"] = self.base_url

            response = self.session.get(
                login_page_url, verify=False, timeout=30, allow_redirects=True
            )
            print(f"   URL: {login_page_url}")
            print(f"   상태: {response.status_code}")
            print(f"   최종 URL: {response.url}")

            # HTML 파싱하여 form 정보 추출
            soup = BeautifulSoup(response.text, "html.parser")

            # 로그인 폼 찾기
            login_form = soup.find("form", {"id": "loginForm"}) or soup.find(
                "form", {"name": "loginForm"}
            )
            if login_form:
                print(f"   ✅ 로그인 폼 발견")
                action = login_form.get("action", "")
                print(f"   Action: {action}")

                # Hidden 필드 추출
                hidden_fields = {}
                for hidden in login_form.find_all("input", {"type": "hidden"}):
                    name = hidden.get("name")
                    value = hidden.get("value", "")
                    if name:
                        hidden_fields[name] = value
                        print(
                            f"   Hidden: {name} = {value[:20]}..."
                            if len(value) > 20
                            else f"   Hidden: {name} = {value}"
                        )

            # CSRF 토큰 찾기 (여러 방법)
            csrf_token = None

            # 방법 1: _csrf 필드
            csrf_input = soup.find("input", {"name": "_csrf"})
            if csrf_input:
                csrf_token = csrf_input.get("value")
                print(f"   CSRF 토큰 발견: {csrf_token[:20]}...")

            # 방법 2: meta 태그
            if not csrf_token:
                csrf_meta = soup.find("meta", {"name": "csrf-token"}) or soup.find(
                    "meta", {"name": "_csrf"}
                )
                if csrf_meta:
                    csrf_token = csrf_meta.get("content")
                    print(f"   CSRF 토큰 (meta): {csrf_token[:20]}...")

            # 방법 3: JavaScript에서 추출
            if not csrf_token and "csrfToken" in response.text:
                match = re.search(
                    r'csrfToken[\'"]?\s*[:=]\s*[\'"]([^\'\"]+)[\'"]', response.text
                )
                if match:
                    csrf_token = match.group(1)
                    print(f"   CSRF 토큰 (JS): {csrf_token[:20]}...")

            time.sleep(1)  # 딜레이 추가

        except Exception as e:
            print(f"   ❌ 오류: {e}")
            return False

        # 3. 로그인 시도
        print("\n3️⃣ 로그인 시도...")
        login_url = f"{self.base_url}/login/loginProcess"

        # 로그인 데이터 준비
        login_data = {"loginID": "nextrade", "loginPW": "Sprtmxm1@3", "saveID": "N"}

        # Hidden 필드 추가
        if "hidden_fields" in locals():
            login_data.update(hidden_fields)

        # CSRF 토큰 추가
        if csrf_token:
            login_data["_csrf"] = csrf_token

        print(f"   로그인 데이터: {list(login_data.keys())}")

        # 로그인 헤더 업데이트
        login_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": self.base_url,
            "Referer": login_page_url,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Requested-With": "XMLHttpRequest",
        }

        try:
            response = self.session.post(
                login_url,
                data=login_data,
                headers=login_headers,
                verify=False,
                timeout=30,
                allow_redirects=False,
            )

            print(f"   상태 코드: {response.status_code}")
            print(f"   응답 헤더: {dict(response.headers)}")

            # 응답 내용 분석
            if response.text:
                print(f"   응답 길이: {len(response.text)} bytes")

                # JSON 응답 확인
                try:
                    json_data = response.json()
                    print(f"   JSON 응답: {json_data}")

                    if json_data.get("success") or json_data.get("result") == "success":
                        print("   ✅ 로그인 성공 (JSON)")
                        return True
                    else:
                        print(
                            f"   ❌ 로그인 실패: {json_data.get('message', 'Unknown error')}"
                        )
                        return False
                except:
                    # HTML 응답 분석
                    if "성공" in response.text or "success" in response.text.lower():
                        print("   ✅ 로그인 성공 (HTML)")
                        return True
                    elif "실패" in response.text or "fail" in response.text.lower():
                        error_msg = re.search(
                            r"(비밀번호가?.*?[.。]|아이디가?.*?[.。])", response.text
                        )
                        if error_msg:
                            print(f"   ❌ 로그인 실패: {error_msg.group(0)}")
                        else:
                            print(f"   ❌ 로그인 실패")
                        print(f"   응답 샘플: {response.text[:500]}")
                        return False

            # 리다이렉트 처리
            if response.status_code in [301, 302, 303, 307]:
                redirect_url = response.headers.get("Location", "")
                print(f"   리다이렉트: {redirect_url}")

                if redirect_url and (
                    "main" in redirect_url.lower() or "index" in redirect_url.lower()
                ):
                    print("   ✅ 로그인 성공 (리다이렉트)")
                    return True
                elif "login" in redirect_url.lower():
                    print("   ❌ 로그인 실패 (로그인 페이지로 리다이렉트)")
                    return False

            # 세션 쿠키 확인
            print(f"   현재 쿠키: {dict(self.session.cookies)}")

        except Exception as e:
            print(f"   ❌ 로그인 오류: {e}")
            return False

        # 4. 세션 확인 (메인 페이지 접근)
        print("\n4️⃣ 세션 확인...")
        try:
            check_url = f"{self.base_url}/main"
            response = self.session.get(
                check_url, verify=False, timeout=30, allow_redirects=True
            )

            print(f"   상태: {response.status_code}")
            print(f"   최종 URL: {response.url}")

            if response.status_code == 200:
                if "login" not in response.url.lower():
                    print("   ✅ 세션 유효 - 로그인 성공")

                    # 사용자 정보 확인
                    if "nextrade" in response.text:
                        print("   ✅ 사용자 확인: nextrade")

                    return True
                else:
                    print("   ❌ 로그인 페이지로 리다이렉트됨")
                    return False

        except Exception as e:
            print(f"   ❌ 세션 확인 오류: {e}")

        return False

    def test_data_access(self):
        """데이터 접근 테스트"""
        print("\n5️⃣ 데이터 접근 테스트...")

        # 여러 가능한 URL 시도
        test_urls = [
            "/board/boardList?menuCode=HPHB0620101",  # 악성IP차단
            "/threat/blacklist",
            "/security/iplist",
            "/api/blacklist/list",
        ]

        for path in test_urls:
            url = f"{self.base_url}{path}"
            print(f"\n   시도: {url}")

            try:
                response = self.session.get(
                    url, verify=False, timeout=30, allow_redirects=True
                )

                print(f"   상태: {response.status_code}")

                if response.status_code == 200:
                    # IP 패턴 찾기
                    ip_pattern = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
                    ips = re.findall(ip_pattern, response.text)

                    if ips:
                        print(f"   ✅ {len(set(ips))}개 고유 IP 발견")
                        print(f"   샘플 IP: {list(set(ips))[:5]}")
                        return True
                    else:
                        # 다운로드 링크 찾기
                        if (
                            "download" in response.text.lower()
                            or "excel" in response.text.lower()
                        ):
                            print("   📥 다운로드 링크 발견")

            except Exception as e:
                print(f"   ❌ 오류: {e}")

        return False


def main():
    tester = REGTECHLoginTest()

    # 로그인 테스트
    login_success = tester.test_login()

    if login_success:
        print("\n" + "=" * 60)
        print("✅ 로그인 성공! 데이터 접근 테스트 진행...")
        print("=" * 60)

        # 데이터 접근 테스트
        data_success = tester.test_data_access()

        if data_success:
            print("\n✅ 데이터 접근 성공!")
        else:
            print("\n⚠️ 데이터 접근 실패 - 추가 조사 필요")
    else:
        print("\n" + "=" * 60)
        print("❌ 로그인 실패 - 자격증명 확인 필요")
        print("=" * 60)
        print("\n가능한 원인:")
        print("1. 아이디/비밀번호 오류")
        print("2. 계정 잠김 또는 만료")
        print("3. IP 차단")
        print("4. 2차 인증 필요")


if __name__ == "__main__":
    main()
