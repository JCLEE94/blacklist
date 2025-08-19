#!/usr/bin/env python3
"""
REGTECH advisoryList HTML 페이지에서 데이터 추출
"""

import os
import re
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


def collect_from_advisory_list():
    """advisoryList 페이지에서 데이터 수집"""
    
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
        return []
    
    logger.info("✅ 로그인 성공")
    
    # advisoryList 페이지 접근
    collected_ips = []
    page = 1
    max_pages = 10
    
    # 날짜 범위 설정
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    while page <= max_pages:
        logger.info(f"\n📄 페이지 {page} 수집 중...")
        
        # POST 요청으로 데이터 가져오기
        url = f"{base_url}/fcti/securityAdvisory/advisoryList"
        
        # 파라미터 설정
        data = {
            "page": str(page),
            "tabSort": "blacklist",  # 블랙리스트 탭
            "startDate": start_date.strftime('%Y%m%d'),
            "endDate": end_date.strftime('%Y%m%d'),
            "findCondition": "all",
            "findKeyword": "",
            "size": "100",
            "rows": "100"
        }
        
        response = session.post(
            url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            logger.warning(f"페이지 {page} 실패: {response.status_code}")
            break
        
        # HTML 파싱
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 테이블 찾기
        tables = soup.find_all('table')
        logger.info(f"테이블 수: {len(tables)}")
        
        # tbody 찾기
        tbody = soup.find('tbody')
        if tbody:
            rows = tbody.find_all('tr')
            logger.info(f"행 수: {len(rows)}")
            
            for row in rows:
                cells = row.find_all('td')
                for cell in cells:
                    text = cell.get_text(strip=True)
                    
                    # IP 패턴 매칭
                    ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
                    ips = ip_pattern.findall(text)
                    
                    for ip in ips:
                        # IP 유효성 검사
                        octets = ip.split('.')
                        try:
                            if all(0 <= int(o) <= 255 for o in octets):
                                ip_data = {
                                    "ip": ip,
                                    "source": "REGTECH",
                                    "description": "Malicious IP from advisoryList",
                                    "detection_date": datetime.now().strftime('%Y-%m-%d'),
                                    "confidence": "high"
                                }
                                if ip_data not in collected_ips:
                                    collected_ips.append(ip_data)
                                    logger.info(f"  ✅ IP 발견: {ip}")
                        except:
                            pass
        
        # div나 ul/li 구조에서도 찾기
        advisory_items = soup.find_all(['div', 'ul', 'li'], class_=re.compile('advisory|blacklist|threat|ip', re.I))
        
        for item in advisory_items:
            text = item.get_text(strip=True)
            ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
            ips = ip_pattern.findall(text)
            
            for ip in ips:
                octets = ip.split('.')
                try:
                    if all(0 <= int(o) <= 255 for o in octets):
                        ip_data = {
                            "ip": ip,
                            "source": "REGTECH",
                            "description": "Malicious IP from advisoryList",
                            "detection_date": datetime.now().strftime('%Y-%m-%d'),
                            "confidence": "high"
                        }
                        if ip_data not in collected_ips:
                            collected_ips.append(ip_data)
                            logger.info(f"  ✅ IP 발견: {ip}")
                except:
                    pass
        
        # JavaScript 데이터에서도 찾기
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # JSON 형태의 데이터 찾기
                if 'ipList' in script.string or 'blacklist' in script.string.lower():
                    ip_pattern = re.compile(r'"ip"\s*:\s*"([^"]+)"')
                    matches = ip_pattern.findall(script.string)
                    for ip in matches:
                        if '.' in ip:
                            ip_data = {
                                "ip": ip.split('/')[0] if '/' in ip else ip,
                                "source": "REGTECH",
                                "description": "Malicious IP from advisoryList JS",
                                "detection_date": datetime.now().strftime('%Y-%m-%d'),
                                "confidence": "high"
                            }
                            if ip_data not in collected_ips:
                                collected_ips.append(ip_data)
                                logger.info(f"  ✅ IP 발견 (JS): {ip}")
        
        # 데이터가 없으면 종료
        if page == 1 and not collected_ips:
            # 첫 페이지 HTML 저장 (디버깅용)
            with open('regtech_advisory_list.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            logger.info("첫 페이지 HTML 저장: regtech_advisory_list.html")
            
            # HTML에서 특정 텍스트 패턴 찾기
            if '데이터가 없습니다' in response.text or 'No data' in response.text:
                logger.warning("페이지에 데이터가 없다고 표시됨")
            
            break
        
        if not collected_ips:
            logger.info(f"페이지 {page}에서 더 이상 데이터 없음")
            break
        
        page += 1
    
    session.close()
    
    # 결과
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 총 {len(collected_ips)}개 IP 수집")
    
    if collected_ips:
        logger.info("\n처음 10개 IP:")
        for i, ip_data in enumerate(collected_ips[:10], 1):
            logger.info(f"  {i}. {ip_data['ip']}")
    
    return collected_ips


if __name__ == "__main__":
    ips = collect_from_advisory_list()
    
    if ips:
        print(f"\n✅ 성공! {len(ips)}개 실제 IP 수집")
        
        # PostgreSQL에 저장
        from src.core.data_storage_fixed import FixedDataStorage
        storage = FixedDataStorage()
        result = storage.store_ips(ips, "REGTECH")
        
        if result.get("success"):
            print(f"✅ PostgreSQL 저장 완료: {result.get('imported_count')}개")
        else:
            print(f"❌ 저장 실패: {result.get('error')}")
    else:
        print("\n❌ 데이터를 찾을 수 없음. HTML 파일을 확인하세요.")