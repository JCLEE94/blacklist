#!/usr/bin/env python3
"""
테스트용 SECUDIUM 데이터 생성
실제 SECUDIUM은 OTP 인증이 필요하므로 테스트 데이터로 대체
"""
import json
import pandas as pd
from datetime import datetime
import random

def create_test_secudium_data():
    """테스트용 SECUDIUM 데이터 생성"""
    
    # 테스트 IP 생성 (실제 악성 IP가 아닌 테스트용)
    test_ips = []
    attack_types = ["DDoS", "Port Scan", "Brute Force", "Malware", "Phishing", "SQL Injection"]
    countries = ["CN", "RU", "KP", "IR", "VN", "TH", "IN", "BR"]
    
    # 1000개의 테스트 IP 생성
    for i in range(1000):
        ip = f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
        
        # 사설 IP 제외
        if ip.startswith("10.") or ip.startswith("192.168.") or ip.startswith("172."):
            continue
            
        test_ips.append({
            "ip_address": ip,
            "attack_type": random.choice(attack_types),
            "country": random.choice(countries),
            "detection_date": datetime.now().strftime("%Y-%m-%d"),
            "threat_level": random.choice(["high", "medium", "low"]),
            "source": "SECUDIUM"
        })
    
    # JSON 파일로 저장
    json_file = "data/secudium_test_data.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            "source": "SECUDIUM",
            "collected_at": datetime.now().isoformat(),
            "total_ips": len(test_ips),
            "ips": [item["ip_address"] for item in test_ips],
            "details": test_ips
        }, f, indent=2, ensure_ascii=False)
    
    print(f"✅ JSON 파일 생성: {json_file}")
    print(f"   총 {len(test_ips)}개 IP")
    
    # Excel 파일로도 저장 (실제 SECUDIUM 형식 모방)
    df = pd.DataFrame(test_ips)
    excel_file = "data/secudium_test_data.xlsx"
    df.to_excel(excel_file, index=False)
    
    print(f"✅ Excel 파일 생성: {excel_file}")
    
    # 샘플 출력
    print("\n샘플 데이터 (첫 5개):")
    for item in test_ips[:5]:
        print(f"  {item['ip_address']} - {item['attack_type']} ({item['country']})")

if __name__ == "__main__":
    create_test_secudium_data()