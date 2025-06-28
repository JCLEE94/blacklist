#!/usr/bin/env python3
"""
REGTECH Excel 파싱 디버깅
"""
import pandas as pd
import re

def is_valid_ip(ip: str) -> bool:
    """IP 주소 유효성 검증"""
    try:
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
        
        # 사설 IP 및 특수 IP 제외
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

def test_excel_parsing():
    print("REGTECH Excel 파싱 테스트")
    
    # Excel 파일 읽기
    df = pd.read_excel('test_download.xlsx')
    print(f"\nExcel 파일 정보:")
    print(f"- 행 수: {len(df)}")
    print(f"- 컬럼: {list(df.columns)}")
    
    # IP 컬럼 찾기
    ip_column = None
    for col in df.columns:
        print(f"\n컬럼 확인: '{col}'")
        print(f"  - 'IP' in col.upper(): {'IP' in col.upper()}")
        print(f"  - 'ip' in col: {'ip' in col}")
        
        if 'IP' in col.upper() or 'ip' in col:
            ip_column = col
            print(f"  → IP 컬럼 발견: '{col}'")
            break
    
    if not ip_column:
        print("\n❌ IP 컬럼을 찾을 수 없음")
        return
    
    print(f"\n✅ IP 컬럼: '{ip_column}'")
    
    # IP 파싱 테스트
    valid_count = 0
    invalid_count = 0
    sample_ips = []
    
    for idx, row in df.iterrows():
        try:
            ip = str(row[ip_column]).strip()
            
            if is_valid_ip(ip):
                valid_count += 1
                if len(sample_ips) < 5:
                    sample_ips.append((idx, ip, row.get('국가', ''), row.get('등록사유', '')))
            else:
                invalid_count += 1
                if invalid_count <= 5:
                    print(f"\n무효한 IP (행 {idx}): '{ip}'")
                    print(f"  - Type: {type(row[ip_column])}")
                    print(f"  - Raw value: {repr(row[ip_column])}")
                    
        except Exception as e:
            print(f"\n오류 (행 {idx}): {e}")
            print(f"  - Row data: {row}")
    
    print(f"\n결과:")
    print(f"- 유효한 IP: {valid_count}")
    print(f"- 무효한 IP: {invalid_count}")
    
    if sample_ips:
        print(f"\n유효한 IP 샘플:")
        for idx, ip, country, reason in sample_ips:
            print(f"  {idx}: {ip} ({country}) - {reason}")

if __name__ == "__main__":
    test_excel_parsing()