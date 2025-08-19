#!/usr/bin/env python3
"""
REGTECH Enhanced Collector
더 많은 데이터를 수집하기 위한 강화된 수집기
- 확장된 날짜 범위
- 다중 페이지 수집
- 다양한 검색 조건
- 여러 데이터 소스 시도
"""

import os
import re
import json
import requests
import sys
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from dotenv import load_dotenv

sys.path.insert(0, '/home/jclee/app/blacklist')
load_dotenv()

def collect_regtech_enhanced():
    """강화된 REGTECH 데이터 수집"""
    
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
        # 1. 로그인
        print(f"🔐 REGTECH 로그인: {username}")
        session.get(f'{base_url}/login/loginForm')
        
        verify_data = {'memberId': username, 'memberPw': password}
        session.headers.update({
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        
        verify_resp = session.post(f"{base_url}/member/findOneMember", data=verify_data)
        if verify_resp.status_code != 200:
            print(f"❌ 사용자 확인 실패: {verify_resp.status_code}")
            return []
        
        login_form_data = {
            'username': username, 'password': password, 'login_error': '',
            'txId': '', 'token': '', 'memberId': '', 'smsTimeExcess': 'N'
        }
        
        login_resp = session.post(f"{base_url}/login/addLogin", data=login_form_data, allow_redirects=True)
        if login_resp.status_code != 200 or 'main' not in login_resp.url:
            print("❌ 로그인 실패")
            return []
        
        print("✅ 로그인 성공")
        
        # 2. 강화된 데이터 수집
        print("\n🔍 강화된 데이터 수집 시작...")
        
        # 2-1. 확장된 날짜 범위 (6개월)
        date_ranges = [
            (180, "6개월"),  # 6개월
            (90, "3개월"),   # 3개월  
            (30, "1개월"),   # 1개월
            (7, "1주일")     # 1주일
        ]
        
        for days_back, period_name in date_ranges:
            print(f"\n📅 {period_name} 데이터 수집 중...")
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # 다중 페이지 수집 (최대 10페이지)
            for page in range(1, 11):
                print(f"  페이지 {page}/10...")
                
                # 다양한 검색 조건들
                search_conditions = [
                    {'tabSort': 'blacklist', 'findCondition': 'all', 'size': '100'},
                    {'tabSort': 'blacklist', 'findCondition': 'title', 'size': '100'},
                    {'tabSort': 'threat', 'findCondition': 'all', 'size': '100'},
                    {'tabSort': 'malware', 'findCondition': 'all', 'size': '100'},
                    {'tabSort': 'ip', 'findCondition': 'all', 'size': '100'},
                ]
                
                for condition in search_conditions:
                    page_ips = collect_single_page(
                        session, base_url, start_date, end_date, page, condition
                    )
                    
                    for ip in page_ips:
                        if ip not in collected_ips:
                            collected_ips.append(ip)
                    
                    # 요청 간 지연
                    time.sleep(0.5)
                
                # 페이지가 비어있으면 중단
                if not page_ips:
                    print(f"    페이지 {page}에서 데이터 없음, 다음 기간으로...")
                    break
        
        # 2-2. 다른 URL 경로들 시도
        alternative_urls = [
            '/board/boardList?menuCode=HPHB0620101',
            '/fcti/securityAdvisory/blackListView', 
            '/threat/blacklist/list',
            '/security/advisory/list'
        ]
        
        print(f"\n🔍 대체 URL 경로 시도...")
        for url_path in alternative_urls:
            print(f"  시도: {url_path}")
            try:
                full_url = f"{base_url}{url_path}"
                resp = session.get(full_url)
                
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    page_ips = extract_ips_from_soup(soup)
                    
                    for ip in page_ips:
                        if ip not in collected_ips:
                            collected_ips.append(ip)
                    
                    print(f"    추가 수집: {len(page_ips)}개")
            except Exception as e:
                print(f"    오류: {e}")
        
        # 2-3. Excel 다운로드 시도 (여러 날짜 범위)
        print(f"\n📥 Excel 다운로드 시도...")
        for days_back, period_name in date_ranges[:3]:  # 상위 3개 기간만
            try:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days_back)
                
                excel_url = f"{base_url}/board/excelDownload"
                excel_params = {
                    'menuCode': 'HPHB0620101',
                    'startDate': start_date.strftime('%Y%m%d'),
                    'endDate': end_date.strftime('%Y%m%d'),
                    'pageSize': '1000'  # 최대 크기
                }
                
                excel_resp = session.post(excel_url, data=excel_params, stream=True)
                
                if excel_resp.status_code == 200:
                    content_type = excel_resp.headers.get('Content-Type', '').lower()
                    if 'excel' in content_type or 'spreadsheet' in content_type:
                        excel_ips = process_excel_response(excel_resp, period_name)
                        
                        for ip in excel_ips:
                            if ip not in collected_ips:
                                collected_ips.append(ip)
                        
                        print(f"  {period_name} Excel: {len(excel_ips)}개 추가")
            except Exception as e:
                print(f"  Excel 오류 ({period_name}): {e}")
        
        print(f"\n📊 총 수집 결과: {len(collected_ips)}개 IP")
        
        # IP 데이터 형식 변환
        ip_data_list = []
        for ip in collected_ips:
            ip_data_list.append({
                "ip": ip,
                "source": "REGTECH",
                "description": "Malicious IP from REGTECH (enhanced collection)",
                "detection_date": datetime.now().strftime('%Y-%m-%d'),
                "confidence": "high"
            })
        
        return ip_data_list
    
    except Exception as e:
        print(f"❌ 수집 중 오류: {e}")
        return []
    
    finally:
        session.close()


def collect_single_page(session, base_url, start_date, end_date, page, condition):
    """단일 페이지에서 데이터 수집"""
    try:
        advisory_url = f"{base_url}/fcti/securityAdvisory/advisoryList"
        
        post_data = {
            'page': str(page),
            'rows': condition.get('size', '100'),
            'size': condition.get('size', '100'),
            'startDate': start_date.strftime('%Y%m%d'),
            'endDate': end_date.strftime('%Y%m%d'),
            'tabSort': condition.get('tabSort', 'blacklist'),
            'findCondition': condition.get('findCondition', 'all'),
            'findKeyword': condition.get('findKeyword', '')
        }
        
        session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        
        resp = session.post(advisory_url, data=post_data)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            return extract_ips_from_soup(soup)
        
        return []
    
    except Exception as e:
        print(f"    페이지 수집 오류: {e}")
        return []


def extract_ips_from_soup(soup):
    """BeautifulSoup 객체에서 IP 추출"""
    ips = []
    ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
    
    # 테이블에서 찾기
    for row in soup.select('tbody tr, table tr'):
        for cell in row.find_all(['td', 'th']):
            text = cell.get_text(strip=True)
            found_ips = ip_pattern.findall(text)
            
            for ip in found_ips:
                if is_valid_ip(ip):
                    ips.append(ip)
    
    # 전체 텍스트에서도 찾기
    all_text = soup.get_text()
    found_ips = ip_pattern.findall(all_text)
    
    for ip in found_ips:
        if is_valid_ip(ip) and ip not in ips:
            ips.append(ip)
    
    return ips


def is_valid_ip(ip):
    """IP 주소 유효성 검사"""
    try:
        octets = ip.split('.')
        if len(octets) != 4:
            return False
        
        for octet in octets:
            num = int(octet)
            if not (0 <= num <= 255):
                return False
        
        # 로컬/예약 IP 제외
        if ip.startswith(('127.', '192.168.', '10.', '172.', '0.', '255.')):
            return False
        
        # 멀티캐스트/브로드캐스트 제외
        first_octet = int(octets[0])
        if first_octet >= 224:  # 224-255는 특수 용도
            return False
        
        return True
    
    except:
        return False


def process_excel_response(excel_resp, period_name):
    """Excel 응답 처리"""
    try:
        import pandas as pd
        
        # 임시 파일로 저장
        excel_path = f"/tmp/regtech_excel_{period_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        with open(excel_path, 'wb') as f:
            for chunk in excel_resp.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Excel 파싱
        df = pd.read_excel(excel_path)
        
        ips = []
        ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        
        # 모든 컬럼에서 IP 찾기
        for col in df.columns:
            for val in df[col].dropna():
                val_str = str(val)
                found_ips = ip_pattern.findall(val_str)
                
                for ip in found_ips:
                    if is_valid_ip(ip) and ip not in ips:
                        ips.append(ip)
        
        # 임시 파일 삭제
        try:
            os.unlink(excel_path)
        except:
            pass
        
        return ips
    
    except Exception as e:
        print(f"Excel 처리 오류: {e}")
        return []


def store_collected_data(ip_data_list):
    """수집된 데이터를 PostgreSQL에 저장"""
    if not ip_data_list:
        return {"success": False, "message": "No data to store"}
    
    try:
        from src.core.data_storage_fixed import FixedDataStorage
        storage = FixedDataStorage()
        result = storage.store_ips(ip_data_list, "REGTECH")
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    print("🚀 REGTECH Enhanced Collector (더 많은 데이터)")
    print("="*60)
    
    # 데이터 수집
    ips = collect_regtech_enhanced()
    
    if ips:
        print(f"\n✅ {len(ips)}개 IP 수집 성공")
        
        # 처음 20개 표시
        print("\n처음 20개 IP:")
        for i, ip_data in enumerate(ips[:20], 1):
            print(f"  {i:2d}. {ip_data['ip']}")
        
        if len(ips) > 20:
            print(f"  ... 외 {len(ips) - 20}개")
        
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
    
    print("\n강화된 수집 완료!")