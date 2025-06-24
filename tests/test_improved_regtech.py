#!/usr/bin/env python3
"""
개선된 REGTECH 수집기 테스트
세션 관리 및 로그인 문제 해결 확인
"""

import os
import sys
import logging

# 로깅 설정
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

sys.path.append('/app')

def test_improved_regtech():
    print("🔍 개선된 REGTECH 수집기 테스트 시작")
    
    try:
        from src.core.regtech_collector import RegtechCollector
        
        # 수집기 생성
        collector = RegtechCollector(data_dir='/app/data')
        print("✅ RegtechCollector 생성 성공")
        
        # 세션 준비 테스트
        session = collector._prepare_session()
        print(f"✅ 세션 준비 성공: {type(session)}")
        print(f"   쿠키 수: {len(session.cookies)}")
        
        # 로그인 테스트
        login_result = collector._perform_login(session)
        print(f"🔑 로그인 결과: {login_result}")
        
        if login_result:
            print("✅ 로그인 성공! 쿠키 정보:")
            for cookie in session.cookies:
                print(f"   - {cookie.name}: {cookie.value[:20]}...")
            
            # 단일 페이지 수집 테스트 (처음 3페이지만)
            print("\n📄 개선된 페이지 수집 테스트...")
            
            total_collected = 0
            for page in range(3):
                print(f"\n페이지 {page} 수집 중...")
                page_data = collector._collect_page(session, page)
                
                if page_data:
                    print(f"✅ 페이지 {page}: {len(page_data)}개 IP 수집")
                    total_collected += len(page_data)
                    
                    # 샘플 데이터 출력
                    for i, item in enumerate(page_data[:3]):
                        print(f"   {i+1}. {item.get('ip')} - {item.get('source')}")
                else:
                    print(f"❌ 페이지 {page}: 데이터 없음")
            
            print(f"\n🎉 총 수집된 IP: {total_collected}개")
            
            # 자동 수집 테스트 (적은 페이지로)
            print("\n🚀 자동 수집 테스트 (10페이지)...")
            auto_result = collector.auto_collect(prefer_web=True)
            
            if auto_result.get('success', False):
                stats = auto_result.get('stats', {})
                print("✅ 자동 수집 성공!")
                print(f"   수집 방법: {auto_result.get('collection_method', 'unknown')}")
                print(f"   처리된 페이지: {stats.get('pages_processed', 0)}")
                print(f"   총 수집: {stats.get('total_collected', 0)}개 IP")
                print(f"   중복 제거: {stats.get('duplicate_count', 0)}개")
                print(f"   성공률: {stats.get('successful_collections', 0)}/{stats.get('total_collected', 0)}")
            else:
                print(f"❌ 자동 수집 실패: {auto_result.get('error', 'unknown')}")
        else:
            print("❌ 로그인 실패 - 자격증명을 확인하세요")
            
        session.close()
        print("\n✅ 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_improved_regtech()