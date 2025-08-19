#!/usr/bin/env python3
"""
데이터베이스 저장 및 시각화 확인 테스트
"""

import sqlite3
import os
import sys
import json
from datetime import datetime

def check_database_status():
    """데이터베이스 상태 확인"""
    print("=" * 60)
    print("🗄️ 데이터베이스 상태 확인")
    print("=" * 60)
    
    db_path = 'instance/blacklist.db'
    
    if not os.path.exists(db_path):
        print("❌ 데이터베이스 파일이 존재하지 않습니다.")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 테이블 목록 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"📋 테이블 목록: {[table[0] for table in tables]}")
        
        # 블랙리스트 테이블 구조 확인
        cursor.execute("PRAGMA table_info(blacklist);")
        columns = cursor.fetchall()
        print(f"📊 blacklist 테이블 컬럼: {len(columns)}개")
        for col in columns:
            print(f"   - {col[1]} ({col[2]})")
        
        # 전체 데이터 개수
        cursor.execute("SELECT COUNT(*) FROM blacklist;")
        total_count = cursor.fetchone()[0]
        print(f"📈 전체 IP 개수: {total_count}")
        
        # 소스별 개수
        cursor.execute("SELECT source, COUNT(*) FROM blacklist GROUP BY source;")
        source_counts = cursor.fetchall()
        print("📊 소스별 분포:")
        for source, count in source_counts:
            print(f"   - {source}: {count}개")
        
        # REGTECH 최신 데이터 확인
        cursor.execute("""
            SELECT ip_address, detection_date, description, created_at 
            FROM blacklist 
            WHERE source = 'REGTECH' 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        regtech_data = cursor.fetchall()
        
        if regtech_data:
            print("\n🎯 REGTECH 최신 데이터 (5개):")
            for ip, date, desc, created in regtech_data:
                print(f"   - {ip} ({date}) - {desc[:30]}... [{created}]")
        else:
            print("\n⚠️ REGTECH 데이터가 없습니다.")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 데이터베이스 확인 중 오류: {e}")
        return False

def test_api_collection():
    """API를 통한 수집 테스트"""
    print("\n" + "=" * 60)
    print("🔌 API 수집 테스트")
    print("=" * 60)
    
    try:
        import requests
        
        # 1. 서버 상태 확인
        health_response = requests.get('http://localhost:32542/health', timeout=5)
        if health_response.status_code != 200:
            print("❌ 서버가 실행되지 않음")
            return False
            
        print("✅ 서버 실행 중")
        
        # 2. 수집 상태 확인
        status_response = requests.get('http://localhost:32542/api/collection/status')
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"📊 수집 상태: {status_data.get('collection_enabled', 'Unknown')}")
        
        # 3. 테스트 쿠키로 수집 시도
        test_data = {
            'cookies': 'JSESSIONID=TEST123; regtech-front=TEST456',
            'start_date': '2025-08-17',
            'end_date': '2025-08-19'
        }
        
        print("🔄 테스트 쿠키로 수집 시도...")
        collection_response = requests.post(
            'http://localhost:32542/api/collection/regtech/trigger',
            json=test_data,
            timeout=30
        )
        
        print(f"📡 API 응답: {collection_response.status_code}")
        if collection_response.status_code in [200, 500]:  # 500도 처리 응답으로 간주
            result = collection_response.json()
            print(f"💬 메시지: {result.get('message', 'No message')}")
            
            if result.get('success'):
                print("✅ 수집 성공")
                return True
            else:
                print(f"⚠️ 수집 실패: {result.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ API 호출 실패: {collection_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ API 테스트 실패: {e}")
        return False

def check_visualization():
    """웹 대시보드 시각화 확인"""
    print("\n" + "=" * 60)
    print("📊 웹 대시보드 시각화 확인")
    print("=" * 60)
    
    try:
        import requests
        
        # 메인 대시보드 접근
        dashboard_response = requests.get('http://localhost:32542/', timeout=5)
        if dashboard_response.status_code == 200:
            print("✅ 대시보드 접근 가능")
            
            # Chart.js 포함 여부 확인
            if 'chart.js' in dashboard_response.text.lower():
                print("✅ Chart.js 시각화 라이브러리 포함")
            else:
                print("⚠️ Chart.js 라이브러리 확인 필요")
            
            # 데이터 테이블 포함 여부 확인
            if 'table' in dashboard_response.text.lower():
                print("✅ 데이터 테이블 포함")
            else:
                print("⚠️ 데이터 테이블 확인 필요")
                
            print(f"📏 대시보드 크기: {len(dashboard_response.text)} bytes")
            return True
        else:
            print(f"❌ 대시보드 접근 실패: {dashboard_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 대시보드 확인 실패: {e}")
        return False

def check_cookie_system():
    """쿠키 시스템 파일 확인"""
    print("\n" + "=" * 60)
    print("🍪 쿠키 시스템 파일 확인")
    print("=" * 60)
    
    cookie_files = [
        'regtech_cookies.json',
        'regtech_cookies_selenium.json',
        'regtech_cookies_manual.json'
    ]
    
    found_files = []
    for cookie_file in cookie_files:
        if os.path.exists(cookie_file):
            found_files.append(cookie_file)
            try:
                with open(cookie_file, 'r') as f:
                    data = json.load(f)
                    print(f"✅ {cookie_file}:")
                    print(f"   추출 시간: {data.get('extracted_at', 'Unknown')}")
                    print(f"   추출 방법: {data.get('method', 'Unknown')}")
                    print(f"   쿠키 개수: {len(data.get('cookies', {}))}")
            except Exception as e:
                print(f"⚠️ {cookie_file} 읽기 실패: {e}")
    
    if found_files:
        print(f"📂 쿠키 파일: {len(found_files)}개 발견")
        return True
    else:
        print("⚠️ 쿠키 파일이 없습니다.")
        return False

def main():
    """메인 테스트 실행"""
    print(f"⏰ 데이터베이스 통합 테스트 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # 1. 데이터베이스 상태 확인
    results.append(("데이터베이스 상태", check_database_status()))
    
    # 2. API 수집 테스트
    results.append(("API 수집", test_api_collection()))
    
    # 3. 시각화 확인
    results.append(("웹 대시보드", check_visualization()))
    
    # 4. 쿠키 시스템 확인
    results.append(("쿠키 시스템", check_cookie_system()))
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📋 테스트 결과 요약")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 전체 결과: {passed}/{len(results)} 통과")
    
    if passed == len(results):
        print("🎉 모든 테스트 통과!")
    else:
        print("⚠️ 일부 테스트 실패 - 시스템 점검 필요")
    
    print("\n💡 수동 확인 사항:")
    print("1. 브라우저에서 http://localhost:32542/ 접속하여 대시보드 확인")
    print("2. REGTECH 데이터가 차트에 올바르게 표시되는지 확인")
    print("3. 실제 쿠키로 수집 테스트 (수동)")
    
    print(f"\n🕐 테스트 종료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()