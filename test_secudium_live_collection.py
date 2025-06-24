#!/usr/bin/env python3
"""
SECUDIUM 라이브 데이터 수집 테스트
실제 웹사이트에서 Black IP 데이터를 수집하는 테스트
"""

import sys
import os
import logging
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.secudium_har_collector import SecudiumHarCollector

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('secudium_live_test.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """메인 테스트 함수"""
    print("=== SECUDIUM 라이브 데이터 수집 테스트 시작 ===")
    
    try:
        # SECUDIUM HAR 수집기 초기화
        collector = SecudiumHarCollector()
        
        print(f"1. 수집기 초기화 완료")
        print(f"   - 기본 URL: {collector.base_url}")
        print(f"   - 로그인 URL: {collector.login_url}")
        print(f"   - Black IP URL: {collector.blackip_url}")
        
        # 인증 테스트
        print("\n2. SECUDIUM 인증 시작...")
        auth_success = collector.authenticate()
        
        if auth_success:
            print("   ✅ 인증 성공!")
        else:
            print("   ❌ 인증 실패")
            return False
        
        # 실시간 데이터 수집
        print("\n3. 실시간 Black IP 데이터 수집 시작...")
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
                blacklist_manager = UnifiedBlacklistManager()
                
                # IP 데이터 형식 변환 및 저장
                for ip_entry in ip_data[:5]:  # 테스트용으로 5개만 저장
                    blacklist_entry = {
                        'ip': ip_entry['ip'],
                        'source': ip_entry.get('source', 'SECUDIUM'),
                        'detection_date': ip_entry.get('detection_date'),
                        'description': ip_entry.get('description', ''),
                        'threat_type': ip_entry.get('threat_type', 'blacklist'),
                        'confidence': ip_entry.get('confidence', 'medium')
                    }
                    
                    # 데이터베이스에 추가
                    success = blacklist_manager.add_ip(**blacklist_entry)
                    if success:
                        print(f"     ✅ {ip_entry['ip']} 저장 성공")
                    else:
                        print(f"     ❌ {ip_entry['ip']} 저장 실패")
                        
                print(f"   데이터베이스 저장 테스트 완료")
                
            except Exception as e:
                print(f"   ❌ 데이터베이스 저장 중 오류: {e}")
        else:
            print("   ❌ 수집된 IP가 없습니다")
            
        print(f"\n=== 테스트 완료 ===")
        return len(ip_data) > 0
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        logger.error(f"테스트 오류: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)