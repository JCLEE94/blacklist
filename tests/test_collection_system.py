#!/usr/bin/env python3
"""
통합 수집 시스템 테스트 및 실행
"""

import json
import os
import sys
from datetime import datetime

# Add path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.collection_unified import UnifiedCollectionSystem

def test_collection_system():
    """통합 수집 시스템 테스트"""
    
    print("=" * 60)
    print("통합 수집 시스템 테스트")
    print("=" * 60)
    
    # Initialize system
    system = UnifiedCollectionSystem()
    
    # 1. Save real credentials
    print("\n1. 자격증명 저장")
    print("-" * 40)
    
    # Save regtech credentials
    saved = system.save_credentials("regtech", "Sprtmxm1@3", "regtech")
    print(f"regtech 자격증명 저장: {'✅ 성공' if saved else '❌ 실패'}")
    
    # Save nextrade credentials
    saved2 = system.save_credentials("nextrade", "Sprtmxm1@3", "regtech")
    print(f"nextrade 자격증명 저장: {'✅ 성공' if saved2 else '❌ 실패'}")
    
    # 2. Verify credentials
    print("\n2. 자격증명 확인")
    print("-" * 40)
    
    creds = system.get_credentials("regtech")
    if creds:
        print(f"저장된 사용자: {creds['username']}")
        print(f"비밀번호: {'*' * len(creds['password'])}")
    else:
        print("❌ 자격증명을 찾을 수 없음")
    
    # 3. Collection statistics
    print("\n3. 수집 통계")
    print("-" * 40)
    
    stats = system.get_statistics()
    print(f"전체 수집 시도: {stats['total_collections']}회")
    print(f"성공한 수집: {stats['successful_collections']}회")
    print(f"실패한 수집: {stats['failed_collections']}회")
    print(f"총 수집 IP: {stats['total_ips_collected']}개")
    
    # Print by source
    if stats['sources']:
        print("\n소스별 통계:")
        for source, source_stats in stats['sources'].items():
            print(f"  {source}:")
            print(f"    - 시도: {source_stats['total']}회")
            print(f"    - 성공: {source_stats['success']}회")
            print(f"    - IP: {source_stats['total_ips']}개")
    
    # 4. Calendar visualization
    print("\n4. 캘린더 시각화")
    print("-" * 40)
    
    now = datetime.now()
    calendar = system.get_collection_calendar(now.year, now.month)
    
    print(f"{now.year}년 {now.month}월 수집 현황:")
    print(f"  총 일수: {calendar['summary']['total_days']}일")
    print(f"  수집일: {calendar['summary']['collected_days']}일")
    print(f"  수집률: {calendar['summary']['collected_days'] / calendar['summary']['total_days'] * 100:.1f}%")
    print(f"  총 IP: {calendar['summary']['total_ips']}개")
    
    # Show sample calendar days
    print("\n  일별 현황 (샘플):")
    for i, (date, info) in enumerate(calendar['calendar'].items()):
        if i < 5:  # Show first 5 days
            status = "✅" if info['collected'] else "⭕"
            print(f"    {date}: {status} {info['count']} IPs")
    
    # 5. Recent collections
    print("\n5. 최근 수집 이력")
    print("-" * 40)
    
    if system.collection_history:
        recent = system.collection_history[-5:]  # Last 5
        for record in recent:
            date = record.get('collected_at', 'Unknown')[:19]
            source = record.get('source', 'unknown')
            success = "✅" if record.get('success') else "❌"
            count = record.get('count', 0)
            error = record.get('error', '')
            
            print(f"  {date} | {source} | {success} | {count} IPs")
            if error and not record.get('success'):
                print(f"    에러: {error[:50]}")
    else:
        print("  수집 이력 없음")
    
    # 6. Test collection (optional)
    print("\n6. 수집 테스트")
    print("-" * 40)
    
    response = input("실제 수집을 테스트하시겠습니까? (y/N): ")
    if response.lower() == 'y':
        print("REGTECH 수집 시작...")
        result = system.collect_regtech()
        
        if result['success']:
            print(f"✅ 수집 성공: {result['count']}개 IP")
        else:
            print(f"❌ 수집 실패: {result.get('error', 'Unknown error')}")
    else:
        print("수집 테스트 건너뜀")
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)
    
    return system


def generate_report(system: UnifiedCollectionSystem):
    """수집 시스템 리포트 생성"""
    
    report = {
        "generated_at": datetime.now().isoformat(),
        "statistics": system.get_statistics(),
        "current_month": system.get_collection_calendar(
            datetime.now().year, 
            datetime.now().month
        ),
        "recent_collections": system.collection_history[-10:] if system.collection_history else []
    }
    
    # Save report
    report_file = "instance/collection_report.json"
    os.makedirs("instance", exist_ok=True)
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n리포트 저장됨: {report_file}")
    
    return report


if __name__ == "__main__":
    # Run test
    system = test_collection_system()
    
    # Generate report
    print("\n리포트 생성 중...")
    report = generate_report(system)
    
    print("\n✅ 모든 테스트 완료!")