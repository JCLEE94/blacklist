#!/usr/bin/env python3
"""
모든 API 엔드포인트 통합 테스트
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://192.168.50.215:2541"

def test_endpoint(method, path, data=None, expected_status=200):
    """개별 엔드포인트 테스트"""
    url = f"{BASE_URL}{path}"
    print(f"\n🔍 테스트: {method} {path}")
    print("-" * 50)
    
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        else:
            print(f"❌ 지원하지 않는 메서드: {method}")
            return False
        
        print(f"📊 상태 코드: {response.status_code}")
        
        if response.status_code == expected_status:
            print("✅ 성공")
            
            # 응답 내용 출력
            if response.headers.get('content-type', '').startswith('application/json'):
                try:
                    json_data = response.json()
                    print(f"📝 응답: {json.dumps(json_data, indent=2, ensure_ascii=False)[:500]}...")
                except:
                    print(f"📝 응답 (텍스트): {response.text[:200]}...")
            else:
                print(f"📝 응답 (텍스트): {response.text[:200]}...")
            
            return True
        else:
            print(f"❌ 실패 - 예상: {expected_status}, 실제: {response.status_code}")
            print(f"📝 오류: {response.text[:500]}...")
            return False
            
    except Exception as e:
        print(f"❌ 요청 실패: {e}")
        return False

def main():
    """모든 API 테스트 실행"""
    print("🚀 블랙리스트 API 통합 테스트")
    print("=" * 60)
    print(f"📍 대상 서버: {BASE_URL}")
    print(f"🕐 시작 시간: {datetime.now()}")
    print("=" * 60)
    
    success_count = 0
    total_count = 0
    
    # 테스트할 엔드포인트 목록
    endpoints = [
        # 헬스 체크
        ("GET", "/health", None, 200),
        ("GET", "/api/status", None, 200),
        
        # 블랙리스트 조회
        ("GET", "/api/blacklist/active", None, 200),
        ("GET", "/api/fortigate", None, 200),
        ("GET", "/api/blacklist/json", None, 200),
        
        # IP 검색
        ("GET", "/api/search/192.168.1.1", None, 200),
        ("POST", "/api/search", {"ips": ["192.168.1.1", "10.0.0.1"]}, 200),
        
        # 통계
        ("GET", "/api/stats", None, 200),
        ("GET", "/api/v2/analytics/summary", None, 200),
        
        # 수집 관리
        ("GET", "/api/collection/status", None, 200),
        ("POST", "/api/collection/enable", None, 200),
        ("POST", "/api/collection/disable", None, 200),
        ("POST", "/api/collection/trigger", {"sources": ["regtech", "secudium"]}, 200),
        ("POST", "/api/collection/regtech/trigger", None, 200),
        ("POST", "/api/collection/secudium/trigger", None, 200),
        
        # 고급 기능
        ("GET", "/api/v2/blacklist/enhanced", None, 200),
    ]
    
    # 각 엔드포인트 테스트
    for method, path, data, expected_status in endpoints:
        total_count += 1
        if test_endpoint(method, path, data, expected_status):
            success_count += 1
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)
    print(f"✅ 성공: {success_count}/{total_count}")
    print(f"❌ 실패: {total_count - success_count}/{total_count}")
    print(f"📈 성공률: {(success_count/total_count*100):.1f}%")
    print(f"🕐 종료 시간: {datetime.now()}")
    
    # 추가 정보
    if success_count < total_count:
        print("\n⚠️  일부 API가 정상 작동하지 않습니다.")
        print("🔧 다음 사항을 확인하세요:")
        print("   - Docker 컨테이너가 정상 실행 중인지")
        print("   - 라우트가 올바르게 등록되었는지")
        print("   - 수집 서비스가 초기화되었는지")

if __name__ == '__main__':
    main()