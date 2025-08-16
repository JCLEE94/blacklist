#!/usr/bin/env python3
"""
SECUDIUM 및 REGTECH API 테스트 스크립트
Postman collection JSON 파일을 분석하여 API 테스트
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest
import requests

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent.parent
document_dir = project_root / "document"

# Add project root to path
sys.path.append(str(project_root))
from src.config.settings import settings


def analyze_postman_collection(json_file):
    """
    Postman collection JSON 파일 분석
    """
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"\n📄 Collection: {data['info']['name']}")

    endpoints = []

    # 재귀적으로 아이템 탐색
    def extract_items(items, parent_name=""):
        for item in items:
            if "item" in item:
                # 폴더인 경우
                folder_name = item.get("name", "")
                extract_items(
                    item["item"],
                    "{parent_name}/{folder_name}" if parent_name else folder_name,
                )
            elif "request" in item:
                # 요청인 경우
                request = item["request"]
                endpoint = {
                    "name": item.get("name", ""),
                    "method": request.get("method", ""),
                    "url": request.get("url", ""),
                    "headers": request.get("header", []),
                    "body": request.get("body", {}),
                    "parent": parent_name,
                }
                endpoints.append(endpoint)

    extract_items(data.get("item", []))

    return endpoints


def test_regtech_apis():
    """
    REGTECH API 테스트
    """
    print("\n🎯 REGTECH API 테스트")

    regtech_file = document_dir / "regtech.json"
    if not regtech_file.exists():
        print("❌ regtech.json 파일을 찾을 수 없습니다.")
        return

    endpoints = analyze_postman_collection(regtech_file)

    print(f"\n📁 총 {len(endpoints)}개 엔드포인트 발견:")

    # 주요 엔드포인트 표시
    for i, ep in enumerate(endpoints, 1):
        url = ep["url"]
        if isinstance(url, dict):
            url_str = url.get("raw", "")
        else:
            url_str = str(url)

        print(f"\n{i}. {ep['name']}")
        print(f"   Method: {ep['method']}")
        print(f"   URL: {url_str}")

        # 로그인 관련 엔드포인트 특별 표시
        if "login" in url_str.lower() or "auth" in url_str.lower():
            print("   🔑 로그인 관련 엔드포인트")

            # body 정보 확인
            body = ep.get("body", {})
            if body.get("mode") == "urlencoded":
                params = body.get("urlencoded", [])
                if params:
                    print("   📝 파라미터:")
                    for param in params:
                        print(f"      - {param.get('key')}: {param.get('value', '')}")


def test_secudium_apis():
    """
    SECUDIUM API 테스트
    """
    print("\n🎯 SECUDIUM API 테스트")

    secudium_file = document_dir / "secudium.json"
    if not secudium_file.exists():
        print("❌ secudium.json 파일을 찾을 수 없습니다.")
        return

    endpoints = analyze_postman_collection(secudium_file)

    print(f"\n📁 총 {len(endpoints)}개 엔드포인트 발견:")

    # 주요 엔드포인트 표시
    for i, ep in enumerate(endpoints, 1):
        url = ep["url"]
        if isinstance(url, dict):
            url_str = url.get("raw", "")
        else:
            url_str = str(url)

        print(f"\n{i}. {ep['name']}")
        print(f"   Method: {ep['method']}")
        print(f"   URL: {url_str}")

        # 로그인 관련 엔드포인트 특별 표시
        if "login" in url_str.lower() or "auth" in url_str.lower():
            print("   🔑 로그인 관련 엔드포인트")

            # body 정보 확인
            body = ep.get("body", {})
            if body.get("mode") == "urlencoded":
                params = body.get("urlencoded", [])
                if params:
                    print("   📝 파라미터:")
                    for param in params:
                        print(f"      - {param.get('key')}: {param.get('value', '')}")


@pytest.mark.integration
@pytest.mark.skip(reason="External API test - skip in CI/CD")
def test_regtech_login():
    """
    REGTECH 로그인 테스트
    """
    print("\n🔐 REGTECH 로그인 테스트")

    username = settings.regtech_username or "test_username"
    password = settings.regtech_password or "test_password"

    print(f"   Username: {username}")
    print(f"   Password: {'*' * len(password)}")

    # 기본 REGTECH URL
    base_url = "https://regtech.fsec.or.kr"

    # 세션 생성
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        }
    )

    try:
        # 1. 메인 페이지 접속
        print("\n1. 메인 페이지 접속...")
        resp = session.get("{base_url}/main/main")
        print(f"   Status: {resp.status_code}")

        # 2. 로그인 페이지 확인
        print("\n2. 로그인 페이지 확인...")
        login_page = session.get("{base_url}/login/login")
        print(f"   Status: {login_page.status_code}")

        # 3. 로그인 시도
        print("\n3. 로그인 시도...")
        login_data = {"loginId": username, "loginPw": password}

        login_resp = session.post(
            "{base_url}/login/loginProcess",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        print(f"   Status: {login_resp.status_code}")
        if login_resp.status_code == 200:
            print("   ✅ 로그인 성공!")

            # 4. 블랙리스트 페이지 접근
            print("\n4. 블랙리스트 페이지 테스트...")
            blacklist_resp = session.get(
                "{base_url}/fcti/securityAdvisory/blackListView"
            )
            print(f"   Status: {blacklist_resp.status_code}")

            if blacklist_resp.status_code == 200:
                print("   ✅ 블랙리스트 페이지 접근 성공!")
                # HTML에서 IP 개수 확인
                if "blackListView" in blacklist_resp.text:
                    print("   📄 블랙리스트 컨텐츠 확인됨")
        else:
            print("   ❌ 로그인 실패")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")

    finally:
        session.close()


def main():
    """
    메인 함수
    """
    print("🔍 API 분석 및 테스트 시작")
    print(f"   시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # REGTECH API 분석
    test_regtech_apis()

    # SECUDIUM API 분석
    test_secudium_apis()

    # REGTECH 로그인 테스트
    print("\n" + "=" * 60)
    choice = input("\nREGTECH 로그인 테스트를 실행하시겠습니까? (y/n): ")
    if choice.lower() == "y":
        test_regtech_login()

    print("\n✅ 분석 및 테스트 완료!")


if __name__ == "__main__":
    main()
