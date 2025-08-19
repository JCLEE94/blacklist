#!/usr/bin/env python3
"""
REGTECH blackListView 페이지 직접 접근 테스트
"""

import os
import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


def test_blacklist_view():
    """blackListView 페이지 테스트"""
    
    username = os.getenv('REGTECH_USERNAME', '')
    password = os.getenv('REGTECH_PASSWORD', '')
    base_url = "https://regtech.fsec.or.kr"
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    })
    
    # 로그인
    logger.info(f"🔐 로그인: {username}")
    login_resp = session.post(
        f"{base_url}/login/loginProcess",
        data={'loginId': username, 'loginPw': password}
    )
    
    if 'regtech-front' not in session.cookies:
        logger.error("❌ 로그인 실패")
        return
    
    logger.info("✅ 로그인 성공")
    
    # 여러 가능한 blacklist 관련 URL 시도
    urls_to_try = [
        "/fcti/securityAdvisory/blackListView",
        "/board/boardList?menuCode=HPHB0620101",
        "/ipPool/ipPoolList",
        "/blacklist/list",
        "/threat/blacklist",
        "/fcti/blacklist",
    ]
    
    for url_path in urls_to_try:
        full_url = base_url + url_path
        logger.info(f"\n📄 시도: {url_path}")
        
        try:
            resp = session.get(full_url, timeout=10)
            logger.info(f"   상태: {resp.status_code}")
            
            if resp.status_code == 200:
                # HTML 분석
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # IP 패턴 찾기
                ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
                all_ips = ip_pattern.findall(resp.text)
                
                # 유효한 IP만 필터링
                valid_ips = []
                for ip in all_ips:
                    octets = ip.split('.')
                    try:
                        if all(0 <= int(o) <= 255 for o in octets):
                            valid_ips.append(ip)
                    except:
                        pass
                
                logger.info(f"   IP 발견: {len(valid_ips)}개")
                
                if valid_ips:
                    logger.info(f"   처음 5개 IP: {valid_ips[:5]}")
                
                # 테이블 확인
                tables = soup.find_all('table')
                logger.info(f"   테이블 수: {len(tables)}")
                
                # 데이터 관련 요소 확인
                data_elements = soup.find_all(['tbody', 'ul', 'ol'])
                logger.info(f"   데이터 요소: {len(data_elements)}개")
                
                # JavaScript 데이터 확인
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string:
                        if 'blacklist' in script.string.lower() or 'iplist' in script.string.lower():
                            logger.info("   ⚡ JavaScript에서 blacklist/iplist 데이터 발견")
                            
                            # JSON 데이터 패턴 찾기
                            json_pattern = re.compile(r'\{[^}]*"ip"[^}]*\}')
                            json_matches = json_pattern.findall(script.string)
                            if json_matches:
                                logger.info(f"   JSON 데이터 발견: {len(json_matches)}개")
                
                # 성공적인 경우 HTML 저장
                if valid_ips or tables:
                    filename = f"regtech_{url_path.replace('/', '_')}.html"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(resp.text)
                    logger.info(f"   💾 HTML 저장: {filename}")
                    
                    # 데이터가 있으면 수집 시도
                    if valid_ips:
                        logger.info(f"\n✅ {url_path}에서 {len(valid_ips)}개 IP 발견!")
                        return valid_ips
                        
        except Exception as e:
            logger.error(f"   오류: {e}")
    
    logger.warning("\n⚠️ 모든 URL에서 데이터를 찾을 수 없음")
    
    # POST 요청으로 데이터 가져오기 시도
    logger.info("\n📮 POST 요청으로 시도...")
    
    post_urls = [
        ("/fcti/securityAdvisory/selectIpPoolList", {"menuCode": "HPHB0620101"}),
        ("/board/selectBoardList", {"menuCode": "HPHB0620101"}),
        ("/api/blacklist/list", {}),
    ]
    
    for url_path, params in post_urls:
        full_url = base_url + url_path
        logger.info(f"\n📄 POST 시도: {url_path}")
        
        try:
            resp = session.post(full_url, data=params, timeout=10)
            logger.info(f"   상태: {resp.status_code}")
            
            if resp.status_code == 200:
                # JSON 응답 확인
                try:
                    data = resp.json()
                    logger.info(f"   JSON 응답 받음")
                    logger.info(f"   키: {list(data.keys()) if isinstance(data, dict) else 'List'}")
                    
                    # IP 추출
                    ips = []
                    if isinstance(data, list):
                        for item in data:
                            if 'ip' in item:
                                ips.append(item['ip'])
                    elif isinstance(data, dict):
                        if 'list' in data:
                            for item in data['list']:
                                if 'ip' in item:
                                    ips.append(item['ip'])
                        elif 'data' in data:
                            for item in data['data']:
                                if 'ip' in item:
                                    ips.append(item['ip'])
                    
                    if ips:
                        logger.info(f"\n✅ {url_path}에서 {len(ips)}개 IP 발견!")
                        logger.info(f"   처음 5개: {ips[:5]}")
                        return ips
                        
                except:
                    # HTML 응답
                    logger.info("   HTML 응답")
                    
        except Exception as e:
            logger.error(f"   오류: {e}")
    
    logger.error("\n❌ 데이터를 찾을 수 없음")
    return []


if __name__ == "__main__":
    ips = test_blacklist_view()
    if ips:
        print(f"\n✅ 총 {len(ips)}개 IP 수집 성공!")
    else:
        print("\n❌ IP를 찾을 수 없음")