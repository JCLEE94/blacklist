#!/usr/bin/env python3
"""
REGTECH 수집 최종 테스트 - 페이지 접근 후 POST 요청
"""
import requests
import json
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta

def test_regtech_final():
    """REGTECH 최종 수집 테스트 - 페이지 접근 후 POST"""
    print("🧪 REGTECH 최종 수집 테스트")
    
    # 설정
    username = "nextrade"
    password = "Sprtmxm1@3"
    base_url = "https://regtech.fsec.or.kr"
    
    # 세션 생성
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    })
    
    try:
        # 1. 로그인
        print("1. 로그인...")
        main_resp = session.get(f"{base_url}/main/main", timeout=30)
        form_resp = session.get(f"{base_url}/login/loginForm", timeout=30)
        
        login_data = {
            'memberId': username,
            'memberPw': password
        }
        
        login_resp = session.post(
            f"{base_url}/login/addLogin",
            data=login_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': f"{base_url}/login/loginForm"
            },
            timeout=30
        )
        
        if login_resp.status_code != 200:
            print(f"❌ 로그인 실패: {login_resp.status_code}")
            return False
        
        print("✅ 로그인 성공")
        
        # 2. Advisory 페이지 접근 (GET 요청으로 세션 초기화)
        print("2. Advisory 페이지 접근...")
        advisory_resp = session.get(f"{base_url}/fcti/securityAdvisory/advisoryList", timeout=30)
        
        if advisory_resp.status_code != 200:
            print(f"❌ Advisory 페이지 접근 실패: {advisory_resp.status_code}")
            return False
        
        print(f"✅ Advisory 페이지 접근 성공 (응답 크기: {len(advisory_resp.text)} bytes)")
        
        # 3. 현재 날짜로 POST 요청 (데이터가 있는 최근 날짜 사용)
        print("3. 현재 날짜로 POST 요청...")
        
        # 최근 7일 범위로 테스트
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        start_date_str = start_date.strftime('%Y%m%d')
        end_date_str = end_date.strftime('%Y%m%d')
        
        print(f"   날짜 범위: {start_date_str} ~ {end_date_str}")
        
        collection_data = [
            ('page', '0'),
            ('tabSort', 'blacklist'),
            ('excelDownload', ''),
            ('cveId', ''),
            ('ipId', ''),
            ('estId', ''),
            ('startDate', start_date_str),    # 현재 날짜 사용
            ('endDate', end_date_str),        # 현재 날짜 사용
            ('findCondition', 'all'),
            ('findKeyword', ''),
            ('excelDown', 'security'),
            ('excelDown', 'blacklist'),
            ('excelDown', 'weakpoint'),
            ('size', '100')                   # 더 큰 사이즈
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
        
        print(f"POST 응답: {collection_resp.status_code} (크기: {len(collection_resp.text)} bytes)")
        
        # 4. 다양한 날짜 범위로 테스트
        date_ranges = [
            (30, "최근 30일"),
            (90, "최근 90일"), 
            (180, "최근 180일"),
            (365, "최근 1년")
        ]
        
        for days, desc in date_ranges:
            print(f"4. {desc} 범위로 테스트...")
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            start_date_str = start_date.strftime('%Y%m%d')
            end_date_str = end_date.strftime('%Y%m%d')
            
            test_data = [
                ('page', '0'),
                ('tabSort', 'blacklist'),
                ('startDate', start_date_str),
                ('endDate', end_date_str),
                ('size', '50')
            ]
            
            test_resp = session.post(
                f"{base_url}/fcti/securityAdvisory/advisoryList",
                data=test_data,
                timeout=30
            )
            
            if test_resp.status_code == 200:
                # BeautifulSoup으로 분석
                soup = BeautifulSoup(test_resp.text, 'html.parser')
                
                # IP 패턴 검색
                ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
                ips = re.findall(ip_pattern, test_resp.text)
                unique_ips = list(set(ips))
                
                # 유효한 공인 IP 필터링
                valid_ips = []
                for ip in unique_ips:
                    parts = ip.split('.')
                    try:
                        if (all(0 <= int(part) <= 255 for part in parts) and
                            not (parts[0] == '192' and parts[1] == '168') and
                            not (parts[0] == '10') and
                            not (parts[0] == '172' and 16 <= int(parts[1]) <= 31) and
                            not parts[0] in ['0', '127', '255']):
                            valid_ips.append(ip)
                    except:
                        continue
                
                print(f"   {desc}: {len(valid_ips)}개 유효 IP 발견")
                
                if valid_ips:
                    print(f"   샘플 IP: {valid_ips[:3]}")
                    return True
                
                # 키워드 검색
                keywords = ['blacklist', '블랙리스트', 'IP', '요주의', '총', 'table']
                found_keywords = [kw for kw in keywords if kw in test_resp.text.lower()]
                if found_keywords:
                    print(f"   발견된 키워드: {found_keywords}")
            
            else:
                print(f"   {desc}: 요청 실패 ({test_resp.status_code})")
        
        return False
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_regtech_final()
    if success:
        print("\n🎉 REGTECH 데이터 수집 성공!")
    else:
        print("\n💥 모든 날짜 범위에서 데이터 없음 - 사이트 정책 변경 가능성")