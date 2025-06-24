#!/usr/bin/env python3
"""
document 폴더에서 실제 IP 추출
"""
import re
import json
from pathlib import Path
from collections import defaultdict

def extract_ips_from_files():
    """HTML 파일에서 실제 IP 추출"""
    base_path = Path("/home/jclee/dev/blacklist/document")
    ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
    
    # 찾은 IP들과 출처 저장
    found_ips = defaultdict(list)
    
    # 제외할 IP 패턴
    exclude_patterns = [
        r'^192\.168\.',  # 사설 IP
        r'^10\.',         # 사설 IP
        r'^127\.',        # 로컬호스트
        r'^0\.',          # 예약된 IP
        r'\.0$',          # 네트워크 주소
        r'^255\.',        # 브로드캐스트
    ]
    
    # HTML 파일 검색
    for html_file in base_path.rglob("*.html"):
        # 제외할 폴더
        if any(skip in str(html_file) for skip in ['css', 'js', 'vendor', 'font']):
            continue
            
        try:
            with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # IP 찾기
                ips = ip_pattern.findall(content)
                
                for ip in ips:
                    # 제외 패턴 체크
                    if any(re.match(pattern, ip) for pattern in exclude_patterns):
                        continue
                    
                    # 유효한 IP 체크
                    parts = ip.split('.')
                    if all(0 <= int(part) <= 255 for part in parts):
                        found_ips[ip].append(str(html_file.relative_to(base_path)))
                        
        except Exception as e:
            print(f"Error reading {html_file}: {e}")
    
    return found_ips

def analyze_regtech_data():
    """REGTECH blackListView에서 상세 정보 추출"""
    view_file = Path("/home/jclee/dev/blacklist/document/regtech/regtech.fsec.or.kr/regtech.fsec.or.kr/fcti/securityAdvisory/blackListView.html")
    
    if view_file.exists():
        with open(view_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 구체적인 정보 추출
        ip_match = re.search(r'<th>아이피</th>\s*<td>\s*([\d.]+)', content)
        country_match = re.search(r'<th>국가</th>\s*<td>(\w+)</td>', content)
        reason_match = re.search(r'<th>등록사유</th>\s*<td[^>]*>\s*([^<]+)', content)
        reg_date_match = re.search(r'<th>등록일</th>\s*<td>\s*([\d-]+)', content)
        release_date_match = re.search(r'<th>해제일</th>\s*<td>\s*([\d-]+)', content)
        
        if ip_match:
            return {
                'ip': ip_match.group(1).strip(),
                'country': country_match.group(1).strip() if country_match else 'Unknown',
                'reason': reason_match.group(1).strip() if reason_match else 'Unknown',
                'registration_date': reg_date_match.group(1).strip() if reg_date_match else 'Unknown',
                'release_date': release_date_match.group(1).strip() if release_date_match else 'Unknown'
            }
    return None

def main():
    print("=== Document 폴더에서 실제 IP 추출 ===\n")
    
    # 1. 모든 HTML에서 IP 추출
    found_ips = extract_ips_from_files()
    
    print(f"총 {len(found_ips)}개의 고유 IP 발견:\n")
    
    # IP별로 정렬하여 출력
    for ip, sources in sorted(found_ips.items()):
        # 실제 악성 IP일 가능성이 높은 것들만
        if not ip.startswith(('192.168.', '10.', '127.', '172.')):
            print(f"IP: {ip}")
            for source in sources[:3]:  # 처음 3개 소스만 표시
                print(f"  - {source}")
            if len(sources) > 3:
                print(f"  ... 외 {len(sources)-3}개 파일")
            print()
    
    # 2. REGTECH 상세 정보 분석
    print("\n=== REGTECH BlackList 상세 정보 ===")
    regtech_info = analyze_regtech_data()
    if regtech_info:
        print(f"IP: {regtech_info['ip']}")
        print(f"국가: {regtech_info['country']}")
        print(f"등록사유: {regtech_info['reason']}")
        print(f"등록일: {regtech_info['registration_date']}")
        print(f"해제일: {regtech_info['release_date']}")
    
    # 3. 실제 악성 IP 목록 생성
    real_malicious_ips = []
    for ip in found_ips:
        # 공인 IP만 선택
        if not any(ip.startswith(prefix) for prefix in ['192.168.', '10.', '127.', '172.', '0.', '255.']):
            # 일반적인 웹 서버 IP가 아닌 것
            if not any(ip.startswith(prefix) for prefix in ['8.8.', '1.1.', '216.58.', '52.84.']):
                real_malicious_ips.append(ip)
    
    print(f"\n=== 실제 악성 IP 후보 ({len(real_malicious_ips)}개) ===")
    for ip in real_malicious_ips[:20]:  # 처음 20개만
        print(f"  - {ip}")
    
    # JSON으로 저장
    output_data = {
        'found_ips': dict(found_ips),
        'regtech_detail': regtech_info,
        'malicious_candidates': real_malicious_ips
    }
    
    with open('data/document_extracted_ips.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n결과가 data/document_extracted_ips.json에 저장되었습니다.")

if __name__ == "__main__":
    main()