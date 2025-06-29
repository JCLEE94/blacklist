#!/usr/bin/env python3
"""
SECUDIUM HAR 기반 수집 테스트
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.core.har_based_secudium_collector import HarBasedSecudiumCollector

def test_secudium_har_collection():
    """SECUDIUM HAR 기반 수집 테스트"""
    print("\n" + "="*60)
    print("SECUDIUM HAR 기반 수집 테스트")
    print("="*60)
    
    collector = HarBasedSecudiumCollector()
    
    # 1. 인증 테스트
    print("\n1. 인증 테스트...")
    auth_result = collector.authenticate()
    print(f"   인증 결과: {'✅ 성공' if auth_result else '❌ 실패'}")
    
    if not auth_result:
        print("   인증 실패로 테스트 중단")
        return
    
    print(f"   토큰: {collector.token[:50]}..." if collector.token else "   토큰 없음")
    
    # 2. 블랙리스트 수집 테스트
    print("\n2. 블랙리스트 수집 테스트...")
    try:
        ip_data = collector.collect_blackip_data(months_back=1)  # 1개월 데이터만 테스트
        print(f"   수집된 IP 수: {len(ip_data)}")
        
        # 처음 5개 IP 출력
        if ip_data:
            print("\n   수집된 IP 샘플:")
            for i, item in enumerate(ip_data[:5]):
                print(f"   [{i+1}] {item['ip']} (소스: {item['source']})")
    except Exception as e:
        print(f"   수집 실패: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. Excel 다운로드 테스트 (옵션)
    print("\n3. Excel 다운로드 테스트...")
    try:
        excel_file = collector.download_excel()
        if excel_file:
            print(f"   ✅ Excel 다운로드 성공: {excel_file}")
            
            # Excel에서 IP 추출
            excel_ips = collector.parse_excel_for_ips(excel_file)
            print(f"   Excel에서 추출된 IP 수: {len(excel_ips)}")
        else:
            print("   ❌ Excel 다운로드 실패")
    except Exception as e:
        print(f"   Excel 처리 실패: {e}")
    
    print("\n" + "="*60)
    print("테스트 완료")
    print("="*60)

if __name__ == "__main__":
    test_secudium_har_collection()