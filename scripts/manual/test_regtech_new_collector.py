#!/usr/bin/env python3
"""
업데이트된 REGTECH 수집기 테스트
"""
import os
os.environ['REGTECH_BEARER_TOKEN'] = "BearereyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJuZXh0cmFkZSIsIm9yZ2FubmFtZSI6IuuEpeyKpO2KuOugiIzdtOuTnCIsImlkIjoibmV4dHJhZGUiLCJleHAiOjE3NTExMTkyNzYsInVzZXJuYW1lIjoi7J6l7ZmN7KSAIn0.YwZHoHZCVqDnaryluB0h5_ituxYcaRz4voT7GRfgrNrP86W8TfvBuJbHMON4tJa4AQmNP-XhC_PuAVPQTjJADA"

from src.core.regtech_collector import RegtechCollector
from datetime import datetime, timedelta

def test_new_collector():
    """새로운 Excel 다운로드 방식 테스트"""
    print("🧪 업데이트된 REGTECH 수집기 테스트\n")
    
    # 수집기 생성
    collector = RegtechCollector(data_dir='./data')
    
    # 날짜 범위 설정
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    print(f"날짜 범위: {start_date.strftime('%Y%m%d')} ~ {end_date.strftime('%Y%m%d')}")
    
    # 수집 실행
    ips = collector.collect_from_web(
        start_date=start_date.strftime('%Y%m%d'),
        end_date=end_date.strftime('%Y%m%d')
    )
    
    if ips:
        print(f"\n✅ 수집 성공!")
        print(f"총 IP 수: {len(ips)}")
        
        # 샘플 출력
        print("\n샘플 데이터 (처음 10개):")
        for i, entry in enumerate(ips[:10]):
            print(f"{i+1}. {entry.ip} ({entry.country}) - {entry.attack_type}")
        
        # 통계
        print(f"\n수집 통계:")
        print(f"- 수집 방법: {collector.stats.source_method}")
        print(f"- 소요 시간: {(collector.stats.end_time - collector.stats.start_time).total_seconds():.2f}초")
        print(f"- 중복 제거: {collector.stats.duplicate_count}개")
        
        return True
    else:
        print("\n❌ 수집 실패")
        print(f"- 에러 수: {collector.stats.error_count}")
        return False

if __name__ == "__main__":
    success = test_new_collector()
    if success:
        print("\n🎉 REGTECH Excel 다운로드 수집기가 정상 작동합니다!")
    else:
        print("\n💥 수집기 테스트 실패")