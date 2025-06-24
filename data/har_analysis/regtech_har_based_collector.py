#!/usr/bin/env python3
"""
HAR 분석 기반 실제 동작하는 REGTECH 수집 코드
"""
import requests
from datetime import datetime, timedelta

def collect_regtech_data():
    """HAR 분석 결과를 바탕으로 한 정확한 요청"""

    # 기본 설정
    base_url = "https://regtech.fsec.or.kr"
    endpoint = "/fcti/securityAdvisory/advisoryListDownloadXlsx"

    # HAR에서 추출한 정확한 헤더
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://regtech.fsec.or.kr",
        "Referer": "https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    # HAR에서 추출한 정확한 POST 파라미터
    form_data = [
        ("page", "0"),
        ("tabSort", "blacklist"),
        ("excelDownload", "security,blacklist,weakpoint,"),
        ("cveId", ""),
        ("ipId", ""),
        ("estId", ""),
        ("startDate", (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")),  # 3개월 전
        ("endDate", datetime.now().strftime("%Y%m%d")),  # 오늘
        ("findCondition", "all"),
        ("findKeyword", ""),
        ("excelDown", "security"),
        ("excelDown", "blacklist"),
        ("excelDown", "weakpoint"),
        ("size", "5000"),  # 더 많은 데이터 요청
    ]

    # 요청 실행
    session = requests.Session()
    try:
        response = session.post(
            f'{base_url}{endpoint}',
            data=form_data,
            headers=headers,
            timeout=120,  # 충분한 타임아웃
            stream=True   # 대용량 파일 처리
        )

        print(f'Status: {response.status_code}')
        print(f'Content-Type: {response.headers.get("Content-Type")}')
        print(f'Content-Disposition: {response.headers.get("Content-Disposition")}')

        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            if 'excel' in content_type or 'spreadsheet' in content_type:
                filename = f'regtech_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f'✅ Excel 파일 저장: {filename}')
                return True
            else:
                print(f'❌ 예상하지 못한 응답: {response.text[:200]}')
        else:
            print(f'❌ HTTP 오류: {response.status_code}')

    except Exception as e:
        print(f'❌ 요청 실패: {e}')

    return False

if __name__ == "__main__":
    collect_regtech_data()