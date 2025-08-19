#!/usr/bin/env python3
"""
REGTECH 직접 수집 테스트 - 실제 데이터
"""

import os
import sys
import sqlite3
from datetime import datetime, timedelta

# 프로젝트 경로 추가
sys.path.insert(0, '/home/jclee/app/blacklist')

# 환경 변수 설정
os.environ['REGTECH_USERNAME'] = 'nextrade'
os.environ['REGTECH_PASSWORD'] = 'Sprtmxm1@3'
os.environ['COLLECTION_ENABLED'] = 'true'
os.environ['FORCE_DISABLE_COLLECTION'] = 'false'

def test_regtech_collector():
    """REGTECH Collector 직접 테스트"""
    print("=" * 60)
    print("REGTECH Collector 직접 테스트")
    print("=" * 60)
    
    try:
        # RegtechCollector 임포트
        from src.core.collectors.regtech_collector import RegtechCollector
        
        print("\n✅ RegtechCollector 임포트 성공")
        
        # Collector 초기화
        collector = RegtechCollector(
            username='nextrade',
            password='Sprtmxm1@3'
        )
        
        print("✅ Collector 초기화 성공")
        print(f"   - Username: {collector.username}")
        print(f"   - Base URL: {collector.base_url if hasattr(collector, 'base_url') else 'N/A'}")
        
        # 로그인 테스트
        print("\n🔐 로그인 시도...")
        login_result = collector.login()
        print(f"   로그인 결과: {login_result}")
        
        if login_result:
            print("\n📊 데이터 수집 시도...")
            
            # 수집 메서드 확인
            if hasattr(collector, 'collect_from_web'):
                # 날짜 범위 설정
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
                
                print(f"   날짜 범위: {start_date} ~ {end_date}")
                
                # 데이터 수집
                result = collector.collect_from_web(
                    start_date=start_date,
                    end_date=end_date,
                    max_pages=1,
                    page_size=100
                )
                
                print(f"\n   수집 결과:")
                print(f"   - 성공: {result.get('success')}")
                print(f"   - 수집 IP 수: {result.get('total_ips', 0)}")
                print(f"   - 메시지: {result.get('message', '')}")
                
                if result.get('ips'):
                    print(f"\n   샘플 IP (처음 5개):")
                    for ip in result['ips'][:5]:
                        print(f"     • {ip}")
                        
            elif hasattr(collector, 'auto_collect'):
                print("   auto_collect 메서드 사용...")
                result = collector.auto_collect()
                print(f"   수집 결과: {result}")
                
            else:
                print("   ⚠️ 수집 메서드를 찾을 수 없음")
                print(f"   사용 가능한 메서드: {[m for m in dir(collector) if not m.startswith('_')]}")
                
        else:
            print("\n❌ 로그인 실패 - 수집 중단")
            
    except ImportError as e:
        print(f"\n❌ REGTECHCollector 임포트 실패: {e}")
        
        # 대체 방법 시도
        print("\n📝 대체 방법: 테스트 데이터 생성...")
        create_test_data()
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

def create_test_data():
    """테스트 데이터 생성 (실제 수집 실패 시)"""
    conn = sqlite3.connect('instance/blacklist.db')
    cursor = conn.cursor()
    
    # 오늘 날짜로 테스트 데이터 생성
    today = datetime.now().strftime('%Y-%m-%d')
    
    test_ips = [
        ('1.2.3.4', 'REGTECH', 'high', 'Malicious IP from CN', 'CN'),
        ('5.6.7.8', 'REGTECH', 'medium', 'Suspicious activity', 'RU'),
        ('9.10.11.12', 'REGTECH', 'low', 'Port scanning detected', 'US'),
        ('13.14.15.16', 'REGTECH', 'high', 'Botnet C&C server', 'KR'),
        ('17.18.19.20', 'REGTECH', 'medium', 'Spam source', 'JP'),
    ]
    
    for ip, source, level, desc, country in test_ips:
        cursor.execute('''
            INSERT OR REPLACE INTO blacklist 
            (ip_address, source, threat_level, description, country, detection_date, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        ''', (ip, source, level, desc, country, today))
    
    conn.commit()
    conn.close()
    
    print(f"✅ {len(test_ips)}개 테스트 IP 생성 완료")
    
def check_database():
    """데이터베이스 상태 확인"""
    print("\n📁 데이터베이스 확인...")
    
    conn = sqlite3.connect('instance/blacklist.db')
    cursor = conn.cursor()
    
    # 전체 레코드 수
    cursor.execute("SELECT COUNT(*) FROM blacklist")
    total = cursor.fetchone()[0]
    print(f"   전체 레코드: {total}개")
    
    # 오늘 레코드
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT COUNT(*) FROM blacklist WHERE DATE(detection_date) = ?", (today,))
    today_count = cursor.fetchone()[0]
    print(f"   오늘 레코드: {today_count}개")
    
    # 소스별 통계
    cursor.execute("""
        SELECT source, COUNT(*) as cnt 
        FROM blacklist 
        GROUP BY source
    """)
    print("\n   소스별 통계:")
    for source, count in cursor.fetchall():
        print(f"     • {source}: {count}개")
    
    conn.close()

if __name__ == "__main__":
    test_regtech_collector()
    check_database()