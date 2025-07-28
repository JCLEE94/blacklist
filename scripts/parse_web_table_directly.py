#!/usr/bin/env python3
"""
웹 페이지 테이블에서 직접 IP 파싱
Excel 다운로드가 안 되면 테이블에서 직접 추출
"""

import json
import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup


def extract_ips_from_web():
    # 세션 생성 및 로그인
    session = requests.Session()
    session.headers.update(
        {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    )

    # 로그인
    print("1. 로그인 중...")
    session.get('https://regtech.fsec.or.kr/login/loginForm')
    login_resp = session.post(
        'https://regtech.fsec.or.kr/login/addLogin',
        data={
            'username': 'nextrade',
            'password': 'Sprtmxm1@3',
            'login_error': '',
            'txId': '',
            'token': '',
            'memberId': '',
            'smsTimeExcess': 'N',
        },
    )

    if login_resp.status_code == 200:
        print("✅ 로그인 성공")

    # 날짜 설정 (최근 90일)
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')

    all_ips = []
    page = 1

    while True:
        print(f"\n2. {page}페이지 데이터 수집 중...")

        # 보안권고 목록 조회
        list_url = 'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList'
        params = {
            'startDate': start_date,
            'endDate': end_date,
            'blockRule': '',
            'blockTarget': '',
            'page': str(page),
            'rows': '100',  # 페이지당 100개
        }

        resp = session.get(list_url, params=params)

        if resp.status_code != 200:
            print(f"❌ 페이지 로드 실패: {resp.status_code}")
            break

        soup = BeautifulSoup(resp.text, 'html.parser')

        # 테이블 찾기
        table = soup.find('table')
        if not table:
            print("테이블을 찾을 수 없습니다.")
            break

        tbody = table.find('tbody')
        if not tbody:
            print("tbody를 찾을 수 없습니다.")
            break

        rows = tbody.find_all('tr')
        if not rows:
            print("더 이상 데이터가 없습니다.")
            break

        print(f"  {len(rows)}개 행 발견")

        # 각 행에서 IP 추출
        for row in rows:
            cells = row.find_all(['td', 'th'])

            # IP 패턴 찾기
            ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')

            for cell in cells:
                text = cell.get_text(strip=True)

                # IP 주소 찾기
                ips = ip_pattern.findall(text)
                for ip in ips:
                    # 유효한 IP인지 확인
                    parts = ip.split('.')
                    if all(0 <= int(part) <= 255 for part in parts):
                        # 로컬 IP 제외
                        if not ip.startswith(
                            ('0.', '10.', '127.', '169.254.', '172.16.', '192.168.')
                        ):
                            ip_info = {
                                'ip': ip,
                                'source': 'REGTECH',
                                'detection_date': datetime.now().strftime('%Y-%m-%d'),
                                'page': page,
                                'row_text': text[:100],  # 컨텍스트 저장
                            }
                            all_ips.append(ip_info)
                            print(f"    IP 발견: {ip}")

        # 다음 페이지 확인
        next_button = soup.find('a', text='다음') or soup.find('a', class_='next')
        if not next_button or len(rows) < 100:
            print("\n마지막 페이지입니다.")
            break

        page += 1

        # 페이지 제한 (안전장치)
        if page > 10:
            print("\n페이지 제한에 도달했습니다.")
            break

    # 결과 저장
    print(f"\n3. 수집 완료: 총 {len(all_ips)}개 IP")

    if all_ips:
        # JSON 파일로 저장
        output_file = f'regtech_web_ips_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(
                {
                    'source': 'REGTECH',
                    'collected_at': datetime.now().isoformat(),
                    'total_ips': len(all_ips),
                    'start_date': start_date,
                    'end_date': end_date,
                    'ips': all_ips,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        print(f"✅ 파일 저장: {output_file}")

        # 중복 제거된 IP 목록
        unique_ips = list(set(item['ip'] for item in all_ips))
        print(f"\n중복 제거 후: {len(unique_ips)}개 고유 IP")

        # 샘플 출력
        print("\n샘플 IP (처음 10개):")
        for ip in unique_ips[:10]:
            print(f"  - {ip}")

        return unique_ips
    else:
        print("❌ IP를 찾을 수 없습니다.")

        # 디버깅을 위해 첫 페이지 HTML 저장
        debug_file = 'regtech_debug.html'
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(resp.text)
        print(f"\n디버깅을 위해 HTML 저장: {debug_file}")

        return []


if __name__ == "__main__":
    ips = extract_ips_from_web()
