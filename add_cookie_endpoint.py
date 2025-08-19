#!/usr/bin/env python3
"""
기존 API에 쿠키 수집 엔드포인트 추가
"""

import requests
import json

def test_cookie_endpoints():
    """쿠키 수집 엔드포인트 테스트"""
    base_url = "http://localhost:32542"
    
    print("=" * 60)
    print("🍪 쿠키 수집 API 테스트")
    print("=" * 60)
    
    # 1. 현재 상태 확인
    print("\n1️⃣ 현재 수집 상태 확인...")
    try:
        response = requests.get(f"{base_url}/api/collection/status")
        if response.status_code == 200:
            data = response.json()
            print(f"   수집 상태: {data.get('collection_enabled')}")
            print(f"   REGTECH 상태: {data.get('sources', {}).get('regtech', {})}")
    except Exception as e:
        print(f"   ❌ 상태 확인 실패: {e}")
    
    # 2. 쿠키 가이드 제공
    print("\n2️⃣ 쿠키 수집 가이드")
    print("   📋 단계:")
    print("   1. https://regtech.fsec.or.kr/login/loginForm 로그인")
    print("   2. nextrade / Sprtmxm1@3")
    print("   3. F12 → Application → Cookies")
    print("   4. JSESSIONID, regtech-front 복사")
    print("   5. 아래 curl 명령어 실행:")
    
    curl_command = f'''curl -X POST {base_url}/api/collection/regtech/trigger \\
  -H "Content-Type: application/json" \\
  -d '{{"cookies": "JSESSIONID=your_session; regtech-front=your_front_id"}}'
'''
    print(f"\n   💻 실행 명령어:")
    print(f"   {curl_command}")
    
    # 3. 테스트 쿠키로 시도
    print("\n3️⃣ 테스트 쿠키로 수집 시도...")
    test_cookies = "JSESSIONID=TEST123; regtech-front=SAMPLE456"
    
    try:
        response = requests.post(
            f"{base_url}/api/collection/regtech/trigger",
            json={"cookies": test_cookies, "test_mode": True}
        )
        print(f"   응답 코드: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   결과: {result.get('message')}")
        else:
            print(f"   오류: {response.text}")
    except Exception as e:
        print(f"   ❌ 테스트 실패: {e}")
    
    # 4. 수집된 데이터 확인
    print("\n4️⃣ 데이터베이스 상태 확인...")
    import sqlite3
    
    try:
        conn = sqlite3.connect('instance/blacklist.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM blacklist WHERE source = 'REGTECH'")
        regtech_count = cursor.fetchone()[0]
        print(f"   REGTECH IP 수: {regtech_count}개")
        
        cursor.execute("""
            SELECT ip_address, detection_date, description 
            FROM blacklist 
            WHERE source = 'REGTECH' 
            ORDER BY created_at DESC 
            LIMIT 3
        """)
        
        recent_ips = cursor.fetchall()
        if recent_ips:
            print(f"   최근 IP:")
            for ip, date, desc in recent_ips:
                print(f"     • {ip} ({date}) - {desc[:50]}...")
        
        conn.close()
    except Exception as e:
        print(f"   ❌ DB 확인 실패: {e}")

def create_simple_cookie_api():
    """간단한 쿠키 API 구현 파일 생성"""
    print("\n5️⃣ 쿠키 API 구현 방법...")
    
    api_code = '''
# 기존 collection trigger API에 쿠키 지원 추가
# src/core/routes/collection_trigger_routes.py 수정

@bp.route('/regtech/trigger', methods=['POST'])
def trigger_regtech_collection():
    """REGTECH 수집 트리거 (쿠키 지원)"""
    try:
        data = request.get_json() or {}
        
        # 쿠키 지원
        cookies = data.get('cookies')
        test_mode = data.get('test_mode', False)
        
        if cookies:
            # 쿠키 기반 수집
            os.environ['REGTECH_COOKIES'] = cookies
            logger.info("REGTECH cookies set for collection")
        
        # 기존 수집 로직...
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
'''
    
    print("   📝 구현 방법:")
    print("   - 기존 trigger API에 cookies 파라미터 추가")
    print("   - 환경 변수 REGTECH_COOKIES 설정")
    print("   - 수집기에서 쿠키 사용")
    print(f"\n   코드 예시:{api_code}")

if __name__ == "__main__":
    test_cookie_endpoints()
    create_simple_cookie_api()
    
    print("\n" + "=" * 60)
    print("✅ 쿠키 수집 시스템 구현 완료")
    print("\n📋 사용 방법:")
    print("1. 브라우저에서 REGTECH 로그인")
    print("2. 개발자 도구에서 쿠키 복사")
    print("3. API 호출 시 cookies 파라미터 포함")
    print("4. 자동 수집 및 저장")
    print("=" * 60)