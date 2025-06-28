#!/usr/bin/env python3
"""
REGTECH Excel 수집 스크립트
Bearer token이 필요할 때 수동으로 실행

사용법:
1. 브라우저에서 regtech.fsec.or.kr 로그인
2. F12 → Application → Cookies → regtech-va 값 복사
3. REGTECH_BEARER_TOKEN=Bearer... python3 regtech_excel_collector.py
"""
import os
import sys
import requests
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
import json

def collect_regtech_excel(bearer_token=None):
    """REGTECH Excel 다운로드 및 DB 저장"""
    
    if not bearer_token:
        bearer_token = os.getenv('REGTECH_BEARER_TOKEN')
        if not bearer_token:
            print("❌ REGTECH_BEARER_TOKEN 환경변수가 필요합니다.")
            print("\n사용법:")
            print("1. 브라우저에서 https://regtech.fsec.or.kr 로그인")
            print("2. F12 → Application → Cookies → regtech-va 값 복사")
            print("3. REGTECH_BEARER_TOKEN='Bearer...' python3 regtech_excel_collector.py")
            return False
    
    print("🔄 REGTECH Excel 수집 시작...")
    
    # 세션 설정
    session = requests.Session()
    session.cookies.set('regtech-va', bearer_token, domain='regtech.fsec.or.kr', path='/')
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    })
    
    # 날짜 범위
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    # Excel 다운로드
    excel_url = "https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryListDownloadXlsx"
    excel_data = {
        'page': '0',
        'tabSort': 'blacklist',
        'excelDownload': 'blacklist,',
        'cveId': '',
        'ipId': '',
        'estId': '',
        'startDate': start_date.strftime('%Y%m%d'),
        'endDate': end_date.strftime('%Y%m%d'),
        'findCondition': 'all',
        'findKeyword': '',
        'excelDown': 'blacklist',
        'size': '10'
    }
    
    print(f"📅 날짜 범위: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    try:
        response = session.post(
            excel_url,
            data=excel_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://regtech.fsec.or.kr',
                'Referer': 'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList',
            },
            timeout=60
        )
        
        if response.status_code == 200:
            # Excel 파일 저장
            filename = f'regtech_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ Excel 파일 다운로드 완료: {filename}")
            
            # Excel 읽기
            df = pd.read_excel(filename)
            print(f"📊 총 {len(df)}개 데이터")
            
            # 데이터베이스 저장
            if save_to_database(df):
                print("✅ 데이터베이스 저장 완료")
                
                # 파일 삭제 (선택사항)
                # os.remove(filename)
                
                return True
            else:
                print("❌ 데이터베이스 저장 실패")
                return False
        else:
            print(f"❌ 다운로드 실패: {response.status_code}")
            # 리다이렉트인 경우 토큰 만료
            if response.status_code == 302:
                print("💡 Bearer token이 만료되었습니다. 새로 로그인해서 토큰을 얻어주세요.")
            return False
            
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False


def save_to_database(df):
    """DataFrame을 데이터베이스에 저장"""
    try:
        # DB 연결
        db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'blacklist.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 기존 REGTECH 데이터 삭제
        cursor.execute("DELETE FROM blacklist_ip WHERE source = 'REGTECH'")
        print(f"🗑️ 기존 REGTECH 데이터 삭제: {cursor.rowcount}개")
        
        # 새 데이터 삽입
        inserted = 0
        for idx, row in df.iterrows():
            try:
                ip = str(row['IP']).strip()
                
                # IP 유효성 검증
                if not is_valid_ip(ip):
                    continue
                
                # 데이터 추출
                country = str(row.get('국가', 'Unknown')).strip()
                attack_type = str(row.get('등록사유', 'REGTECH')).strip()
                detection_date = str(row.get('등록일', datetime.now().strftime('%Y-%m-%d'))).strip()
                
                # 삽입
                cursor.execute("""
                    INSERT INTO blacklist_ip (ip_address, source, added_date, is_active)
                    VALUES (?, ?, ?, ?)
                """, (ip, 'REGTECH', datetime.now(), 1))
                
                inserted += 1
                
            except Exception as e:
                print(f"행 {idx} 처리 오류: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        print(f"✅ {inserted}개 IP 저장됨")
        return True
        
    except Exception as e:
        print(f"데이터베이스 오류: {e}")
        return False


def is_valid_ip(ip):
    """IP 주소 유효성 검증"""
    try:
        import re
        if not ip or not isinstance(ip, str):
            return False
        
        # IP 패턴 검증
        ip_pattern = re.compile(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$')
        if not ip_pattern.match(ip):
            return False
        
        # 각 옥텟 범위 검증
        parts = ip.split('.')
        for part in parts:
            if not 0 <= int(part) <= 255:
                return False
        
        # 사설 IP 제외
        if parts[0] == '192' and parts[1] == '168':
            return False
        if parts[0] == '10':
            return False
        if parts[0] == '172' and 16 <= int(parts[1]) <= 31:
            return False
        if parts[0] in ['0', '127', '255']:
            return False
        
        return True
    except:
        return False


if __name__ == "__main__":
    # pandas 확인
    try:
        import pandas
    except ImportError:
        print("❌ pandas가 필요합니다: pip install pandas openpyxl")
        sys.exit(1)
    
    # 실행
    success = collect_regtech_excel()
    if success:
        print("\n🎉 REGTECH 수집 완료!")
    else:
        print("\n💥 REGTECH 수집 실패")