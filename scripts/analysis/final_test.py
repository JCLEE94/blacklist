#!/usr/bin/env python3
"""최종 통합 테스트 스크립트"""

import requests
import time
import json

# 테스트 설정
BASE_URL = "http://localhost:8541"

def test_db_clear():
    """데이터베이스 클리어 테스트"""
    print("\n=== 1. DB 클리어 테스트 ===")
    try:
        response = requests.post(f"{BASE_URL}/api/db/clear")
        if response.status_code == 200:
            print("✓ DB 클리어 성공")
            print(f"  응답: {response.json()}")
        else:
            print(f"✗ DB 클리어 실패: {response.status_code}")
            print(f"  응답: {response.text}")
    except Exception as e:
        print(f"✗ DB 클리어 실패: {e}")

def test_stats_after_clear():
    """클리어 후 통계 확인"""
    print("\n=== 2. 클리어 후 통계 확인 ===")
    try:
        response = requests.get(f"{BASE_URL}/api/stats")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                stats = data.get('data', {})
                print(f"✓ 통계 조회 성공")
                print(f"  총 IP 수: {stats.get('total_ips', 0)}")
                print(f"  활성 IP 수: {stats.get('active_ips', 0)}")
                print(f"  REGTECH: {stats.get('regtech_count', 0)}")
                print(f"  SECUDIUM: {stats.get('secudium_count', 0)}")
                if stats.get('total_ips', 0) == 0:
                    print("✓ DB가 정상적으로 클리어됨")
                else:
                    print("✗ DB 클리어가 완전하지 않음")
            else:
                print(f"✗ 통계 조회 실패: {data.get('error')}")
        else:
            print(f"✗ 통계 조회 실패: {response.status_code}")
    except Exception as e:
        print(f"✗ 통계 조회 실패: {e}")

def test_regtech_collection():
    """REGTECH 수집 테스트"""
    print("\n=== 3. REGTECH 수집 테스트 ===")
    try:
        response = requests.post(f"{BASE_URL}/api/collection/regtech/trigger")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✓ REGTECH 수집 트리거 성공")
                print(f"  수집된 IP 수: {data.get('ip_count', 0)}")
                print(f"  저장된 IP 수: {data.get('imported_count', 0)}")
                print(f"  메시지: {data.get('message')}")
            else:
                print(f"✗ REGTECH 수집 실패: {data.get('error')}")
                print(f"  메시지: {data.get('message')}")
        else:
            print(f"✗ REGTECH 수집 실패: {response.status_code}")
            print(f"  응답: {response.text}")
    except Exception as e:
        print(f"✗ REGTECH 수집 실패: {e}")

def test_secudium_collection():
    """SECUDIUM 수집 테스트 - 비활성화됨"""
    print("\n=== 4. SECUDIUM 수집 테스트 ===")
    print("✓ SECUDIUM 수집이 비활성화되었습니다 (사용자 요청)")

def test_final_stats():
    """최종 통계 확인"""
    print("\n=== 5. 최종 통계 확인 ===")
    try:
        response = requests.get(f"{BASE_URL}/api/stats")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                stats = data.get('data', {})
                print(f"✓ 최종 통계 조회 성공")
                print(f"  총 IP 수: {stats.get('total_ips', 0)}")
                print(f"  활성 IP 수: {stats.get('active_ips', 0)}")
                print(f"  REGTECH: {stats.get('regtech_count', 0)}")
                print(f"  SECUDIUM: {stats.get('secudium_count', 0)}")
                print(f"  공용: {stats.get('public_count', 0)}")
            else:
                print(f"✗ 통계 조회 실패: {data.get('error')}")
        else:
            print(f"✗ 통계 조회 실패: {response.status_code}")
    except Exception as e:
        print(f"✗ 통계 조회 실패: {e}")

def test_check_id_sequence():
    """ID 시퀀스 확인"""
    print("\n=== 6. ID 시퀀스 확인 ===")
    try:
        response = requests.get(f"{BASE_URL}/api/v2/blacklist/enhanced?limit=5")
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('data', {}).get('entries'):
                entries = data['data']['entries']
                first_id = entries[0].get('id') if entries else None
                if first_id == 1:
                    print("✓ ID가 1번부터 시작합니다")
                else:
                    print(f"✗ ID가 {first_id}번부터 시작합니다 (1번이어야 함)")
                
                # ID 목록 출력
                ids = [entry.get('id') for entry in entries[:5]]
                print(f"  처음 5개 ID: {ids}")
            else:
                print("✗ 데이터가 없습니다")
        else:
            print(f"✗ API 호출 실패: {response.status_code}")
    except Exception as e:
        print(f"✗ ID 확인 실패: {e}")

def test_dashboard_charts():
    """대시보드 차트 데이터 확인"""
    print("\n=== 7. 대시보드 차트 데이터 확인 ===")
    try:
        # 월별 통계
        response = requests.get(f"{BASE_URL}/api/stats/monthly")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                monthly_data = data.get('data', [])
                print(f"✓ 월별 통계 조회 성공")
                for month in monthly_data[-3:]:  # 최근 3개월
                    print(f"  {month['month']}: REGTECH={month['regtech']}, SECUDIUM={month['secudium']}, 총={month['total']}")
            else:
                print(f"✗ 월별 통계 조회 실패: {data.get('error')}")
        else:
            print(f"✗ 월별 통계 조회 실패: {response.status_code}")
    except Exception as e:
        print(f"✗ 월별 통계 조회 실패: {e}")

if __name__ == "__main__":
    print("=== 블랙리스트 시스템 최종 테스트 시작 ===")
    print(f"테스트 서버: {BASE_URL}")
    
    # 서버 상태 확인
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✓ 서버가 정상 작동 중입니다")
        else:
            print(f"✗ 서버 상태 이상: {response.status_code}")
            exit(1)
    except Exception as e:
        print(f"✗ 서버 연결 실패: {e}")
        exit(1)
    
    # 테스트 실행
    test_db_clear()
    time.sleep(2)  # DB 클리어 완료 대기
    
    test_stats_after_clear()
    time.sleep(1)
    
    test_regtech_collection()
    time.sleep(5)  # REGTECH 수집 완료 대기
    
    test_secudium_collection()
    time.sleep(5)  # SECUDIUM 수집 완료 대기
    
    test_final_stats()
    test_check_id_sequence()
    test_dashboard_charts()
    
    print("\n=== 최종 테스트 완료 ===")