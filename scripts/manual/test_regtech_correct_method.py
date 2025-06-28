#!/usr/bin/env python3
"""
REGTECH 올바른 수집 방식 - 서버사이드 렌더링 방식
"""
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import time

def collect_regtech_correctly():
    """REGTECH 데이터를 올바른 방식으로 수집"""
    print("🧪 REGTECH 올바른 수집 방식 테스트")
    
    # Bearer Token
    bearer_token = "BearereyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJuZXh0cmFkZSIsIm9yZ2FubmFtZSI6IuuEpeyKpO2KuOugiIzdtOuTnCIsImlkIjoibmV4dHJhZGUiLCJleHAiOjE3NTExMTkyNzYsInVzZXJuYW1lIjoi7J6l7ZmN7KSAIn0.YwZHoHZCVqDnaryluB0h5_ituxYcaRz4voT7GRfgrNrP86W8TfvBuJbHMON4tJa4AQmNP-XhC_PuAVPQTjJADA"
    
    session = requests.Session()
    session.cookies.set('regtech-va', bearer_token, domain='regtech.fsec.or.kr', path='/')
    
    # 헤더 설정 - 일반 브라우저처럼
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    })
    
    try:
        # 날짜 범위 설정 (최근 90일)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        start_date_str = start_date.strftime('%Y%m%d')
        end_date_str = end_date.strftime('%Y%m%d')
        
        print(f"날짜 범위: {start_date_str} ~ {end_date_str}")
        
        all_ips = []
        max_pages = 10  # 최대 10페이지까지
        
        # 페이지별로 수집
        for page in range(max_pages):
            print(f"\n📄 페이지 {page + 1} 수집 중...")
            
            # 폼 데이터 - HTML의 fnPageMove() 함수 모방
            form_data = {
                'page': str(page),
                'tabSort': 'blacklist',  # 요주의 IP 탭
                'excelDownload': '',
                'cveId': '',
                'ipId': '',
                'estId': '',
                'startDate': start_date_str,
                'endDate': end_date_str,
                'findCondition': 'all',
                'findKeyword': '',
                'size': '10'  # 페이지당 10개
            }
            
            # POST 요청
            response = session.post(
                'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList',
                data=form_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': 'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList'
                },
                timeout=30
            )
            
            if response.status_code == 200:
                # HTML 파싱
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 요주의 IP 테이블 찾기
                tables = soup.find_all('table')
                ip_found_in_page = False
                
                for table in tables:
                    caption = table.find('caption')
                    if caption and '요주의 IP' in caption.text:
                        tbody = table.find('tbody')
                        if tbody:
                            rows = tbody.find_all('tr')
                            
                            for row in rows:
                                cells = row.find_all('td')
                                if len(cells) >= 6:
                                    ip = cells[0].get_text(strip=True)
                                    
                                    # IP 패턴 검증
                                    if re.match(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', ip):
                                        country = cells[1].get_text(strip=True)
                                        attack_type = cells[2].get_text(strip=True)
                                        detection_date = cells[3].get_text(strip=True)
                                        
                                        ip_entry = {
                                            'ip': ip,
                                            'country': country,
                                            'attack_type': attack_type,
                                            'detection_date': detection_date,
                                            'source': 'REGTECH'
                                        }
                                        
                                        all_ips.append(ip_entry)
                                        ip_found_in_page = True
                                        print(f"  ✅ {ip} ({country}) - {attack_type}")
                
                if not ip_found_in_page:
                    print("  ❌ 이 페이지에 IP가 없음 - 마지막 페이지일 수 있음")
                    break
                
                # 너무 빠른 요청 방지
                time.sleep(1)
                
            else:
                print(f"  ❌ 요청 실패: {response.status_code}")
                break
        
        print(f"\n🎯 총 수집된 IP: {len(all_ips)}개")
        
        if all_ips:
            # 중복 제거
            unique_ips = []
            seen = set()
            for entry in all_ips:
                if entry['ip'] not in seen:
                    unique_ips.append(entry)
                    seen.add(entry['ip'])
            
            print(f"중복 제거 후: {len(unique_ips)}개")
            
            # 수집기 코드 업데이트 제안
            print("\n📝 regtech_collector.py 업데이트 제안:")
            print("1. Bearer Token 인증 유지 ✅")
            print("2. 페이지별 POST 요청으로 데이터 수집")
            print("3. HTML 테이블에서 직접 데이터 파싱")
            print("4. JavaScript 동적 로딩 대신 서버사이드 렌더링 활용")
            
            return unique_ips
        else:
            print("❌ 수집된 IP가 없음")
            return []
            
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    collected = collect_regtech_correctly()
    if collected:
        print(f"\n✅ 성공! {len(collected)}개의 IP를 수집했습니다.")
        print("\n샘플 데이터:")
        for ip in collected[:5]:
            print(f"  - {ip['ip']} ({ip['country']}) - {ip['attack_type']}")