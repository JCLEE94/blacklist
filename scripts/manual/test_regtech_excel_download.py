#!/usr/bin/env python3
"""
REGTECH Excel 다운로드 방식 테스트
PowerShell 스크립트를 Python으로 변환
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
import io
import os

def download_regtech_excel():
    """REGTECH Excel 파일 다운로드"""
    print("📊 REGTECH Excel 다운로드 테스트\n")
    
    # Bearer Token (PowerShell에서 제공)
    bearer_token = "BearereyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJuZXh0cmFkZSIsIm9yZ2FubmFtZSI6IuuEpeyKpO2KuOugiIzdtOuTnCIsImlkIjoibmV4dHJhZGUiLCJleHAiOjE3NTExMTkyNzYsInVzZXJuYW1lIjoi7J6l7ZmN7KSAIn0.YwZHoHZCVqDnaryluB0h5_ituxYcaRz4voT7GRfgrNrP86W8TfvBuJbHMON4tJa4AQmNP-XhC_PuAVPQTjJADA"
    
    session = requests.Session()
    
    # 쿠키 설정 (PowerShell 스크립트와 동일)
    session.cookies.set('_ga', 'GA1.1.215465125.1748404470', domain='.fsec.or.kr', path='/')
    session.cookies.set('regtech-front', '0236FE878AD466A0DBA59F898DA14924', domain='regtech.fsec.or.kr', path='/')
    session.cookies.set('regtech-va', bearer_token, domain='regtech.fsec.or.kr', path='/')
    session.cookies.set('_ga_7WRDYHF66J', 'GS2.1.s1751032862$o16$g1$t1751036793$j46$l0$h0', domain='.fsec.or.kr', path='/')
    
    # 헤더 설정
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'max-age=0',
        'Origin': 'https://regtech.fsec.or.kr',
        'Referer': 'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    }
    
    # 날짜 설정
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # POST 데이터
    data = {
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
    
    print(f"날짜 범위: {data['startDate']} ~ {data['endDate']}")
    
    try:
        # Excel 다운로드 요청
        print("\n📥 Excel 파일 다운로드 중...")
        response = session.post(
            'https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryListDownloadXlsx',
            headers=headers,
            data=data,
            timeout=60,
            stream=True
        )
        
        print(f"응답 상태: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        print(f"Content-Length: {response.headers.get('Content-Length', 'unknown')} bytes")
        
        if response.status_code == 200:
            # Excel 파일인지 확인
            content_type = response.headers.get('Content-Type', '')
            if 'excel' in content_type or 'spreadsheet' in content_type or 'octet-stream' in content_type:
                # 파일 저장
                filename = 'regtech_blacklist.xlsx'
                with open(filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print(f"\n✅ Excel 파일 저장됨: {filename}")
                
                # Excel 파일 읽기
                try:
                    df = pd.read_excel(filename)
                    print(f"\n📊 Excel 데이터:")
                    print(f"행 수: {len(df)}")
                    print(f"열: {list(df.columns)}")
                    
                    if len(df) > 0:
                        print(f"\n샘플 데이터 (처음 5행):")
                        print(df.head())
                        
                        # IP 컬럼 찾기
                        ip_column = None
                        for col in df.columns:
                            if 'IP' in col.upper() or 'ip' in col:
                                ip_column = col
                                break
                        
                        if ip_column:
                            ips = df[ip_column].tolist()
                            print(f"\n🎯 총 {len(ips)}개 IP 수집됨")
                            print("샘플 IP:")
                            for ip in ips[:10]:
                                print(f"  - {ip}")
                            
                            return True
                    else:
                        print("❌ Excel 파일에 데이터가 없음")
                    
                except Exception as e:
                    print(f"❌ Excel 파일 읽기 오류: {e}")
                    
                    # 파일 내용 확인
                    with open(filename, 'rb') as f:
                        content = f.read(200)
                        print(f"\n파일 시작 부분: {content[:100]}")
                        
                        # HTML인지 확인
                        if b'<!DOCTYPE' in content or b'<html' in content:
                            print("❌ Excel이 아닌 HTML 응답을 받음")
                            with open('regtech_excel_response.html', 'wb') as html_f:
                                html_f.write(content)
                                f.seek(0)
                                html_f.write(f.read())
                            print("💾 HTML 응답이 regtech_excel_response.html로 저장됨")
            else:
                print(f"❌ Excel이 아닌 응답: {content_type}")
                
                # 응답 내용 저장
                with open('regtech_excel_response.txt', 'wb') as f:
                    f.write(response.content)
                print("💾 응답이 regtech_excel_response.txt로 저장됨")
        else:
            print(f"❌ 다운로드 실패: {response.status_code}")
            
        return False
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # pandas 설치 확인
    try:
        import pandas
        print("✅ pandas 설치됨\n")
    except ImportError:
        print("❌ pandas가 설치되지 않았습니다.")
        print("설치: pip install pandas openpyxl")
        exit(1)
    
    success = download_regtech_excel()
    if success:
        print("\n🎉 Excel 다운로드 방식으로 데이터 수집 성공!")
        print("\n💡 이 방식을 regtech_collector.py에 추가할 수 있습니다.")
    else:
        print("\n💥 Excel 다운로드 실패")