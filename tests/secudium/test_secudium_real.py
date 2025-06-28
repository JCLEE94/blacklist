#!/usr/bin/env python3
"""
SECUDIUM 실제 데이터 수집 테스트
SK인포섹의 실제 사이트 확인
"""
import requests
import json
from datetime import datetime

def test_secudium_skinfosec():
    """SK인포섹 사이트 테스트"""
    
    # SK인포섹 관련 가능한 URL들
    urls = [
        "https://www.skinfosec.com",
        "https://www.skshieldus.com",
        "https://secudium.skinfosec.com",
        "https://api.secudium.com",
        "https://secudium.com"
    ]
    
    print("SK인포섹/SECUDIUM 사이트 확인...")
    for url in urls:
        print(f"\n시도: {url}")
        try:
            resp = requests.get(url, timeout=5, verify=False)
            print(f"   상태: {resp.status_code}")
            if resp.status_code == 200:
                print(f"   타이틀: {resp.text[:100]}")
        except Exception as e:
            print(f"   실패: {e}")
    
    # SECUDIUM이 실제로는 파일 기반으로 제공될 수 있음
    print("\n\nSECUDIUM 데이터 형식 테스트...")
    
    # 테스트용 SECUDIUM 형식 데이터 생성
    test_data = {
        "source": "SECUDIUM",
        "collected_at": datetime.now().isoformat(),
        "total_ips": 0,
        "ips": [],
        "details": []
    }
    
    # 샘플 IP 데이터 추가
    sample_ips = [
        {"ip": "192.0.2.1", "attack_type": "Port Scan", "country": "CN", "detection_date": "2025-06-27"},
        {"ip": "198.51.100.1", "attack_type": "DDoS", "country": "RU", "detection_date": "2025-06-27"},
        {"ip": "203.0.113.1", "attack_type": "Brute Force", "country": "KP", "detection_date": "2025-06-27"}
    ]
    
    for item in sample_ips:
        test_data["ips"].append(item["ip"])
        test_data["details"].append(item)
    
    test_data["total_ips"] = len(test_data["ips"])
    
    print(json.dumps(test_data, indent=2, ensure_ascii=False))
    
    # 실제 SECUDIUM 수집기가 파일에서 데이터를 읽는 방식일 수 있음
    print("\n\nSECUDIUM은 실제로 다음 방식으로 작동할 수 있습니다:")
    print("1. 정기적으로 업데이트되는 파일 다운로드")
    print("2. 이메일로 전송되는 데이터")
    print("3. FTP/SFTP 서버에서 파일 수집")
    print("4. 별도의 전용 클라이언트 프로그램")

if __name__ == "__main__":
    test_secudium_skinfosec()