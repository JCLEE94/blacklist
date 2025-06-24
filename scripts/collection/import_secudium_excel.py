#!/usr/bin/env python3
"""
SECUDIUM 엑셀 파일 임포트 스크립트
"""
import sys
import pandas as pd
from pathlib import Path
import requests
import json

def import_secudium_excel(filepath):
    """SECUDIUM 엑셀 파일을 시스템에 임포트"""
    try:
        # 파일 존재 확인
        if not Path(filepath).exists():
            print(f"❌ 파일을 찾을 수 없음: {filepath}")
            return False
            
        # 엑셀 파일 읽기
        df = pd.read_excel(filepath)
        print(f"📊 데이터 로드: {len(df)}행")
        
        # IP 컬럼 찾기
        ip_columns = [col for col in df.columns if 'ip' in str(col).lower() or 'addr' in str(col).lower()]
        if not ip_columns:
            print("❌ IP 컬럼을 찾을 수 없음")
            return False
            
        ip_column = ip_columns[0]
        print(f"📋 IP 컬럼: {ip_column}")
        
        # IP 주소 추출
        ips = df[ip_column].dropna().astype(str).tolist()
        valid_ips = [ip.strip() for ip in ips if ip.strip() and '.' in ip]
        
        print(f"🔍 유효한 IP: {len(valid_ips)}개")
        
        # API로 임포트
        api_url = "http://localhost:1541/api/admin/import/secudium"
        
        # 임시 파일로 다시 저장 (API 업로드용)
        temp_file = Path("/tmp/secudium_import.xlsx")
        df.to_excel(temp_file, index=False)
        
        with open(temp_file, 'rb') as f:
            files = {'file': f}
            response = requests.post(api_url, files=files)
            
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 임포트 성공: {result}")
            return True
        else:
            print(f"❌ 임포트 실패: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("사용법: python3 import_secudium_excel.py <엑셀파일경로>")
        sys.exit(1)
        
    filepath = sys.argv[1]
    success = import_secudium_excel(filepath)
    sys.exit(0 if success else 1)
