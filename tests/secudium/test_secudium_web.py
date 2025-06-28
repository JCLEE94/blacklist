#!/usr/bin/env python3
"""
SECUDIUM 웹사이트 구조 분석
"""
import requests
from bs4 import BeautifulSoup
import re

def analyze_secudium():
    """SECUDIUM 웹사이트 분석"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    print("1. 보호나라 메인 페이지 분석...")
    try:
        resp = session.get("https://www.boho.or.kr")
        print(f"   상태 코드: {resp.status_code}")
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 로그인 폼 찾기
            login_forms = soup.find_all('form')
            print(f"   폼 개수: {len(login_forms)}")
            
            # 링크 분석
            links = soup.find_all('a', href=True)
            blacklist_links = []
            for link in links:
                href = link['href']
                text = link.text.strip()
                if any(keyword in text.lower() for keyword in ['black', '차단', 'ip', '탐지', '공격']):
                    blacklist_links.append((text, href))
            
            if blacklist_links:
                print("\n   블랙리스트 관련 링크:")
                for text, href in blacklist_links[:5]:
                    print(f"      {text}: {href}")
            
            # JavaScript 분석
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and ('login' in script.string or 'api' in script.string):
                    print("\n   로그인/API 관련 스크립트 발견")
                    api_patterns = re.findall(r'["\']([^"\']*api[^"\']*)["\']', script.string)
                    for pattern in api_patterns[:5]:
                        print(f"      API 패턴: {pattern}")
                        
    except Exception as e:
        print(f"   오류: {e}")
    
    print("\n2. KISA 사이버위협정보 분석...")
    kisa_urls = [
        "https://www.krcert.or.kr",
        "https://www.boho.or.kr/kr/bbs/list.do?menuNo=205020&bbsId=B0000133",
        "https://www.boho.or.kr/kr/bbs/list.do?bbsId=B0000133&menuNo=205020"
    ]
    
    for url in kisa_urls:
        print(f"\n   URL 시도: {url}")
        try:
            resp = session.get(url, timeout=10)
            print(f"      상태 코드: {resp.status_code}")
            
            if resp.status_code == 200 and 'ip' in resp.text.lower():
                # IP 패턴 찾기
                ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
                ips = ip_pattern.findall(resp.text)
                if ips:
                    print(f"      IP 발견: {len(set(ips))}개")
                    print(f"      샘플: {list(set(ips))[:3]}")
        except Exception as e:
            print(f"      오류: {e}")
    
    print("\n3. C-TAS 시스템 확인...")
    ctas_urls = [
        "https://www.krcert.or.kr/data/secNoticeList.do",
        "https://www.krcert.or.kr/data/trendView.do"
    ]
    
    for url in ctas_urls:
        print(f"\n   URL: {url}")
        try:
            resp = session.get(url, timeout=10)
            print(f"      상태 코드: {resp.status_code}")
        except Exception as e:
            print(f"      오류: {e}")

if __name__ == "__main__":
    analyze_secudium()