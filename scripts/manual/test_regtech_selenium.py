#!/usr/bin/env python3
"""
REGTECH Selenium 기반 수집 테스트
JavaScript 동적 렌더링 처리
"""
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("❌ Selenium이 설치되지 않았습니다.")
    print("설치: pip install selenium")

import time
import re
from datetime import datetime, timedelta

def test_regtech_with_selenium():
    """Selenium을 사용한 REGTECH 데이터 수집"""
    if not SELENIUM_AVAILABLE:
        return False
        
    print("🧪 REGTECH Selenium 테스트")
    
    # Chrome 옵션 설정
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 헤드리스 모드
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    try:
        # WebDriver 생성
        driver = webdriver.Chrome(options=chrome_options)
        print("✅ Chrome WebDriver 생성 성공")
        
        # 1. 메인 페이지 접속
        print("\n1. 메인 페이지 접속...")
        driver.get("https://regtech.fsec.or.kr/main/main")
        time.sleep(2)
        
        # 2. 로그인
        print("2. 로그인 수행...")
        driver.get("https://regtech.fsec.or.kr/login/loginForm")
        time.sleep(2)
        
        # 로그인 폼 입력
        username_input = driver.find_element(By.ID, "username")
        password_input = driver.find_element(By.ID, "password")
        
        username_input.send_keys("nextrade")
        password_input.send_keys("Sprtmxm1@3")
        
        # 로그인 버튼 클릭
        login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_button.click()
        time.sleep(3)
        
        # 3. Advisory 페이지로 이동
        print("3. Advisory 페이지 이동...")
        driver.get("https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList")
        time.sleep(3)
        
        # 4. 날짜 설정 및 검색
        print("4. 날짜 설정 및 검색...")
        
        # 날짜 입력 필드 찾기
        try:
            start_date_input = driver.find_element(By.NAME, "startDate")
            end_date_input = driver.find_element(By.NAME, "endDate")
            
            # 날짜 설정
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
            
            start_date_input.clear()
            start_date_input.send_keys(start_date.strftime('%Y%m%d'))
            
            end_date_input.clear()
            end_date_input.send_keys(end_date.strftime('%Y%m%d'))
            
            print(f"날짜 범위: {start_date.strftime('%Y%m%d')} ~ {end_date.strftime('%Y%m%d')}")
        except:
            print("날짜 입력 필드를 찾을 수 없음")
        
        # blacklist 탭 클릭 (있다면)
        try:
            blacklist_tab = driver.find_element(By.XPATH, "//a[contains(text(), 'blacklist') or contains(text(), '블랙리스트')]")
            blacklist_tab.click()
            time.sleep(2)
            print("✅ Blacklist 탭 클릭")
        except:
            print("Blacklist 탭을 찾을 수 없음")
        
        # 검색 버튼 클릭
        try:
            search_button = driver.find_element(By.XPATH, "//button[contains(text(), '검색') or contains(text(), '조회')]")
            search_button.click()
            time.sleep(3)
            print("✅ 검색 버튼 클릭")
        except:
            print("검색 버튼을 찾을 수 없음")
        
        # 5. 데이터 수집
        print("\n5. 데이터 수집...")
        
        # 페이지가 완전히 로드될 때까지 대기
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # IP 패턴
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        
        # 테이블 찾기
        tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"발견된 테이블: {len(tables)}개")
        
        ip_list = []
        
        for i, table in enumerate(tables):
            rows = table.find_elements(By.TAG_NAME, "tr")
            print(f"테이블 {i+1}: {len(rows)}개 행")
            
            for row in rows[1:]:  # 헤더 제외
                cells = row.find_elements(By.TAG_NAME, "td")
                row_text = ' '.join([cell.text for cell in cells])
                
                # IP 찾기
                ips = re.findall(ip_pattern, row_text)
                for ip in ips:
                    if ip not in ip_list and not ip.startswith(('192.168.', '10.', '172.', '127.', '0.')):
                        ip_list.append(ip)
                        print(f"  IP 발견: {ip}")
        
        # 전체 페이지에서 IP 검색
        page_source = driver.page_source
        all_ips = re.findall(ip_pattern, page_source)
        
        for ip in all_ips:
            if ip not in ip_list and not ip.startswith(('192.168.', '10.', '172.', '127.', '0.')):
                ip_list.append(ip)
        
        print(f"\n🎯 총 수집된 IP: {len(ip_list)}개")
        
        if ip_list:
            print("샘플 IP:")
            for ip in ip_list[:10]:
                print(f"  - {ip}")
            return True
        else:
            # 페이지 소스 저장
            with open('regtech_selenium_page.html', 'w', encoding='utf-8') as f:
                f.write(page_source)
            print("💾 페이지 소스가 regtech_selenium_page.html로 저장됨")
            return False
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'driver' in locals():
            driver.quit()
            print("\n✅ WebDriver 종료")

if __name__ == "__main__":
    if SELENIUM_AVAILABLE:
        success = test_regtech_with_selenium()
        if success:
            print("\n🎉 Selenium으로 데이터 수집 성공!")
        else:
            print("\n💥 Selenium에서도 데이터를 찾을 수 없음")
    else:
        print("\n💡 대안: Playwright 사용을 고려하거나 실제 API 엔드포인트를 찾아야 합니다.")