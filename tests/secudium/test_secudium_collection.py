#!/usr/bin/env python3
"""
SECUDIUM 수집 및 저장 테스트
"""
import sys
sys.path.append('.')

from src.core.secudium_collector_fixed import SecudiumCollector
from src.core.unified_service import UnifiedBlacklistService
from src.core.container import get_container

def test_secudium_collection():
    """SECUDIUM 수집 테스트"""
    
    print("1. SECUDIUM 수집기 초기화...")
    collector = SecudiumCollector('data')
    
    print("\n2. 테스트 데이터 수집...")
    result = collector.auto_collect()
    
    if result['success']:
        print(f"✅ 수집 성공: {result['total_collected']}개 IP")
        
        if 'ips' in result and result['ips']:
            print("\n3. 데이터베이스에 저장...")
            try:
                # 컨테이너에서 서비스 가져오기
                container = get_container()
                blacklist_manager = container.get('blacklist_manager')
                
                # BlacklistEntry를 딕셔너리로 변환
                ips_data = []
                for ip_entry in result['ips']:
                    ips_data.append({
                        'ip': ip_entry.ip_address,
                        'source': 'SECUDIUM',
                        'threat_type': ip_entry.reason,
                        'country': ip_entry.country,
                        'confidence': 1.0
                    })
                
                # bulk_import_ips 호출
                import_result = blacklist_manager.bulk_import_ips(ips_data, source='SECUDIUM')
                
                if import_result['success']:
                    print(f"✅ 저장 성공: {import_result['imported_count']}개 IP")
                else:
                    print(f"❌ 저장 실패: {import_result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"❌ 저장 중 오류: {e}")
                
            # 샘플 출력
            print("\n4. 수집된 IP 샘플 (첫 5개):")
            for ip in result['ips'][:5]:
                print(f"   {ip.ip_address} - {ip.reason} ({ip.country})")
    else:
        print(f"❌ 수집 실패: {result['message']}")
    
    # 데이터베이스 확인
    print("\n5. 데이터베이스 상태 확인...")
    import sqlite3
    try:
        conn = sqlite3.connect('instance/blacklist.db')
        cursor = conn.cursor()
        
        # 전체 IP 수
        cursor.execute("SELECT COUNT(*) FROM blacklist_ip")
        total = cursor.fetchone()[0]
        print(f"   전체 IP: {total}개")
        
        # SECUDIUM IP 수
        cursor.execute("SELECT COUNT(*) FROM blacklist_ip WHERE source = 'SECUDIUM'")
        secudium = cursor.fetchone()[0]
        print(f"   SECUDIUM IP: {secudium}개")
        
        # REGTECH IP 수
        cursor.execute("SELECT COUNT(*) FROM blacklist_ip WHERE source = 'REGTECH'")
        regtech = cursor.fetchone()[0]
        print(f"   REGTECH IP: {regtech}개")
        
        conn.close()
    except Exception as e:
        print(f"   데이터베이스 확인 오류: {e}")

if __name__ == "__main__":
    test_secudium_collection()