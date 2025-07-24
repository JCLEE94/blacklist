#!/usr/bin/env python3
"""
수집 디버깅 스크립트
REGTECH 수집 상태 및 문제 진단
"""

import os
import sys
import json
import requests
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_collection_status():
    """수집 상태 확인"""
    try:
        # 외부 URL 사용
        response = requests.get('https://blacklist.jclee.me/api/collection/status', 
                               verify=False, timeout=30)
        data = response.json()
        
        print("=== 수집 상태 ===")
        print(f"수집 활성화: {data.get('enabled', 'N/A')}")
        print(f"상태: {data.get('status', 'N/A')}")
        print(f"메시지: {data.get('message', 'N/A')}")
        print(f"총 IP: {data.get('stats', {}).get('total_ips', 0)}")
        print(f"오늘 수집: {data.get('stats', {}).get('today_collected', 0)}")
        
        # 소스별 상태
        sources = data.get('sources', {})
        print("\n=== 소스별 상태 ===")
        for source, info in sources.items():
            print(f"{source.upper()}:")
            print(f"  - 활성화: {info.get('enabled', 'N/A')}")
            print(f"  - 상태: {info.get('status', 'N/A')}")
            print(f"  - 마지막 수집: {info.get('last_collection', 'N/A')}")
        
        # 로그 확인
        logs = data.get('logs', [])
        print(f"\n=== 최근 로그 ({len(logs)}개) ===")
        for log in logs[:10]:  # 최근 10개만
            print(f"[{log.get('timestamp', 'N/A')}] {log.get('source', 'N/A')}: {log.get('action', 'N/A')}")
            if log.get('details'):
                details = log.get('details', {})
                if 'ips_collected' in details:
                    print(f"  -> 수집된 IP: {details['ips_collected']}")
                if 'error' in details:
                    print(f"  -> 오류: {details['error']}")
        
        return True
        
    except Exception as e:
        print(f"수집 상태 확인 실패: {e}")
        return False

def test_regtech_collection():
    """REGTECH 수집 테스트"""
    print("\n=== REGTECH 수집 테스트 ===")
    
    try:
        # 수집 트리거
        response = requests.post('https://blacklist.jclee.me/api/collection/regtech/trigger',
                                headers={'Content-Type': 'application/json'},
                                json={},
                                verify=False,
                                timeout=300)  # 5분 타임아웃
        
        data = response.json()
        
        if data.get('success'):
            print("✅ REGTECH 수집 성공")
            print(f"수집된 IP: {data.get('details', {}).get('collected', 0)}")
            print(f"메시지: {data.get('message', 'N/A')}")
        else:
            print("❌ REGTECH 수집 실패")
            print(f"오류: {data.get('error', data.get('message', 'Unknown error'))}")
        
        return data.get('success', False)
        
    except Exception as e:
        print(f"REGTECH 수집 테스트 실패: {e}")
        return False

def check_environment():
    """환경 확인"""
    print("\n=== 환경 확인 ===")
    
    try:
        # 헬스 체크
        response = requests.get('https://blacklist.jclee.me/health', 
                               verify=False, timeout=30)
        data = response.json()
        
        print(f"서비스 상태: {data.get('status', 'N/A')}")
        print(f"버전: {data.get('version', 'N/A')}")
        print(f"업타임: {data.get('uptime', 'N/A')}")
        
        # 통계 확인
        stats_response = requests.get('https://blacklist.jclee.me/api/stats', 
                                     verify=False, timeout=30)
        stats_data = stats_response.json()
        
        print(f"\n통계:")
        print(f"  - 총 IP: {stats_data.get('details', {}).get('total_ips', 0)}")
        print(f"  - 활성 IP: {stats_data.get('details', {}).get('active_ips', 0)}")
        print(f"  - REGTECH IP: {stats_data.get('details', {}).get('regtech_count', 0)}")
        
        return True
        
    except Exception as e:
        print(f"환경 확인 실패: {e}")
        return False

def main():
    """메인 함수"""
    print("🔍 수집 디버깅 시작")
    print("=" * 50)
    
    # 1. 환경 확인
    env_ok = check_environment()
    
    # 2. 수집 상태 확인
    status_ok = check_collection_status()
    
    # 3. REGTECH 수집 테스트 (자동 실행)
    print("\n🚀 REGTECH 수집 테스트 실행 중...")
    collection_ok = test_regtech_collection()
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("🎯 디버깅 결과 요약")
    print(f"환경 상태: {'✅ OK' if env_ok else '❌ FAIL'}")
    print(f"수집 상태: {'✅ OK' if status_ok else '❌ FAIL'}")
    
    print(f"REGTECH 수집: {'✅ OK' if collection_ok else '❌ FAIL'}")
    
    print("\n💡 문제 발생 시 확인사항:")
    print("1. 네트워크 연결 확인")
    print("2. 서비스 상태 확인 (kubectl get pods -n blacklist)")
    print("3. 로그 확인 (kubectl logs -f deployment/blacklist -n blacklist)")
    print("4. 환경 변수 확인 (COLLECTION_ENABLED, REGTECH_* 등)")

if __name__ == "__main__":
    main()