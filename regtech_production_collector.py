#!/usr/bin/env python3
"""
REGTECH Production Collector
성공한 로그인 방식을 사용하는 프로덕션용 수집기
"""

import os
import re
import json
import requests
import sys
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, '/home/jclee/app/blacklist')

load_dotenv()

def collect_regtech_production():
    """프로덕션용 REGTECH 데이터 수집"""
    
    username = os.getenv('REGTECH_USERNAME', '')
    password = os.getenv('REGTECH_PASSWORD', '')
    
    if not username or not password:
        print("❌ REGTECH 자격증명이 설정되지 않음")
        return []
    
    base_url = "https://regtech.fsec.or.kr"
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    })
    
    collected_ips = []
    
    try:
        # 1. 로그인 페이지 접속
        print(f"🔐 REGTECH 로그인: {username}")
        session.get(f'{base_url}/login/loginForm')
        
        # 2. 사용자 확인
        verify_data = {
            'memberId': username,
            'memberPw': password
        }
        
        session.headers.update({
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        
        verify_resp = session.post(f"{base_url}/member/findOneMember", data=verify_data)
        if verify_resp.status_code != 200:
            print(f"❌ 사용자 확인 실패: {verify_resp.status_code}")
            return []
        
        print("✅ 사용자 확인 성공")
        
        # 3. 실제 로그인
        login_form_data = {
            'username': username,
            'password': password,
            'login_error': '',
            'txId': '',
            'token': '',
            'memberId': '',
            'smsTimeExcess': 'N'
        }
        
        login_resp = session.post(f"{base_url}/login/addLogin", data=login_form_data, allow_redirects=True)
        
        if login_resp.status_code != 200 or 'main' not in login_resp.url:
            print("❌ 로그인 실패")
            return []
        
        print("✅ 로그인 성공")
        
        # 4. 데이터 수집
        print("\n🔍 데이터 수집 중...")
        
        # 날짜 범위 설정 (최근 30일)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Advisory List에서 수집
        advisory_url = f"{base_url}/fcti/securityAdvisory/advisoryList"
        
        post_data = {
            'page': '1',
            'size': '100',
            'rows': '100',
            'startDate': start_date.strftime('%Y%m%d'),
            'endDate': end_date.strftime('%Y%m%d'),
            'tabSort': 'blacklist',
            'findCondition': 'all',
            'findKeyword': ''
        }
        
        session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        
        list_resp = session.post(advisory_url, data=post_data)
        
        if list_resp.status_code == 200:
            soup = BeautifulSoup(list_resp.text, 'html.parser')
            
            # IP 패턴 매칭
            ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
            
            # 테이블 행에서 IP 찾기
            rows = soup.select('tbody tr')
            print(f"  테이블 행: {len(rows)}개")
            
            for row in rows:
                cells = row.find_all('td')
                for cell in cells:
                    text = cell.get_text(strip=True)
                    ips = ip_pattern.findall(text)
                    
                    for ip in ips:
                        octets = ip.split('.')
                        try:
                            if all(0 <= int(o) <= 255 for o in octets):
                                # 로컬/예약 IP 제외
                                if not ip.startswith(('127.', '192.168.', '10.', '172.', '0.')):
                                    if ip not in collected_ips:
                                        collected_ips.append(ip)
                        except:
                            pass
            
            print(f"  수집된 IP: {len(collected_ips)}개")
        
        # 5. IP 데이터 형식 변환
        ip_data_list = []
        for ip in collected_ips:
            ip_data_list.append({
                "ip": ip,
                "source": "REGTECH",
                "description": "Malicious IP from REGTECH advisory",
                "detection_date": datetime.now().strftime('%Y-%m-%d'),
                "confidence": "high"
            })
        
        return ip_data_list
    
    except Exception as e:
        print(f"❌ 수집 중 오류: {e}")
        return []
    
    finally:
        session.close()


def store_collected_data(ip_data_list):
    """수집된 데이터를 PostgreSQL에 저장"""
    if not ip_data_list:
        print("저장할 데이터가 없음")
        return {"success": False, "message": "No data to store"}
    
    try:
        from src.core.data_storage_fixed import FixedDataStorage
        storage = FixedDataStorage()
        result = storage.store_ips(ip_data_list, "REGTECH")
        return result
    except Exception as e:
        print(f"❌ 저장 중 오류: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    print("🚀 REGTECH Production Collector")
    print("="*60)
    
    # 데이터 수집
    ips = collect_regtech_production()
    
    if ips:
        print(f"\n✅ {len(ips)}개 IP 수집 성공")
        
        # 처음 10개 표시
        print("\n처음 10개 IP:")
        for i, ip_data in enumerate(ips[:10], 1):
            print(f"  {i}. {ip_data['ip']}")
        
        # PostgreSQL에 저장
        result = store_collected_data(ips)
        
        if result.get("success"):
            print(f"\n✅ PostgreSQL 저장 완료:")
            print(f"  - 신규 저장: {result.get('imported_count', 0)}개")
            print(f"  - 중복 제외: {result.get('duplicate_count', 0)}개")
            print(f"  - 전체 DB: {result.get('total_count', 0)}개")
        else:
            print(f"\n❌ 저장 실패: {result.get('error', 'Unknown error')}")
    else:
        print("\n❌ 수집된 데이터가 없음")
    
    print("\n수집 완료!")