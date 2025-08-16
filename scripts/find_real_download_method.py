#!/usr/bin/env python3
"""
실제 다운로드 방법 찾기
보통 웹사이트의 Excel 다운로드 구조:
1. 테이블 데이터를 AJAX로 가져옴
2. 다운로드 버튼 클릭 시 form submit 또는 window.location 변경
3. 서버에서 Excel 생성 후 다운로드
"""

import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup


def find_download_method():
    # 세션 생성 및 로그인
    session = requests.Session()
    session.headers.update(
        {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )

    # 로그인
    print("1. 로그인 중...")
    session.get("https://regtech.fsec.or.kr/login/loginForm")

    login_resp = session.post(
        "https://regtech.fsec.or.kr/login/addLogin",
        data={
            "username": "nextrade",
            "password": "test_password",
            "login_error": "",
            "txId": "",
            "token": "",
            "memberId": "",
            "smsTimeExcess": "N",
        },
    )

    if login_resp.status_code == 200:
        print("✅ 로그인 성공")

    # 보안권고 페이지 HTML 분석
    print("\n2. 보안권고 페이지 분석...")
    advisory_resp = session.get(
        "https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList"
    )
    soup = BeautifulSoup(advisory_resp.text, "html.parser")

    # JavaScript 코드에서 다운로드 함수 찾기
    print("\n3. JavaScript에서 다운로드 관련 함수 찾기:")
    scripts = soup.find_all("script")

    download_functions = []
    for script in scripts:
        if script.string:
            # 다운로드 관련 함수 패턴
            patterns = [
                r"function\s+\w*[Dd]ownload\w*\s*\([^)]*\)",
                r"function\s+\w*[Ee]xcel\w*\s*\([^)]*\)",
                r"function\s+\w*[Ee]xport\w*\s*\([^)]*\)",
                r"\.download\s*=\s*function",
                r"download\s*:\s*function",
                r"fnCmd\w*Download",
                r"fn\w*Excel",
            ]

            for pattern in patterns:
                matches = re.findall(pattern, script.string, re.IGNORECASE)
                download_functions.extend(matches)

    for func in set(download_functions):
        print(f"  - {func}")

    # 다운로드 버튼/링크 찾기
    print("\n4. 다운로드 버튼/링크 찾기:")

    # 버튼
    buttons = soup.find_all(
        ["button", "a", "input"], class_=re.compile(r"download|excel|export", re.I)
    )
    for btn in buttons:
        print(f"  버튼: {btn.get('class')} - onclick: {btn.get('onclick', '')}")

    # 텍스트로 찾기
    download_elements = soup.find_all(text=re.compile(r"다운로드|엑셀|excel|download", re.I))
    for elem in download_elements:
        parent = elem.parent
        if parent.name in ["button", "a", "span", "div"]:
            print(f"  요소: {parent.name} - {elem.strip()}")
            if parent.get("onclick"):
                print(f"    onclick: {parent.get('onclick')}")

    # 실제 JavaScript 코드 내용 확인
    print("\n5. 다운로드 함수 내용 확인:")
    for script in scripts:
        if script.string and any(
            keyword in script.string
            for keyword in ["advisoryListDownload", "excelDownload", "downloadExcel"]
        ):
            # 함수 내용 추출
            lines = script.string.split("\n")
            in_download_func = False
            func_content = []

            for line in lines:
                if (
                    any(keyword in line for keyword in ["download", "excel"])
                    and "function" in line
                ):
                    in_download_func = True
                    func_content = [line]
                elif in_download_func:
                    func_content.append(line)
                    if line.strip() == "}":
                        # 함수 끝
                        print("\n".join(func_content[:20]))  # 처음 20줄만
                        print("...")
                        in_download_func = False
                        break

    # AJAX 요청 찾기
    print("\n6. AJAX 데이터 요청 찾기:")
    for script in scripts:
        if script.string:
            # jQuery AJAX 패턴
            ajax_patterns = [
                r'\$\.ajax\s*\(\s*\{[^}]*url\s*:\s*["\']([^"\']+)',
                r'\.post\s*\(\s*["\']([^"\']+)',
                r'\.get\s*\(\s*["\']([^"\']+)',
                r'fetch\s*\(\s*["\']([^"\']+)',
            ]

            for pattern in ajax_patterns:
                matches = re.findall(pattern, script.string)
                for url in matches:
                    if "advisory" in url.lower():
                        print(f"  AJAX URL: {url}")

    # Form 찾기
    print("\n7. Form 분석:")
    forms = soup.find_all("form")
    for form in forms:
        form_id = form.get("id", "")
        form_name = form.get("name", "")
        if any(
            keyword in (form_id + form_name).lower()
            for keyword in ["download", "excel", "search"]
        ):
            print(f"  Form: id={form_id}, name={form_name}")
            print(f"    action: {form.get('action', '')}")

            # hidden inputs
            hidden_inputs = form.find_all("input", type="hidden")
            for inp in hidden_inputs:
                print(f"    hidden: {inp.get('name')} = {inp.get('value', '')}")

    # 실제 데이터 테이블 구조 확인
    print("\n8. 데이터 테이블 구조:")
    tables = soup.find_all("table")
    print(f"  테이블 수: {len(tables)}")

    for i, table in enumerate(tables):
        tbody = table.find("tbody")
        if tbody:
            rows = tbody.find_all("tr")
            print(f"  테이블 {i+1}: {len(rows)}개 행")

            # 첫 번째 행의 구조 확인
            if rows:
                first_row = rows[0]
                cells = first_row.find_all(["td", "th"])
                print(f"    컬럼 수: {len(cells)}")

                # IP 관련 컬럼 찾기
                for j, cell in enumerate(cells):
                    text = cell.get_text(strip=True)
                    if any(
                        keyword in text for keyword in ["IP", "ip", "주소", "address"]
                    ):
                        print(f"    IP 컬럼 위치: {j+1}번째")


if __name__ == "__main__":
    find_download_method()
