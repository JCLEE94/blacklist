#!/usr/bin/env python3
"""
API 직접 테스트
"""
import sys
sys.path.append('.')

from src.core.blacklist_unified import UnifiedBlacklistManager
from src.core.container import get_container

def test_api():
    """API 기능 직접 테스트"""
    try:
        # 컨테이너 초기화
        container = get_container()
        manager = container.resolve('blacklist_manager')
        
        print("=== Blacklist Manager Test ===\n")
        
        # 1. 활성 IP 목록
        active_ips = manager.get_active_ips()
        print(f"Active IPs: {len(active_ips)}")
        if active_ips:
            # set과 list 분리
            if isinstance(active_ips, tuple) and len(active_ips) == 2:
                ip_set, ip_list = active_ips
                print(f"IP Set: {len(ip_set)} items")
                print(f"IP List: {len(ip_list)} items")
                # 처음 5개 출력
                for ip in list(ip_set)[:5]:
                    print(f"  - {ip}")
            else:
                print("Unexpected format:", type(active_ips))
        
        # 2. FortiGate 형식
        print("\n=== FortiGate Format ===")
        fortigate = manager.get_fortigate_format()
        print(f"Entries: {len(fortigate.get('entries', []))}")
        print(f"Total count: {fortigate.get('total_count', 0)}")
        
        # 3. 통계
        print("\n=== Statistics ===")
        # get_stats() 메서드가 없으면 다른 방법 시도
        try:
            if hasattr(manager, 'get_stats'):
                stats = manager.get_stats()
                print(stats)
            else:
                print("get_stats() method not available")
                # 직접 DB 조회
                import sqlite3
                conn = sqlite3.connect('instance/blacklist.db')
                cursor = conn.cursor()
                cursor.execute('SELECT source, COUNT(*) FROM blacklist_ip GROUP BY source')
                for row in cursor.fetchall():
                    print(f"  {row[0]}: {row[1]} IPs")
                conn.close()
        except Exception as e:
            print(f"Stats error: {e}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api()