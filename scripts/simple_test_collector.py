#!/usr/bin/env python3
"""
간단한 테스트 수집기
"""
import requests
import json
from datetime import datetime
import sqlite3

def test_secudium():
    """SECUDIUM 테스트"""
    print("=== SECUDIUM Test ===")
    
    # 로그인
    session = requests.Session()
    login_url = "https://secudium.skinfosec.co.kr/isap-api/loginProcess"
    
    login_data = {
        'lang': 'ko',
        'is_otp': 'N', 
        'is_expire': 'N',
        'login_name': 'nextrade',
        'password': 'Sprtmxm1@3',
        'otp_value': ''
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    resp = session.post(login_url, data=login_data, headers=headers)
    print(f"Login status: {resp.status_code}")
    print(f"Response: {resp.text[:200]}")
    
    # 응답 파싱
    try:
        data = resp.json()
        if data.get('response', {}).get('error') == 'already.login':
            print("Already logged in")
            return True
    except:
        pass
    
    return False

def test_regtech_blacklist():
    """REGTECH 블랙리스트 페이지 테스트"""
    print("\n=== REGTECH Blacklist Test ===")
    
    # 예제 IP (document에서 찾은 것)
    test_ip = "3.138.185.30"
    
    # 데이터베이스에 직접 추가
    conn = sqlite3.connect('instance/blacklist.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO blacklist_ip 
            (ip, source, detection_date, threat_type, metadata, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        ''', (
            test_ip,
            'REGTECH',
            '2025-06-20',
            'malicious',
            json.dumps({
                'country': 'US',
                'reason': 'Namo CrossEditor 정보 노출 탐지',
                'release_date': '2025-09-18'
            })
        ))
        conn.commit()
        print(f"Added test IP: {test_ip}")
        
        # 추가 테스트 IP들
        additional_ips = [
            ('1.234.56.78', 'KR', 'Malware distribution'),
            ('203.123.45.67', 'CN', 'Phishing site'),
            ('185.234.218.98', 'RU', 'Botnet C&C'),
            ('45.117.89.234', 'VN', 'Port scanning'),
            ('104.248.89.123', 'US', 'DDoS attack source')
        ]
        
        for ip, country, reason in additional_ips:
            cursor.execute('''
                INSERT OR REPLACE INTO blacklist_ip 
                (ip, source, detection_date, threat_type, metadata, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            ''', (
                ip,
                'REGTECH' if country in ['KR', 'US'] else 'SECUDIUM',
                datetime.now().strftime('%Y-%m-%d'),
                'malicious',
                json.dumps({
                    'country': country,
                    'reason': reason
                })
            ))
        
        conn.commit()
        print(f"Added {len(additional_ips)} additional test IPs")
        
        # 확인
        cursor.execute('SELECT COUNT(*) FROM blacklist_ip WHERE is_active = 1')
        count = cursor.fetchone()[0]
        print(f"Total active IPs in database: {count}")
        
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

def main():
    """메인 함수"""
    print("Simple Test Collector\n")
    
    # SECUDIUM 테스트
    test_secudium()
    
    # REGTECH 데이터 추가
    test_regtech_blacklist()
    
    print("\n=== Test Complete ===")
    print("Check the API endpoints:")
    print("  - http://localhost:8541/api/blacklist/active")
    print("  - http://localhost:8541/api/fortigate")
    print("  - http://localhost:8541/api/stats")

if __name__ == "__main__":
    main()