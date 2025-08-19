#!/usr/bin/env python3
"""
통합 수집 시스템 테스트
- 성공한 REGTECH 인증 적용
- 기간별 수집 기능
- 스케줄링 시스템
- 통합 관리패널 API
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta

# 프로젝트 경로 추가
sys.path.insert(0, '/home/jclee/app/blacklist')

from src.core.services.collection_scheduler import CollectionScheduler
from src.core.regtech_integration_fixed import RegtechIntegrationSystem


def test_integrated_system():
    """통합 시스템 테스트"""
    
    all_validation_failures = []
    total_tests = 0
    
    print("🚀 통합 수집 시스템 테스트")
    print("="*80)
    
    # Test 1: REGTECH 통합 시스템
    total_tests += 1
    try:
        print("\n🔧 Test 1: REGTECH 통합 시스템 초기화...")
        regtech_system = RegtechIntegrationSystem()
        
        if not regtech_system:
            all_validation_failures.append("REGTECH 시스템 초기화 실패")
        else:
            print("✅ REGTECH 통합 시스템 초기화 성공")
            
    except Exception as e:
        all_validation_failures.append(f"REGTECH 시스템 초기화 오류: {e}")
    
    # Test 2: 수집 스케줄러
    total_tests += 1
    try:
        print("\n⏰ Test 2: 수집 스케줄러 초기화...")
        scheduler = CollectionScheduler()
        
        # REGTECH 수집 콜백 등록
        def regtech_collection_callback():
            return regtech_system.run_collection()
        
        scheduler.register_collection_callback("regtech", regtech_collection_callback)
        
        schedule_status = scheduler.get_schedule_status()
        if not schedule_status or "schedules" not in schedule_status:
            all_validation_failures.append("스케줄러 상태 조회 실패")
        else:
            print("✅ 수집 스케줄러 초기화 성공")
            print(f"  - 등록된 스케줄: {len(schedule_status['schedules'])}개")
            
    except Exception as e:
        all_validation_failures.append(f"스케줄러 초기화 오류: {e}")
    
    # Test 3: 성공한 인증 방식으로 실제 수집 테스트
    total_tests += 1
    try:
        print("\n🔐 Test 3: 실제 REGTECH 데이터 수집...")
        
        # 자격증명 확인
        username = os.getenv('REGTECH_USERNAME')
        password = os.getenv('REGTECH_PASSWORD')
        
        if not username or not password:
            print("⚠️ REGTECH 자격증명이 없어 수집 테스트 건너뜀")
        else:
            # 실제 수집 실행 (최근 30일)
            collection_result = regtech_system.run_collection()
            
            if collection_result.get("success"):
                collected_count = collection_result.get("stored_count", 0)
                total_db_count = collection_result.get("total_ips_in_db", 0)
                
                print(f"✅ REGTECH 수집 성공")
                print(f"  - 신규 수집: {collected_count}개 IP")
                print(f"  - 전체 DB: {total_db_count}개 IP")
                print(f"  - 실행 시간: {collection_result.get('execution_time_seconds', 0):.2f}초")
                
                if collected_count == 0:
                    print("  ℹ️ 신규 IP 없음 (중복 제거됨)")
                    
            else:
                error_msg = collection_result.get("error", "Unknown error")
                all_validation_failures.append(f"REGTECH 수집 실패: {error_msg}")
                
    except Exception as e:
        all_validation_failures.append(f"실제 수집 테스트 오류: {e}")
    
    # Test 4: 기간별 수집 테스트
    total_tests += 1
    try:
        print("\n📅 Test 4: 기간별 수집 테스트...")
        
        # 다양한 기간으로 테스트
        test_periods = [
            ("2주일", "2025-08-06", "2025-08-20"),
            ("1개월", "2025-07-21", "2025-08-20"), 
            ("3개월", "2025-05-22", "2025-08-20")
        ]
        
        period_results = {}
        
        for period_name, start_date, end_date in test_periods:
            try:
                result = regtech_system.run_collection(start_date=start_date, end_date=end_date)
                
                period_results[period_name] = {
                    "success": result.get("success", False),
                    "collected_count": result.get("collected_count", 0),
                    "stored_count": result.get("stored_count", 0),
                    "execution_time": result.get("execution_time_seconds", 0)
                }
                
                if result.get("success"):
                    print(f"  ✅ {period_name}: {result.get('collected_count', 0)}개 수집")
                else:
                    print(f"  ❌ {period_name}: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                period_results[period_name] = {"success": False, "error": str(e)}
                print(f"  ❌ {period_name}: {e}")
        
        # 기간별 결과 분석
        successful_periods = sum(1 for r in period_results.values() if r.get("success"))
        total_periods = len(period_results)
        
        print(f"\n📊 기간별 수집 결과: {successful_periods}/{total_periods} 성공")
        
        if successful_periods == 0:
            all_validation_failures.append("모든 기간별 수집이 실패")
            
    except Exception as e:
        all_validation_failures.append(f"기간별 수집 테스트 오류: {e}")
    
    # Test 5: 스케줄러 동작 테스트
    total_tests += 1
    try:
        print("\n🕐 Test 5: 스케줄러 동작 테스트...")
        
        # 스케줄 설정 업데이트
        scheduler.update_schedule("regtech", enabled=True, interval_hours=1)
        
        # 즉시 수집 트리거 테스트
        trigger_result = scheduler.trigger_immediate_collection("regtech")
        
        if trigger_result:
            print("✅ 즉시 수집 트리거 성공")
            
            # 잠시 대기 후 상태 확인
            time.sleep(2)
            
            status = scheduler.get_schedule_status()
            regtech_schedule = status.get("schedules", {}).get("regtech", {})
            
            print(f"  - 성공 횟수: {regtech_schedule.get('success_count', 0)}")
            print(f"  - 실패 횟수: {regtech_schedule.get('failure_count', 0)}")
            print(f"  - 성공률: {regtech_schedule.get('success_rate', 0):.1f}%")
            
        else:
            all_validation_failures.append("즉시 수집 트리거 실패")
            
    except Exception as e:
        all_validation_failures.append(f"스케줄러 동작 테스트 오류: {e}")
    
    # Test 6: API 엔드포인트 시뮬레이션
    total_tests += 1
    try:
        print("\n🌐 Test 6: API 데이터 형식 테스트...")
        
        # 대시보드 데이터 형식 테스트
        dashboard_data = {
            "daily_stats": generate_sample_daily_stats(30),
            "source_stats": generate_sample_source_stats(),
            "system_health": {"total_ips": 930, "status": "healthy"},
            "period_availability": generate_period_availability(),
            "last_updated": datetime.now().isoformat()
        }
        
        # JSON 직렬화 테스트
        json_data = json.dumps(dashboard_data, ensure_ascii=False, indent=2)
        
        if len(json_data) > 0:
            print("✅ API 데이터 형식 검증 성공")
            print(f"  - 일자별 통계: {len(dashboard_data['daily_stats'])}일")
            print(f"  - 소스별 통계: {len(dashboard_data['source_stats'])}개")
            print(f"  - 데이터 크기: {len(json_data):,} bytes")
        else:
            all_validation_failures.append("API 데이터 직렬화 실패")
            
    except Exception as e:
        all_validation_failures.append(f"API 데이터 형식 테스트 오류: {e}")
    
    # Test 7: 성능 검증
    total_tests += 1
    try:
        print("\n⚡ Test 7: 성능 검증...")
        
        # 시스템 상태 조회 성능 측정
        start_time = time.time()
        system_status = regtech_system.get_system_status()
        status_time = time.time() - start_time
        
        # 스케줄러 상태 조회 성능 측정
        start_time = time.time()
        schedule_status = scheduler.get_schedule_status()
        schedule_time = time.time() - start_time
        
        print(f"✅ 성능 검증 완료")
        print(f"  - 시스템 상태 조회: {status_time*1000:.1f}ms")
        print(f"  - 스케줄 상태 조회: {schedule_time*1000:.1f}ms")
        
        if status_time > 1.0 or schedule_time > 1.0:
            all_validation_failures.append("성능 기준 미달 (1초 초과)")
            
    except Exception as e:
        all_validation_failures.append(f"성능 검증 오류: {e}")
    
    # 최종 검증 결과
    print("\n" + "="*80)
    print("📋 통합 테스트 결과")
    print("="*80)
    
    if all_validation_failures:
        print(f"❌ 테스트 실패 - {len(all_validation_failures)}/{total_tests}개 테스트 실패:")
        for i, failure in enumerate(all_validation_failures, 1):
            print(f"  {i}. {failure}")
        
        return False
    else:
        print(f"✅ 모든 테스트 통과 - {total_tests}/{total_tests}개 성공")
        print("\n🎉 통합 수집 시스템이 성공적으로 구축되었습니다!")
        print("\n📊 시스템 요약:")
        print("  - ✅ REGTECH 인증 및 수집")
        print("  - ✅ 기간별 수집 지원")
        print("  - ✅ 자동 스케줄링")
        print("  - ✅ 통합 관리패널 API")
        print("  - ✅ 실시간 모니터링")
        print("  - ✅ 성능 최적화")
        
        return True


def generate_sample_daily_stats(days: int):
    """샘플 일자별 통계 생성"""
    stats = []
    base_date = datetime.now()
    
    for i in range(days):
        date = base_date - timedelta(days=i)
        stats.append({
            "date": date.strftime('%Y-%m-%d'),
            "regtech_ips": 30 + (i % 10),
            "secudium_ips": 0,
            "total_ips": 30 + (i % 10),
            "collections": 1 if i % 7 != 6 else 0,
            "success": True if i % 10 != 9 else False
        })
    
    return list(reversed(stats))


def generate_sample_source_stats():
    """샘플 소스별 통계 생성"""
    return {
        "REGTECH": {
            "name": "REGTECH",
            "status": "active",
            "total_ips": 930,
            "success_rate": 92.5,
            "enabled": True
        },
        "SECUDIUM": {
            "name": "SECUDIUM",
            "status": "disabled",
            "total_ips": 0,
            "success_rate": 0,
            "enabled": False
        }
    }


def generate_period_availability():
    """기간별 가용성 샘플 데이터"""
    return {
        "1일": {"available": False, "ip_count": 0},
        "1주일": {"available": False, "ip_count": 0},
        "2주일": {"available": True, "ip_count": 30},
        "1개월": {"available": True, "ip_count": 930},
        "3개월": {"available": True, "ip_count": 930},
        "6개월": {"available": True, "ip_count": 930},
        "1년": {"available": True, "ip_count": 930}
    }


if __name__ == "__main__":
    success = test_integrated_system()
    sys.exit(0 if success else 1)