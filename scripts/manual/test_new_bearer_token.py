#!/usr/bin/env python3
"""
새로운 Bearer Token으로 Excel 다운로드 테스트
"""
import requests
import pandas as pd
from datetime import datetime, timedelta

def test_excel_with_new_token():
    """새 토큰으로 Excel 다운로드"""
    print("🧪 새 Bearer Token으로 Excel 다운로드 테스트\n")
    
    # 방금 얻은 새 토큰
    bearer_token = "BearereyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJuZXh0cmFkZSIsIm9yZ2FubmFtZSI6IuuEpeyKpO2KuOugiIzdtOuTnCIsImlkIjoibmV4dHJhZGUiLCJleHAiOjE3NTExMjY2NTcsInVzZXJuYW1lIjoi7J6l7ZmN7KSAIn0.w0yrogG80Qd3mzvTIgcB_Uc_V2fswamAikitKMpvPRDSJ5TWsaCpr_w-P_W3cD16ico141M_nMvTp9f_lU_YGg"
    
    session = requests.Session()
    session.cookies.set('regtech-va', bearer_token, domain='regtech.fsec.or.kr', path='/')
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    })
    
    # 날짜 범위
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Excel 다운로드
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
    
    print(f"날짜 범위: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    try:
        # Excel 다운로드
        print("\n📥 Excel 다운로드 중...")
        response = session.post(
            'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryListDownloadXlsx',
            data=excel_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://regtech.fsec.or.kr',
                'Referer': 'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList',
            },
            timeout=60,
            stream=True
        )
        
        print(f"응답 상태: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        
        if response.status_code == 200:
            # Excel 파일 저장
            filename = 'regtech_new_token_test.xlsx'
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"\n✅ Excel 파일 저장: {filename}")
            
            # 파일 크기 확인
            import os
            file_size = os.path.getsize(filename)
            print(f"파일 크기: {file_size:,} bytes")
            
            if file_size > 1000:  # 1KB 이상이면 성공
                # Excel 읽기
                try:
                    df = pd.read_excel(filename)
                    print(f"\n📊 Excel 데이터:")
                    print(f"행 수: {len(df)}")
                    print(f"열: {list(df.columns)}")
                    
                    if len(df) > 0:
                        print(f"\n✅ 성공! {len(df)}개의 IP 데이터를 받았습니다.")
                        print("\n샘플 (처음 5개):")
                        print(df.head())
                        return True
                except Exception as e:
                    print(f"Excel 읽기 오류: {e}")
                    
                    # 파일 내용 확인
                    with open(filename, 'rb') as f:
                        content = f.read(200)
                        if b'<!DOCTYPE' in content or b'<html' in content:
                            print("❌ HTML 응답을 받았습니다 (로그인 페이지일 수 있음)")
            else:
                print("❌ 파일이 너무 작습니다")
                
        return False
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_excel_with_new_token()
    if success:
        print("\n🎉 새 Bearer Token이 작동합니다!")
        print("\n이제 이 토큰을 Docker 환경변수에 설정하면 됩니다:")
        print("export REGTECH_BEARER_TOKEN=\"Bearer...\"")
    else:
        print("\n💥 토큰이 작동하지 않습니다")