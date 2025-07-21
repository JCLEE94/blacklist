#!/usr/bin/env python3
"""
최종 시스템 검증 스크립트
"""
import requests
import time
import subprocess
import sys

def verify_system():
    print("🧪 API 엔드포인트 최종 검증...")

    # kubectl port-forward 시작
    port_forward = subprocess.Popen([
        'kubectl', 'port-forward', '-n', 'blacklist', 
        'deployment/blacklist', '8544:8541'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    time.sleep(2)

    try:
        base_url = 'http://localhost:8544'
        
        # 핵심 엔드포인트 테스트
        endpoints = {
            '/health': '시스템 상태',
            '/api/stats': '통계 정보',
            '/api/collection/status': '수집 상태',
            '/api/blacklist/active': '활성 IP 목록',
            '/api/fortigate': 'FortiGate 연동'
        }
        
        all_passed = True
        results = {}
        
        for endpoint, description in endpoints.items():
            try:
                response = requests.get(f'{base_url}{endpoint}', timeout=5)
                if response.status_code == 200:
                    print(f"✅ {endpoint}: {description} - OK")
                    results[endpoint] = True
                else:
                    print(f"❌ {endpoint}: {description} - {response.status_code}")
                    results[endpoint] = False
                    all_passed = False
            except Exception as e:
                print(f"❌ {endpoint}: {description} - 오류: {str(e)}")
                results[endpoint] = False
                all_passed = False
        
        print(f"\n📊 검증 결과: {sum(results.values())}/{len(results)} 통과")
        
        if all_passed:
            print("🎉 모든 API 엔드포인트 정상!")
            return True
        else:
            print("⚠️ 일부 엔드포인트에 문제 있음")
            return False

    finally:
        port_forward.terminate()
        port_forward.wait()

if __name__ == "__main__":
    success = verify_system()
    sys.exit(0 if success else 1)