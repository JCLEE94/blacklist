#!/usr/bin/env python3
"""
SECUDIUM 간단한 수집기
환경변수 문제를 피하기 위한 독립 실행 수집기
"""
import os
import requests
import json
from datetime import datetime, timedelta
from pathlib import Path

class SimpleSecudiumCollector:
    def __init__(self):
        self.base_url = os.getenv('SECUDIUM_BASE_URL', 'https://secudium.skinfosec.co.kr')
        self.username = os.getenv('SECUDIUM_USERNAME', 'nextrade')
        self.password = os.getenv('SECUDIUM_PASSWORD', 'Sprtmxm1@3')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def collect(self):
        """데이터 수집"""
        print(f"SECUDIUM 수집 시작... (URL: {self.base_url})")
        
        # 로그인
        login_data = {
            'lang': 'ko',
            'is_otp': 'N',
            'is_expire': 'Y',
            'login_name': self.username,
            'password': self.password,
            'otp_value': ''
        }
        
        login_resp = self.session.post(
            f"{self.base_url}/isap-api/loginProcess",
            data=login_data,
            timeout=30
        )
        
        if login_resp.status_code != 200:
            print("로그인 실패")
            return []
        
        # 데이터 수집
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        params = {
            'view_count': '1000',
            'page': '1',
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        }
        
        resp = self.session.get(
            f"{self.base_url}/secinfo/black_ip",
            params=params,
            timeout=30
        )
        
        if resp.status_code != 200:
            print("데이터 수집 실패")
            return []
        
        # IP 추출
        data = resp.json()
        ips = [item.get('mal_ip') for item in data.get('list', []) if item.get('mal_ip')]
        
        print(f"수집된 IP: {len(ips)}개")
        return ips

if __name__ == "__main__":
    collector = SimpleSecudiumCollector()
    ips = collector.collect()
    
    # 결과 저장
    Path("data").mkdir(exist_ok=True)
    with open("data/secudium_ips.json", "w") as f:
        json.dump({"ips": ips, "collected_at": datetime.now().isoformat()}, f, indent=2)
