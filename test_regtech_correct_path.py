#!/usr/bin/env python3
"""
REGTECH 올바른 경로로 데이터 수집 테스트
"""

import os
import sys
import re
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


def collect_regtech_data():
    """올바른 경로로 REGTECH 데이터 수집"""
    
    username = os.getenv('REGTECH_USERNAME', '')
    password = os.getenv('REGTECH_PASSWORD', '')
    base_url = "https://regtech.fsec.or.kr"
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    })
    
    # Step 1: 로그인
    logger.info(f"🔐 로그인 시작: {username}")
    login_resp = session.post(
        f"{base_url}/login/loginProcess",
        data={'loginId': username, 'loginPw': password},
        allow_redirects=True
    )
    
    if 'regtech-front' not in session.cookies:
        logger.error("❌ 로그인 실패 - 쿠키 없음")
        return []
    
    logger.info(f"✅ 로그인 성공! 쿠키: {session.cookies.get('regtech-front')[:20]}...")
    
    # Step 2: 데이터 수집 (올바른 경로)
    collected_ips = []
    page = 0
    max_pages = 10
    
    # 날짜 설정 (최근 30일)
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
    
    logger.info(f"📅 수집 기간: {start_date} ~ {end_date}")
    
    while page < max_pages:
        logger.info(f"📄 페이지 {page + 1} 수집 중...")
        
        # 올바른 엔드포인트와 파라미터
        data = {
            "page": str(page),
            "tabSort": "blacklist",
            "startDate": start_date,
            "endDate": end_date,
            "findCondition": "all",
            "findKeyword": "",
            "size": "100",
            "rows": "100",
            "excelDownload": "",
            "cveId": "",
            "ipId": "",
            "estId": "",
        }
        
        # POST 요청
        url = f"{base_url}/fcti/securityAdvisory/advisoryList"
        response = session.post(
            url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30
        )
        
        logger.info(f"   응답 상태: {response.status_code}")
        
        if response.status_code != 200:
            logger.warning(f"   ⚠️ 페이지 {page + 1} 실패")
            break
        
        # HTML 파싱
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 로그인 체크
        if "login" in response.text.lower()[:500]:
            logger.error("❌ 세션 만료 - 재로그인 필요")
            break
        
        # 테이블 찾기
        tables = soup.find_all('table')
        logger.info(f"   테이블 수: {len(tables)}")
        
        # IP 데이터 추출
        page_ips = []
        
        # 다양한 방법으로 IP 찾기
        # 1. 테이블에서 찾기
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                for cell in cells:
                    text = cell.get_text(strip=True)
                    # IP 패턴 매칭
                    if text and '.' in text:
                        parts = text.split('.')
                        if len(parts) == 4:
                            try:
                                # IP 형식 검증
                                octets = [int(p) for p in parts if p.isdigit()]
                                if len(octets) == 4 and all(0 <= o <= 255 for o in octets):
                                    ip_data = {
                                        "ip": text,
                                        "source": "REGTECH",
                                        "description": "Malicious IP from REGTECH",
                                        "detection_date": datetime.now().strftime('%Y-%m-%d'),
                                        "confidence": "high"
                                    }
                                    page_ips.append(ip_data)
                                    logger.info(f"      ✅ IP 발견: {text}")
                            except:
                                pass
        
        # 2. JavaScript 데이터에서 찾기
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'blacklist' in script.string.lower():
                # JavaScript에서 IP 패턴 찾기
                ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
                matches = ip_pattern.findall(script.string)
                for match in matches:
                    # 실제 IP인지 검증
                    octets = match.split('.')
                    try:
                        if all(0 <= int(o) <= 255 for o in octets):
                            ip_data = {
                                "ip": match,
                                "source": "REGTECH",
                                "description": "Malicious IP from REGTECH (JS)",
                                "detection_date": datetime.now().strftime('%Y-%m-%d'),
                                "confidence": "high"
                            }
                            if ip_data not in page_ips:
                                page_ips.append(ip_data)
                                logger.info(f"      ✅ IP 발견 (JS): {match}")
                    except:
                        pass
        
        # 3. Advisory 데이터 확인
        advisory_items = soup.find_all(class_=re.compile('advisory|blacklist|threat', re.I))
        logger.info(f"   Advisory 항목: {len(advisory_items)}")
        
        if page_ips:
            logger.info(f"   📊 페이지 {page + 1}에서 {len(page_ips)}개 IP 수집")
            collected_ips.extend(page_ips)
        else:
            logger.info(f"   ⚠️ 페이지 {page + 1}에서 IP를 찾을 수 없음")
            
            # 디버깅: HTML 일부 저장
            if page == 0:
                with open('regtech_first_page.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                logger.info("   첫 페이지 HTML을 regtech_first_page.html에 저장")
            
            # 더 이상 데이터가 없으면 종료
            if page > 0:
                logger.info("   더 이상 데이터 없음 - 수집 종료")
                break
        
        page += 1
    
    session.close()
    
    # 결과 요약
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 수집 결과:")
    logger.info(f"   총 {len(collected_ips)}개 IP 수집")
    
    if collected_ips:
        logger.info(f"\n🔍 처음 5개 IP:")
        for i, ip_data in enumerate(collected_ips[:5], 1):
            logger.info(f"   {i}. {ip_data['ip']}")
    
    return collected_ips


if __name__ == "__main__":
    # 실행
    collected_data = collect_regtech_data()
    
    if collected_data:
        print(f"\n✅ 성공! {len(collected_data)}개 실제 IP를 수집했습니다.")
        sys.exit(0)
    else:
        print("\n❌ 데이터를 찾을 수 없습니다. HTML 파일을 확인해보세요.")
        sys.exit(1)