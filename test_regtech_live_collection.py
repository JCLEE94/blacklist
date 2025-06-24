#!/usr/bin/env python3
"""
REGTECH 라이브 데이터 수집 테스트
실제 웹사이트에서 Black IP 데이터를 수집하는 테스트
"""

import sys
import os
import logging
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.regtech_har_collector import RegtechHarCollector

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('regtech_live_test.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """메인 테스트 함수"""
    print("=== REGTECH 라이브 데이터 수집 테스트 시작 ===")
    
    try:
        # REGTECH HAR 수집기 초기화
        collector = RegtechHarCollector()
        
        print(f"1. 수집기 초기화 완료")
        print(f"   - 기본 URL: {collector.base_url}")
        print(f"   - 리스트 URL: {collector.advisory_list_url}")
        print(f"   - 다운로드 URL: {collector.download_excel_url}")
        
        # 인증 테스트
        print("\n2. REGTECH 접근 권한 확인...")
        auth_success = collector.authenticate()
        
        if auth_success:
            print("   ✅ 접근 권한 확인 성공!")
        else:
            print("   ❌ 접근 권한 확인 실패")
            return False
        
        # 실시간 데이터 수집 (최근 3개월)
        print("\n3. 실시간 Black IP 데이터 수집 시작...")
        print("   - 날짜 범위: 최근 3개월")
        print("   - 데이터 소스: REGTECH Excel 다운로드")
        
        ip_data = collector.collect_blackip_data()
        
        print(f"\n4. 수집 결과:")
        print(f"   - 총 수집된 IP: {len(ip_data)}개")
        
        if ip_data:
            print(f"\n5. 수집된 IP 샘플 (최대 10개):")
            for i, ip_entry in enumerate(ip_data[:10]):
                print(f"   {i+1}. {ip_entry.get('ip', 'N/A')} - {ip_entry.get('description', 'N/A')}")
                
            # 데이터 저장 테스트
            print(f"\n6. 데이터 저장 테스트...")
            from src.core.blacklist_unified import UnifiedBlacklistManager
            
            try:
                blacklist_manager = UnifiedBlacklistManager('data')
                
                # IP 데이터 형식 변환 및 저장 (bulk_import_ips 사용)
                test_data = ip_data[:5]  # 테스트용으로 5개만 저장
                
                try:
                    # UnifiedBlacklistManager의 bulk_import_ips 메서드 호출
                    result = blacklist_manager.bulk_import_ips(
                        ips_data=test_data,
                        source='REGTECH_TEST'
                    )
                    
                    if result.get('success', False):
                        imported = result.get('imported_count', 0)
                        skipped = result.get('skipped_count', 0)
                        errors = result.get('error_count', 0)
                        
                        print(f"     ✅ 벌크 저장 성공: {imported}개 추가, {skipped}개 스킵, {errors}개 오류")
                        print(f"   데이터베이스 저장 완료: {imported}/{len(test_data)}개 성공")
                    else:
                        print(f"     ❌ 벌크 저장 실패: {result.get('error', 'Unknown error')}")
                        
                except Exception as save_error:
                    print(f"     ❌ 데이터베이스 저장 오류: {save_error}")
                
            except Exception as e:
                print(f"   ❌ 데이터베이스 저장 중 오류: {e}")
        else:
            print("   ❌ 수집된 IP가 없습니다")
            
        # 수집기 통계
        print(f"\n7. 수집기 통계:")
        stats = collector.get_stats()
        for key, value in stats.items():
            print(f"   - {key}: {value}")
            
        print(f"\n=== 테스트 완료 ===")
        return len(ip_data) > 0
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        logger.error(f"테스트 오류: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)