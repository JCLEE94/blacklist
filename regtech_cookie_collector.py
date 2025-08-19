#!/usr/bin/env python3
"""
REGTECH 실제 쿠키 수집 스크립트
브라우저에서 복사한 쿠키로 데이터 수집
"""

import requests
import json
import re
from datetime import datetime, timedelta

# 여기에 브라우저에서 복사한 쿠키 문자열 입력
COOKIE_STRING = ""  # 예: "JSESSIONID=ABC123; regtech-front=XYZ789"

def collect_with_cookies():
    session = requests.Session()
    
    # 쿠키 설정
    if COOKIE_STRING:
        for cookie in COOKIE_STRING.split(';'):
            if '=' in cookie:
                name, value = cookie.strip().split('=', 1)
                session.cookies.set(name, value)
    
    # 헤더 설정
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://regtech.fsec.or.kr/'
    })
    
    # 데이터 수집 시도
    urls = [
        'https://regtech.fsec.or.kr/board/boardList?menuCode=HPHB0620101',
        'https://regtech.fsec.or.kr/main',
        'https://regtech.fsec.or.kr/api/blacklist/list'
    ]
    
    for url in urls:
        try:
            response = session.get(url, verify=False, timeout=30)
            print(f"URL: {url}")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                # IP 패턴 찾기
                ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
                ips = re.findall(ip_pattern, response.text)
                
                if ips:
                    unique_ips = list(set(ips))[:10]  # 처음 10개
                    print(f"Found IPs: {unique_ips}")
                    
                    # 결과 저장
                    result = {
                        'source': 'REGTECH',
                        'url': url,
                        'collected_at': datetime.now().isoformat(),
                        'ips': unique_ips
                    }
                    
                    filename = f"regtech_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    with open(filename, 'w') as f:
                        json.dump(result, f, indent=2)
                    
                    print(f"Saved: {filename}")
                    break
                    
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    if not COOKIE_STRING:
        print("⚠️ COOKIE_STRING 변수에 브라우저 쿠키를 설정하세요")
    else:
        collect_with_cookies()
