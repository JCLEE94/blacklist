#!/usr/bin/env python3
"""
통합 데이터 파이프라인 테스트
SECUDIUM + REGTECH 수집 → 데이터 정제 → DB 저장 전체 플로우 테스트
"""

import sys
import os
import logging
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.secudium_har_collector import SecudiumHarCollector
from src.core.regtech_har_collector import RegtechHarCollector
from src.core.data_pipeline import DataCleaningPipeline
from src.core.blacklist_unified import UnifiedBlacklistManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('integrated_pipeline_test.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """통합 파이프라인 테스트 메인 함수"""
    print("=== 통합 데이터 파이프라인 테스트 시작 ===\n")
    
    try:
        # 1. 블랙리스트 매니저 초기화
        print("1. 블랙리스트 매니저 초기화...")
        blacklist_manager = UnifiedBlacklistManager('data')
        print("   ✅ 블랙리스트 매니저 초기화 완료\n")
        
        # 2. SECUDIUM 수집
        print("2. SECUDIUM 데이터 수집...")
        secudium_collector = SecudiumHarCollector()
        
        if secudium_collector.authenticate():
            print("   ✅ SECUDIUM 인증 성공")
            secudium_data = secudium_collector.collect_blackip_data()
            print(f"   ✅ SECUDIUM 수집 완료: {len(secudium_data)}개 IP")
        else:
            print("   ❌ SECUDIUM 인증 실패 - 백업 데이터 사용")
            secudium_data = []
        
        # 3. REGTECH 수집  
        print("\n3. REGTECH 데이터 수집...")
        regtech_collector = RegtechHarCollector()
        
        if regtech_collector.authenticate():
            print("   ✅ REGTECH 접근 권한 확인 성공")
            regtech_data = regtech_collector.collect_blackip_data()
            print(f"   ✅ REGTECH 수집 완료: {len(regtech_data)}개 IP")
        else:
            print("   ❌ REGTECH 접근 실패 - 백업 데이터 사용")
            regtech_data = []
        
        # 4. 데이터 정제 파이프라인 초기화
        print("\n4. 데이터 정제 파이프라인 초기화...")
        pipeline = DataCleaningPipeline(blacklist_manager)
        print("   ✅ 데이터 파이프라인 초기화 완료")
        
        total_saved = 0
        
        # 5. SECUDIUM 데이터 정제 및 저장
        if secudium_data:
            print(f"\n5. SECUDIUM 데이터 정제 및 저장 ({len(secudium_data)}개)...")
            secudium_result = pipeline.process_collector_data(secudium_data, 'SECUDIUM')
            
            if secudium_result['success']:
                stats = secudium_result['stats']
                print(f"   ✅ SECUDIUM 정제 완료:")
                print(f"      - 총 처리: {stats['total_processed']}개")
                print(f"      - 유효 IP: {stats['valid_ips']}개")
                print(f"      - 중복 제거: {stats['duplicates']}개")
                print(f"      - DB 저장: {stats['saved']}개")
                print(f"      - 오류: {stats['errors']}개")
                total_saved += stats['saved']
            else:
                print(f"   ❌ SECUDIUM 정제 실패")
        else:
            print("\n5. SECUDIUM 데이터 없음 - 스킵")
        
        # 6. REGTECH 데이터 정제 및 저장
        if regtech_data:
            print(f"\n6. REGTECH 데이터 정제 및 저장 ({len(regtech_data)}개)...")
            regtech_result = pipeline.process_collector_data(regtech_data, 'REGTECH')
            
            if regtech_result['success']:
                stats = regtech_result['stats']
                print(f"   ✅ REGTECH 정제 완료:")
                print(f"      - 총 처리: {stats['total_processed']}개")
                print(f"      - 유효 IP: {stats['valid_ips']}개")
                print(f"      - 중복 제거: {stats['duplicates']}개")
                print(f"      - DB 저장: {stats['saved']}개")
                print(f"      - 오류: {stats['errors']}개")
                total_saved += stats['saved']
            else:
                print(f"   ❌ REGTECH 정제 실패")
        else:
            print("\n6. REGTECH 데이터 없음 - 스킵")
        
        # 7. 전체 통계 및 검증
        print(f"\n7. 전체 파이프라인 결과:")
        print(f"   - 총 저장된 IP: {total_saved}개")
        
        # 데이터베이스 검증
        try:
            db_stats = blacklist_manager.get_stats()
            print(f"   - 데이터베이스 총 IP: {db_stats.get('total_ips', 0)}개")
            print(f"   - 최근 업데이트: {db_stats.get('last_updated', 'N/A')}")
        except Exception as e:
            print(f"   ❌ 데이터베이스 통계 조회 실패: {e}")
        
        # 파이프라인 통계
        pipeline_stats = pipeline.get_processing_stats()
        print(f"   - 파이프라인 처리된 고유 IP: {pipeline_stats['processed_ips_count']}개")
        
        # 8. 샘플 데이터 확인
        print(f"\n8. 저장된 데이터 샘플 확인...")
        try:
            # 최근 저장된 IP 몇 개 조회
            sample_ips = blacklist_manager.get_active_ips()[:10]
            print(f"   샘플 IP (최대 10개):")
            for i, ip in enumerate(sample_ips[:5], 1):
                print(f"      {i}. {ip}")
            
            if len(sample_ips) > 5:
                print(f"      ... 및 {len(sample_ips) - 5}개 더")
                
        except Exception as e:
            print(f"   ❌ 샘플 데이터 조회 실패: {e}")
        
        print(f"\n=== 통합 파이프라인 테스트 완료 ===")
        return total_saved > 0
        
    except Exception as e:
        print(f"❌ 통합 테스트 중 오류 발생: {e}")
        logger.error(f"통합 테스트 오류: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)