#!/usr/bin/env python3
"""
REGTECH Time-Based Collector
시간대별 세밀한 수집 및 다른 카테고리 탐색
- 일별 세밀한 수집
- 다른 탭 카테고리 (malware, threat, etc.)
- 실시간 vs 과거 데이터
- 다른 정렬 방식
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

def time_based_collection():
    """시간대별 세밀한 REGTECH 수집"""
    
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
    
    collected_ips = set()  # 중복 방지
    
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
            print(f"❌ 사용자 확인 실패")
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
        
        # 2. 다양한 카테고리 탐색
        print("\n🔍 다양한 카테고리 탐색...")
        
        # 2-1. 다른 탭 카테고리들
        tab_categories = [
            'blacklist',    # 기본
            'threat',       # 위협
            'malware',      # 악성코드
            'phishing',     # 피싱
            'botnet',       # 봇넷
            'exploit',      # 익스플로잇
            'ransomware',   # 랜섬웨어
            'trojan',       # 트로이목마
            'virus',        # 바이러스
            'worm',         # 웜
            'spyware',      # 스파이웨어
            'adware',       # 애드웨어
            'rootkit',      # 루트킷
            'backdoor',     # 백도어
            'keylogger',    # 키로거
            'all',          # 전체
            'recent',       # 최근
            'critical',     # 중요
            'high',         # 높음
            'medium',       # 중간
            'low'           # 낮음
        ]
        
        for category in tab_categories:
            print(f"  카테고리: {category}")
            ips = collect_by_category(session, base_url, category)
            if ips:
                collected_ips.update(ips)
                print(f"    수집: {len(ips)}개")
        
        # 2-2. 일별 세밀한 수집 (최근 30일)
        print(f"\n📅 일별 세밀한 수집 (최근 30일)...")
        
        for days_ago in range(30):
            target_date = datetime.now() - timedelta(days=days_ago)
            date_str = target_date.strftime('%Y-%m-%d')
            
            print(f"  날짜: {date_str}")
            
            # 해당 날짜만 정확히 수집
            ips = collect_by_single_date(session, base_url, target_date)
            if ips:
                collected_ips.update(ips)
                print(f"    {date_str}: {len(ips)}개 수집")
            
            time.sleep(0.5)  # 요청 간 지연
        
        # 2-3. 다른 정렬 방식
        print(f"\n🔄 다른 정렬 방식 시도...")
        
        sort_options = [
            {'sort': 'date', 'order': 'desc'},     # 날짜 내림차순
            {'sort': 'date', 'order': 'asc'},      # 날짜 오름차순
            {'sort': 'severity', 'order': 'desc'}, # 심각도 내림차순
            {'sort': 'ip', 'order': 'asc'},        # IP 오름차순
            {'sort': 'ip', 'order': 'desc'},       # IP 내림차순
            {'sort': 'source', 'order': 'asc'},    # 소스 오름차순
            {'sort': 'type', 'order': 'desc'},     # 타입 내림차순
        ]
        
        for sort_option in sort_options:
            print(f"  정렬: {sort_option}")
            ips = collect_with_sort(session, base_url, sort_option)
            if ips:
                collected_ips.update(ips)
                print(f"    정렬 수집: {len(ips)}개")
        
        # 2-4. 키워드 기반 검색
        print(f"\n🔎 키워드 기반 검색...")
        
        keywords = [
            'malicious', 'threat', 'attack', 'botnet', 'phishing',
            '악성', '위협', '공격', '봇넷', '피싱',
            'IP', 'address', '주소', 'block', '차단',
            'suspicious', '의심', 'harmful', '유해'
        ]
        
        for keyword in keywords:
            print(f"  키워드: {keyword}")
            ips = collect_by_keyword(session, base_url, keyword)
            if ips:
                collected_ips.update(ips)
                print(f"    키워드 수집: {len(ips)}개")
        
        # 2-5. 페이지 크기 변경
        print(f"\n📄 다양한 페이지 크기 시도...")
        
        page_sizes = [50, 100, 200, 500, 1000, 2000]
        
        for page_size in page_sizes:
            print(f"  페이지 크기: {page_size}")
            ips = collect_with_page_size(session, base_url, page_size)
            if ips:
                collected_ips.update(ips)
                print(f"    크기별 수집: {len(ips)}개")
        
        print(f"\n📊 시간대별 수집 결과: {len(collected_ips)}개 고유 IP")
        
        # IP 데이터 형식 변환
        ip_data_list = []
        for ip in collected_ips:
            ip_data_list.append({
                "ip": ip,
                "source": "REGTECH",
                "description": "Malicious IP from REGTECH (time-based collection)",
                "detection_date": datetime.now().strftime('%Y-%m-%d'),
                "confidence": "high"
            })
        
        return ip_data_list
    
    except Exception as e:
        print(f"❌ 시간대별 수집 중 오류: {e}")
        return []
    
    finally:
        session.close()


def collect_by_category(session, base_url, category):
    """카테고리별 수집"""
    try:
        advisory_url = f"{base_url}/fcti/securityAdvisory/advisoryList"
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        post_data = {
            'page': '1',
            'size': '1000',
            'rows': '1000',
            'startDate': start_date.strftime('%Y%m%d'),
            'endDate': end_date.strftime('%Y%m%d'),
            'tabSort': category,
            'findCondition': 'all',
            'findKeyword': ''
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
        return []


def collect_by_single_date(session, base_url, target_date):
    """단일 날짜 정확 수집"""
    try:
        advisory_url = f"{base_url}/fcti/securityAdvisory/advisoryList"
        
        date_str = target_date.strftime('%Y%m%d')
        
        post_data = {
            'page': '1',
            'size': '1000',
            'rows': '1000',
            'startDate': date_str,
            'endDate': date_str,  # 같은 날짜로 설정
            'tabSort': 'blacklist',
            'findCondition': 'all',
            'findKeyword': ''
        }
        
        resp = session.post(advisory_url, data=post_data)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            return extract_ips_from_soup(soup)
        
        return []
    
    except Exception as e:
        return []


def collect_with_sort(session, base_url, sort_option):
    """정렬 방식별 수집"""
    try:
        advisory_url = f"{base_url}/fcti/securityAdvisory/advisoryList"
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        post_data = {
            'page': '1',
            'size': '1000',
            'rows': '1000',
            'startDate': start_date.strftime('%Y%m%d'),
            'endDate': end_date.strftime('%Y%m%d'),
            'tabSort': 'blacklist',
            'findCondition': 'all',
            'findKeyword': '',
            'sortField': sort_option.get('sort', ''),
            'sortOrder': sort_option.get('order', ''),
            'orderBy': f"{sort_option.get('sort', '')} {sort_option.get('order', '')}"
        }
        
        resp = session.post(advisory_url, data=post_data)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            return extract_ips_from_soup(soup)
        
        return []
    
    except Exception as e:
        return []


def collect_by_keyword(session, base_url, keyword):
    """키워드별 수집"""
    try:
        advisory_url = f"{base_url}/fcti/securityAdvisory/advisoryList"
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)  # 키워드 검색은 더 넓은 범위
        
        post_data = {
            'page': '1',
            'size': '1000',
            'rows': '1000',
            'startDate': start_date.strftime('%Y%m%d'),
            'endDate': end_date.strftime('%Y%m%d'),
            'tabSort': 'blacklist',
            'findCondition': 'all',
            'findKeyword': keyword
        }
        
        resp = session.post(advisory_url, data=post_data)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            return extract_ips_from_soup(soup)
        
        return []
    
    except Exception as e:
        return []


def collect_with_page_size(session, base_url, page_size):
    """페이지 크기별 수집"""
    try:
        advisory_url = f"{base_url}/fcti/securityAdvisory/advisoryList"
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        post_data = {
            'page': '1',
            'size': str(page_size),
            'rows': str(page_size),
            'startDate': start_date.strftime('%Y%m%d'),
            'endDate': end_date.strftime('%Y%m%d'),
            'tabSort': 'blacklist',
            'findCondition': 'all',
            'findKeyword': ''
        }
        
        resp = session.post(advisory_url, data=post_data)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            return extract_ips_from_soup(soup)
        
        return []
    
    except Exception as e:
        return []


def extract_ips_from_soup(soup):
    """BeautifulSoup에서 IP 추출"""
    ips = []
    ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
    
    # 모든 텍스트에서 IP 찾기
    all_text = soup.get_text()
    found_ips = ip_pattern.findall(all_text)
    
    for ip in found_ips:
        if is_valid_ip(ip):
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
        if first_octet >= 224:
            return False
        
        return True
    
    except:
        return False


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
    print("🚀 REGTECH Time-Based Collector")
    print("="*60)
    
    # 시간대별 수집 실행
    ips = time_based_collection()
    
    if ips:
        print(f"\n✅ {len(ips)}개 IP 시간대별 수집 성공")
        
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
        print("\n❌ 시간대별 수집에서 데이터가 없음")
    
    print("\n📅 시간대별 수집 완료!")