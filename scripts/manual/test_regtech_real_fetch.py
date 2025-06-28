#!/usr/bin/env python3
"""
REGTECH 실제 브라우저 fetch 요청 재현
"""
import requests
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup

def test_real_fetch():
    """브라우저에서 캡처한 실제 fetch 요청 재현"""
    print("🧪 REGTECH 실제 fetch 요청 테스트")
    
    # Bearer Token
    bearer_token = "BearereyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJuZXh0cmFkZSIsIm9yZ2FubmFtZSI6IuuEpeyKpO2KuOugiIydtOuTnCIsImlkIjoibmV4dHJhZGUiLCJleHAiOjE3NTExMTkyNzYsInVzZXJuYW1lIjoi7J6l7ZmN7KSAIn0.YwZHoHZCVqDnaryluB0h5_ituxYcaRz4voT7GRfgrNrP86W8TfvBuJbHMON4tJa4AQmNP-XhC_PuAVPQTjJADA"
    
    # 세션 생성
    session = requests.Session()
    
    # Bearer Token 쿠키 설정
    session.cookies.set('regtech-va', bearer_token, domain='regtech.fsec.or.kr', path='/')
    
    # 브라우저와 동일한 헤더 설정
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'no-cache',
        'content-type': 'application/x-www-form-urlencoded',
        'pragma': 'no-cache',
        'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'referer': 'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList'
    }
    
    # 날짜 설정
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')
    
    # 브라우저와 동일한 POST 데이터 (날짜 추가)
    form_data = {
        'page': '0',
        'tabSort': 'blacklist',
        'excelDownload': '',
        'cveId': '',
        'ipId': '',
        'estId': '',
        'startDate': start_date_str,  # 날짜 추가
        'endDate': end_date_str,      # 날짜 추가
        'findCondition': 'all',
        'findKeyword': '',
        'excelDown': ['security', 'blacklist', 'weakpoint'],  # 리스트로 처리
        'size': '100'  # 더 많은 데이터 요청
    }
    
    try:
        print(f"날짜 범위: {start_date_str} ~ {end_date_str}")
        print("요청 보내는 중...")
        
        # POST 요청
        response = session.post(
            'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList',
            headers=headers,
            data=form_data,
            timeout=30
        )
        
        print(f"응답 상태: {response.status_code}")
        print(f"응답 크기: {len(response.text)} bytes")
        
        if response.status_code == 200:
            # BeautifulSoup으로 파싱
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # IP 패턴 검색
            ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
            
            # 1. 테이블 검색
            tables = soup.find_all('table')
            print(f"\n발견된 테이블: {len(tables)}개")
            
            ip_list = []
            
            for i, table in enumerate(tables):
                # 테이블 클래스나 ID 확인
                table_attrs = f"class={table.get('class', 'N/A')} id={table.get('id', 'N/A')}"
                print(f"테이블 {i+1}: {table_attrs}")
                
                rows = table.find_all('tr')
                print(f"  행 수: {len(rows)}")
                
                # 헤더 확인
                headers = table.find_all('th')
                if headers:
                    header_text = [h.get_text(strip=True) for h in headers[:5]]
                    print(f"  헤더: {header_text}")
                
                # 데이터 행 처리
                for row in rows[1:]:  # 헤더 제외
                    cells = row.find_all(['td', 'th'])
                    if cells:
                        row_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                        
                        # IP 찾기
                        ips = re.findall(ip_pattern, row_text)
                        for ip in ips:
                            # 유효한 공인 IP만
                            parts = ip.split('.')
                            if (all(0 <= int(part) <= 255 for part in parts) and
                                not ip.startswith('192.168.') and
                                not ip.startswith('10.') and
                                not ip.startswith('172.') and
                                not ip.startswith('127.') and
                                not ip.startswith('0.') and
                                ip not in ip_list):
                                ip_list.append(ip)
                                print(f"    IP 발견: {ip}")
            
            # 2. 데이터 영역 검색
            data_divs = soup.find_all('div', class_=re.compile(r'(data|list|content|result)', re.I))
            print(f"\n데이터 영역: {len(data_divs)}개")
            
            for div in data_divs[:3]:
                div_class = div.get('class', [])
                print(f"  {div_class}")
            
            # 3. 전체 텍스트에서 IP 검색
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
            
            print(f"\n🎯 총 발견된 IP: {len(ip_list)}개")
            
            if ip_list:
                print("샘플 IP:")
                for ip in ip_list[:10]:
                    print(f"  - {ip}")
                if len(ip_list) > 10:
                    print(f"  ... 그리고 {len(ip_list) - 10}개 더")
                return True
            else:
                # 디버깅 정보
                print("\n🔍 추가 분석:")
                
                # 특정 텍스트 패턴 검색
                if '총' in all_text and '건' in all_text:
                    # 총 N건 패턴 찾기
                    total_pattern = r'총\s*(\d+)\s*건'
                    matches = re.findall(total_pattern, all_text)
                    if matches:
                        print(f"총 건수 표시: {matches}")
                
                # 페이지네이션 확인
                pagination = soup.find_all(class_=re.compile(r'(page|paging|pagination)', re.I))
                if pagination:
                    print(f"페이지네이션 발견: {len(pagination)}개")
                
                # JavaScript 확인
                scripts = soup.find_all('script')
                js_keywords = ['ajax', 'load', 'fetch', 'blacklist', 'getData']
                for keyword in js_keywords:
                    for script in scripts:
                        if script.string and keyword in script.string:
                            print(f"JavaScript '{keyword}' 키워드 발견")
                            break
                
                # 숨겨진 필드 확인
                hidden_inputs = soup.find_all('input', type='hidden')
                if hidden_inputs:
                    print(f"\n숨겨진 필드 {len(hidden_inputs)}개:")
                    for inp in hidden_inputs[:5]:
                        print(f"  {inp.get('name', 'N/A')} = {inp.get('value', 'N/A')}")
                
                # 응답 일부 저장
                with open('regtech_fetch_response.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print("\n💾 응답이 regtech_fetch_response.html로 저장됨")
                
                return False
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_real_fetch()
    if success:
        print("\n🎉 데이터 수집 성공!")
    else:
        print("\n💥 데이터를 찾을 수 없음 - JavaScript 동적 로딩")