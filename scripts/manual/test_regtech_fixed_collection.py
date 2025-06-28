#!/usr/bin/env python3
"""
REGTECH 수집 테스트 - HAR 분석 기반 실제 데이터 수집
"""
import requests
import json
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta

def test_regtech_collection():
    """HAR 분석 기반 실제 REGTECH 데이터 수집 테스트"""
    print("🧪 REGTECH 실제 데이터 수집 테스트 (HAR 분석 기반)")
    
    # 설정
    username = "nextrade"
    password = "Sprtmxm1@3"
    base_url = "https://regtech.fsec.or.kr"
    
    # 날짜 설정 (최근 30일)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')
    
    print(f"날짜 범위: {start_date_str} ~ {end_date_str}")
    
    # 세션 생성
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    })
    
    try:
        # 1. 로그인 수행
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
        
        # 2. HAR 분석 기반 실제 데이터 수집 요청
        print("2. 실제 데이터 수집 (HAR 분석 기반)...")
        
        # HAR에서 발견된 정확한 POST 파라미터 (실제 동작했던 요청 복사)
        # 중복 파라미터를 지원하기 위해 리스트 형태로 사용
        collection_data = [
            ('page', '0'),
            ('tabSort', 'blacklist'),
            ('excelDownload', ''),
            ('cveId', ''),
            ('ipId', ''),
            ('estId', ''),
            ('startDate', '20250601'),
            ('endDate', '20250630'),
            ('findCondition', 'all'),
            ('findKeyword', ''),
            ('excelDown', 'security'),
            ('excelDown', 'blacklist'),      # 중복 파라미터
            ('excelDown', 'weakpoint'),      # 중복 파라미터
            ('size', '10')
        ]
        
        # POST 요청 (HAR에서 확인된 실제 엔드포인트)
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
            # 3. BeautifulSoup으로 HTML 파싱
            print("3. BeautifulSoup4로 HTML 파싱...")
            soup = BeautifulSoup(collection_resp.text, 'html.parser')
            
            # 총 건수 찾기
            total_count_elem = soup.find('em', {'class': 'num'})
            if total_count_elem:
                total_count = total_count_elem.get_text(strip=True)
                print(f"📊 총 건수: {total_count}")
            
            # 테이블에서 IP 데이터 추출
            ip_list = []
            
            # 다양한 테이블 구조 확인
            tables = soup.find_all('table')
            print(f"발견된 테이블 수: {len(tables)}")
            
            for i, table in enumerate(tables):
                rows = table.find_all('tr')
                print(f"테이블 {i+1}: {len(rows)}개 행")
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) > 1:  # 헤더가 아닌 데이터 행
                        row_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                        
                        # IP 주소 패턴 찾기
                        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
                        ips_in_row = re.findall(ip_pattern, row_text)
                        
                        for ip in ips_in_row:
                            if ip not in ip_list and ip != '0.0.0.0':
                                ip_list.append(ip)
                                print(f"   📍 발견된 IP: {ip}")
            
            # 텍스트에서 직접 IP 검색 (테이블 외부에 있을 수 있음)
            all_text = soup.get_text()
            all_ips = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', all_text)
            
            for ip in all_ips:
                if ip not in ip_list and ip not in ['0.0.0.0', '127.0.0.1']:
                    # 유효한 공인 IP인지 확인
                    parts = ip.split('.')
                    if (not (parts[0] == '192' and parts[1] == '168') and  # 사설 IP 제외
                        not (parts[0] == '10') and
                        not (parts[0] == '172' and 16 <= int(parts[1]) <= 31) and
                        not parts[0] in ['0', '127', '224', '225', '226', '227', '228', '229', '230', '231', '232', '233', '234', '235', '236', '237', '238', '239']):
                        ip_list.append(ip)
            
            print(f"\n🎯 최종 수집된 IP 개수: {len(ip_list)}")
            if ip_list:
                print("샘플 IP들:")
                for ip in ip_list[:10]:  # 처음 10개만 출력
                    print(f"  - {ip}")
                
                if len(ip_list) > 10:
                    print(f"  ... 그리고 {len(ip_list) - 10}개 더")
                
                return True
            else:
                # 응답 내용 분석
                print("\n🔍 응답 내용 분석:")
                print(f"응답 길이: {len(collection_resp.text)} 바이트")
                
                # 중요한 키워드 검색
                keywords = ['blacklist', '블랙리스트', 'IP', '요주의', '총', 'table', 'tbody']
                for keyword in keywords:
                    if keyword in collection_resp.text.lower():
                        print(f"  ✅ '{keyword}' 키워드 발견")
                    else:
                        print(f"  ❌ '{keyword}' 키워드 없음")
                
                # JavaScript나 AJAX 코드 확인
                if 'ajax' in collection_resp.text.lower() or 'json' in collection_resp.text.lower():
                    print("  ⚠️ AJAX/JSON 코드 발견 - 동적 로딩 가능성")
                
                return False
        else:
            print(f"❌ 데이터 수집 실패: {collection_resp.status_code}")
            return False
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_regtech_collection()
    if success:
        print("\n🎉 REGTECH 데이터 수집 성공!")
    else:
        print("\n💥 REGTECH 데이터 수집 실패")