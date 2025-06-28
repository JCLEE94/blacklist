#!/usr/bin/env python3
"""
REGTECH AJAX 기반 데이터 수집 테스트
"""
import requests
import json
from datetime import datetime, timedelta

def test_regtech_ajax():
    """AJAX 엔드포인트로 직접 데이터 요청"""
    print("🧪 REGTECH AJAX 데이터 수집 테스트")
    
    base_url = "https://regtech.fsec.or.kr"
    
    # Bearer Token
    bearer_token = "BearereyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJuZXh0cmFkZSIsIm9yZ2FubmFtZSI6IuuEpeyKpO2KuOugiOydtOuTnCIsImlkIjoibmV4dHJhZGUiLCJleHAiOjE3NTExMTkyNzYsInVzZXJuYW1lIjoi7J6l7ZmN7KSAIn0.YwZHoHZCVqDnaryluB0h5_ituxYcaRz4voT7GRfgrNrP86W8TfvBuJbHMON4tJa4AQmNP-XhC_PuAVPQTjJADA"
    
    # 세션 생성
    session = requests.Session()
    session.cookies.set('regtech-va', bearer_token, domain='regtech.fsec.or.kr', path='/')
    
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
        'X-Requested-With': 'XMLHttpRequest',
        'Authorization': f'Bearer {bearer_token[6:]}'
    })
    
    try:
        # 날짜 설정
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        start_date_str = start_date.strftime('%Y%m%d')
        end_date_str = end_date.strftime('%Y%m%d')
        
        print(f"날짜 범위: {start_date_str} ~ {end_date_str}")
        
        # 1. AJAX 엔드포인트 시도 (JSON 응답 기대)
        ajax_endpoints = [
            "/fcti/securityAdvisory/getAdvisoryList",
            "/fcti/securityAdvisory/advisoryListAjax",
            "/fcti/securityAdvisory/blacklistData",
            "/api/securityAdvisory/blacklist",
            "/fcti/api/blacklist"
        ]
        
        for endpoint in ajax_endpoints:
            print(f"\n시도: {endpoint}")
            
            # JSON 요청
            json_data = {
                'page': 0,
                'size': 100,
                'tabSort': 'blacklist',
                'startDate': start_date_str,
                'endDate': end_date_str,
                'findCondition': 'all',
                'findKeyword': ''
            }
            
            try:
                resp = session.post(
                    f"{base_url}{endpoint}",
                    json=json_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                
                print(f"응답: {resp.status_code}")
                
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        print(f"JSON 응답 받음: {type(data)}")
                        
                        # 데이터 구조 분석
                        if isinstance(data, dict):
                            print(f"키: {list(data.keys())}")
                            
                            # 가능한 데이터 필드들
                            for key in ['data', 'list', 'items', 'blacklist', 'ips', 'content']:
                                if key in data:
                                    print(f"'{key}' 필드 발견: {len(data[key])}개 항목")
                                    if data[key]:
                                        print(f"샘플: {data[key][:2]}")
                                        return True
                        
                        elif isinstance(data, list):
                            print(f"리스트 응답: {len(data)}개 항목")
                            if data:
                                print(f"샘플: {data[:2]}")
                                return True
                    
                    except json.JSONDecodeError:
                        print("JSON 파싱 실패 - HTML 응답일 수 있음")
                
            except requests.exceptions.RequestException as e:
                print(f"요청 실패: {e}")
        
        # 2. Form 데이터로 재시도
        print("\n\n2. Form 데이터로 AJAX 요청...")
        
        form_data = {
            'page': '0',
            'tabSort': 'blacklist',
            'startDate': start_date_str,
            'endDate': end_date_str,
            'size': '100'
        }
        
        resp = session.post(
            f"{base_url}/fcti/securityAdvisory/advisoryList",
            data=form_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest'
            },
            timeout=30
        )
        
        print(f"Form 요청 응답: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
        
        # 응답 분석
        if 'json' in resp.headers.get('Content-Type', ''):
            try:
                data = resp.json()
                print(f"JSON 데이터: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
                return True
            except:
                pass
        
        # 3. Excel 다운로드 엔드포인트 (Bearer Token 사용)
        print("\n\n3. Excel 다운로드 시도...")
        
        excel_data = {
            'page': '0',
            'tabSort': 'blacklist',
            'excelDownload': 'security,blacklist,weakpoint,',
            'startDate': start_date_str,
            'endDate': end_date_str,
            'size': '1000'  # 더 많은 데이터
        }
        
        excel_resp = session.post(
            f"{base_url}/fcti/securityAdvisory/advisoryListDownloadXlsx",
            data=excel_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': f"{base_url}/fcti/securityAdvisory/advisoryList"
            },
            stream=True,
            timeout=60
        )
        
        print(f"Excel 응답: {excel_resp.status_code}")
        print(f"Content-Type: {excel_resp.headers.get('Content-Type', 'N/A')}")
        print(f"Content-Disposition: {excel_resp.headers.get('Content-Disposition', 'N/A')}")
        
        if 'excel' in excel_resp.headers.get('Content-Type', '') or 'xlsx' in excel_resp.headers.get('Content-Type', ''):
            print("✅ Excel 파일 수신!")
            
            # 파일 저장
            with open('regtech_data.xlsx', 'wb') as f:
                for chunk in excel_resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print("Excel 파일 저장됨: regtech_data.xlsx")
            
            # pandas로 읽기 시도
            try:
                import pandas as pd
                df = pd.read_excel('regtech_data.xlsx')
                print(f"Excel 데이터: {len(df)}행")
                print(df.head())
                return True
            except Exception as e:
                print(f"Excel 파싱 실패: {e}")
        
        return False
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_regtech_ajax()
    if success:
        print("\n🎉 AJAX 데이터 수집 성공!")
    else:
        print("\n💥 AJAX 데이터 수집 실패")