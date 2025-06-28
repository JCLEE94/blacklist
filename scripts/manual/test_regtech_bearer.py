#!/usr/bin/env python3
"""
REGTECH Bearer Token 인증 테스트
"""
import requests
import json
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta

def test_regtech_with_bearer():
    """Bearer Token을 사용한 REGTECH 데이터 수집"""
    print("🧪 REGTECH Bearer Token 인증 테스트")
    
    base_url = "https://regtech.fsec.or.kr"
    
    # PowerShell 스크립트에서 제공된 Bearer Token
    bearer_token = "BearereyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJuZXh0cmFkZSIsIm9yZ2FubmFtZSI6IuuEpeyKpO2KuOugiOydtOuTnCIsImlkIjoibmV4dHJhZGUiLCJleHAiOjE3NTExMTkyNzYsInVzZXJuYW1lIjoi7J6l7ZmN7KSAIn0.YwZHoHZCVqDnaryluB0h5_ituxYcaRz4voT7GRfgrNrP86W8TfvBuJbHMON4tJa4AQmNP-XhC_PuAVPQTjJADA"
    
    # 세션 생성
    session = requests.Session()
    
    # Bearer Token을 쿠키로 설정 (PowerShell 스크립트처럼)
    session.cookies.set('regtech-va', bearer_token, domain='regtech.fsec.or.kr', path='/')
    
    # 기본 헤더 설정
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
        'Authorization': f'Bearer {bearer_token[6:]}'  # "Bearer" 제거하고 토큰만
    })
    
    try:
        # 1. Advisory 페이지 직접 접근 (인증된 상태로)
        print("1. Advisory 페이지 접근 (Bearer Token 인증)...")
        advisory_resp = session.get(f"{base_url}/fcti/securityAdvisory/advisoryList", timeout=30)
        
        print(f"응답 상태: {advisory_resp.status_code}")
        
        if advisory_resp.status_code == 200:
            print("✅ 페이지 접근 성공")
        else:
            print(f"❌ 페이지 접근 실패: {advisory_resp.status_code}")
            return False
        
        # 2. 데이터 수집 POST 요청
        print("\n2. 데이터 수집 요청...")
        
        # 날짜 설정
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)  # 90일로 확대
        start_date_str = start_date.strftime('%Y%m%d')
        end_date_str = end_date.strftime('%Y%m%d')
        
        print(f"날짜 범위: {start_date_str} ~ {end_date_str}")
        
        # POST 데이터
        collection_data = [
            ('page', '0'),
            ('tabSort', 'blacklist'),
            ('excelDownload', ''),
            ('cveId', ''),
            ('ipId', ''),
            ('estId', ''),
            ('startDate', start_date_str),
            ('endDate', end_date_str),
            ('findCondition', 'all'),
            ('findKeyword', ''),
            ('excelDown', 'security'),
            ('excelDown', 'blacklist'),
            ('excelDown', 'weakpoint'),
            ('size', '100')
        ]
        
        collection_resp = session.post(
            f"{base_url}/fcti/securityAdvisory/advisoryList",
            data=collection_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Referer': f"{base_url}/fcti/securityAdvisory/advisoryList"
            },
            timeout=30
        )
        
        print(f"데이터 수집 응답: {collection_resp.status_code}")
        
        if collection_resp.status_code == 200:
            # 3. 응답 파싱
            soup = BeautifulSoup(collection_resp.text, 'html.parser')
            
            # IP 수집
            ip_list = []
            ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
            
            # 테이블에서 IP 찾기
            tables = soup.find_all('table')
            print(f"발견된 테이블: {len(tables)}개")
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    text = row.get_text()
                    ips = re.findall(ip_pattern, text)
                    for ip in ips:
                        # 유효한 공인 IP만 수집
                        parts = ip.split('.')
                        if (all(0 <= int(part) <= 255 for part in parts) and
                            not ip.startswith('192.168.') and
                            not ip.startswith('10.') and
                            not ip.startswith('172.') and
                            not ip.startswith('127.') and
                            not ip.startswith('0.') and
                            ip not in ip_list):
                            ip_list.append(ip)
            
            # 페이지 전체에서도 IP 검색
            all_text = soup.get_text()
            all_ips = re.findall(ip_pattern, all_text)
            
            for ip in all_ips:
                parts = ip.split('.')
                try:
                    if (all(0 <= int(part) <= 255 for part in parts) and
                        not ip.startswith('192.168.') and
                        not ip.startswith('10.') and
                        not ip.startswith('172.') and
                        not ip.startswith('127.') and
                        not ip.startswith('0.') and
                        ip not in ip_list):
                        ip_list.append(ip)
                except:
                    continue
            
            print(f"\n🎯 수집된 IP: {len(ip_list)}개")
            
            if ip_list:
                print("샘플 IP:")
                for ip in ip_list[:10]:
                    print(f"  - {ip}")
                if len(ip_list) > 10:
                    print(f"  ... 그리고 {len(ip_list) - 10}개 더")
                return True
            else:
                print("❌ IP를 찾을 수 없음")
                
                # 디버깅 정보
                if 'blacklist' in all_text.lower():
                    print("✅ 'blacklist' 키워드는 존재")
                if '총' in all_text:
                    print("✅ '총' 키워드는 존재")
                    
                # JavaScript/AJAX 확인
                if 'ajax' in all_text.lower() or 'javascript' in all_text.lower():
                    print("⚠️ JavaScript/AJAX 동적 로딩 감지")
                
                return False
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_regtech_with_bearer()
    if success:
        print("\n🎉 Bearer Token 인증으로 데이터 수집 성공!")
    else:
        print("\n💥 Bearer Token 인증 실패 또는 데이터 없음")