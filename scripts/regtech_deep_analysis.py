#!/usr/bin/env python3
"""
REGTECH 심층 분석 - 실제 응답 내용 확인
"""
import requests
import re
from datetime import datetime, timedelta

def analyze_regtech_responses():
    """REGTECH 응답 심층 분석"""
    print("🔍 REGTECH 응답 심층 분석")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    # 1. 메인 페이지 응답 분석
    print("\n1. 메인 페이지 분석...")
    try:
        main_resp = session.get("https://regtech.fsec.or.kr/main/main", timeout=30)
        print(f"   Status: {main_resp.status_code}")
        print(f"   Content-Type: {main_resp.headers.get('Content-Type')}")
        print(f"   Content-Length: {len(main_resp.text)}")
        
        # HTML 내용 분석
        if '로그인' in main_resp.text:
            print("   ✅ 로그인 페이지 확인됨")
        if 'IP' in main_resp.text or 'blacklist' in main_resp.text.lower():
            print("   ✅ IP/블랙리스트 관련 내용 발견")
        
        # 숨겨진 폼 찾기
        forms = re.findall(r'<form[^>]*>(.*?)</form>', main_resp.text, re.DOTALL)
        print(f"   폼 개수: {len(forms)}")
        
        # 스크립트에서 API 엔드포인트 찾기
        script_urls = re.findall(r'["\']([^"\']*api[^"\']*)["\']', main_resp.text)
        if script_urls:
            print(f"   발견된 API URLs: {set(script_urls)}")
        
    except Exception as e:
        print(f"   오류: {e}")
    
    # 2. Advisory 페이지 분석
    print("\n2. Advisory 페이지 분석...")
    try:
        advisory_resp = session.get("https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList", timeout=30)
        print(f"   Status: {advisory_resp.status_code}")
        print(f"   Content-Length: {len(advisory_resp.text)}")
        
        # JavaScript 분석
        js_patterns = [
            r'function\s+(\w*download\w*)',
            r'function\s+(\w*excel\w*)',
            r'function\s+(\w*export\w*)',
            r'url\s*:\s*["\']([^"\']*download[^"\']*)["\']',
            r'url\s*:\s*["\']([^"\']*excel[^"\']*)["\']'
        ]
        
        for pattern in js_patterns:
            matches = re.findall(pattern, advisory_resp.text, re.IGNORECASE)
            if matches:
                print(f"   JS 패턴 '{pattern}': {matches}")
        
        # 숨겨진 입력 필드 찾기
        hidden_inputs = re.findall(r'<input[^>]*type=["\']hidden["\'][^>]*>', advisory_resp.text)
        print(f"   숨겨진 입력: {len(hidden_inputs)}개")
        
        for hidden in hidden_inputs[:3]:  # 처음 3개만 출력
            name_match = re.search(r'name=["\']([^"\']*)["\']', hidden)
            value_match = re.search(r'value=["\']([^"\']*)["\']', hidden)
            if name_match:
                print(f"     {name_match.group(1)}: {value_match.group(1) if value_match else 'N/A'}")
        
    except Exception as e:
        print(f"   오류: {e}")
    
    # 3. Excel 엔드포인트 상세 분석
    print("\n3. Excel 엔드포인트 상세 분석...")
    
    # 다양한 파라미터 조합 시도
    param_combinations = [
        {},  # 빈 파라미터
        {'page': '0'},
        {'tabSort': 'blacklist'},
        {'page': '0', 'tabSort': 'blacklist'},
        {'page': '0', 'tabSort': 'blacklist', 'size': '10'},
        {'startDate': '20240101', 'endDate': '20240131'},
        {'findCondition': 'all'},
        # HAR에서 추출한 정확한 파라미터
        {
            'page': '0',
            'tabSort': 'blacklist',
            'excelDownload': 'security,blacklist,weakpoint,',
            'startDate': (datetime.now() - timedelta(days=30)).strftime('%Y%m%d'),
            'endDate': datetime.now().strftime('%Y%m%d'),
            'findCondition': 'all',
            'size': '10'
        }
    ]
    
    excel_url = "https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryListDownloadXlsx"
    
    for i, params in enumerate(param_combinations):
        try:
            print(f"\n   시도 {i+1}: {params}")
            
            # GET 시도
            get_resp = session.get(excel_url, params=params, timeout=30)
            print(f"     GET: {get_resp.status_code}, Content-Type: {get_resp.headers.get('Content-Type', 'N/A')}")
            
            # POST 시도
            post_resp = session.post(excel_url, data=params, timeout=30)
            print(f"     POST: {post_resp.status_code}, Content-Type: {post_resp.headers.get('Content-Type', 'N/A')}")
            
            # Content-Disposition 확인
            content_disp = post_resp.headers.get('Content-Disposition')
            if content_disp:
                print(f"     Content-Disposition: {content_disp}")
            
            # 응답 크기 확인
            if post_resp.status_code == 200:
                content_length = len(post_resp.content)
                print(f"     응답 크기: {content_length} bytes")
                
                # 실제 Excel인지 확인 (Excel 파일은 PK로 시작)
                if post_resp.content.startswith(b'PK'):
                    print(f"     ✅ Excel 파일 형식 확인!")
                    
                    # 파일 저장
                    filename = f"/tmp/regtech_attempt_{i+1}.xlsx"
                    with open(filename, 'wb') as f:
                        f.write(post_resp.content)
                    print(f"     📁 파일 저장: {filename}")
                    
                    # Excel 파일 읽기 시도
                    try:
                        import pandas as pd
                        df = pd.read_excel(filename)
                        print(f"     📊 Excel 데이터: {len(df)} 행, {len(df.columns)} 열")
                        print(f"     📋 컬럼: {list(df.columns)}")
                        
                        # IP 찾기
                        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
                        all_text = df.to_string()
                        ips = re.findall(ip_pattern, all_text)
                        public_ips = [ip for ip in set(ips) if is_public_ip(ip)]
                        
                        if public_ips:
                            print(f"     🎯 발견된 공인 IP: {len(public_ips)}개")
                            print(f"     📋 샘플: {public_ips[:5]}")
                            return {
                                'success': True,
                                'method': f'param_combination_{i+1}',
                                'ips': public_ips,
                                'file': filename,
                                'params': params
                            }
                        
                    except Exception as excel_error:
                        print(f"     ❌ Excel 읽기 오류: {excel_error}")
                
                # HTML 응답인 경우 내용 미리보기
                elif 'text/html' in post_resp.headers.get('Content-Type', ''):
                    preview = post_resp.text[:300].replace('\n', ' ').replace('  ', ' ')
                    print(f"     HTML 미리보기: {preview}...")
            
        except Exception as e:
            print(f"     오류: {e}")
    
    # 4. robots.txt 및 sitemap 확인
    print("\n4. robots.txt 및 sitemap 확인...")
    try:
        robots_resp = session.get("https://regtech.fsec.or.kr/robots.txt", timeout=15)
        if robots_resp.status_code == 200:
            print(f"   robots.txt 발견:")
            print(f"   {robots_resp.text[:300]}")
        
        sitemap_resp = session.get("https://regtech.fsec.or.kr/sitemap.xml", timeout=15)
        if sitemap_resp.status_code == 200:
            print(f"   sitemap.xml 발견")
            # sitemap에서 URL 추출
            urls = re.findall(r'<loc>(.*?)</loc>', sitemap_resp.text)
            blacklist_urls = [url for url in urls if 'blacklist' in url.lower()]
            if blacklist_urls:
                print(f"   블랙리스트 관련 URL: {blacklist_urls}")
    
    except Exception as e:
        print(f"   오류: {e}")
    
    return {'success': False, 'message': 'No working method found'}

def is_public_ip(ip: str) -> bool:
    """공인 IP 확인"""
    try:
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        
        first = int(parts[0])
        second = int(parts[1])
        
        # 사설 IP 제외
        if first == 10:
            return False
        if first == 172 and 16 <= second <= 31:
            return False
        if first == 192 and second == 168:
            return False
        if first == 127:
            return False
        if first == 0 or first >= 224:
            return False
        
        return True
    except:
        return False

if __name__ == "__main__":
    result = analyze_regtech_responses()
    
    print("\n" + "="*60)
    print("📊 심층 분석 결과")
    print("="*60)
    
    if result['success']:
        print(f"✅ 성공한 방법: {result['method']}")
        print(f"🎯 발견된 IP: {len(result['ips'])}개")
        print(f"📁 저장된 파일: {result['file']}")
        print(f"📋 사용된 파라미터: {result['params']}")
    else:
        print(f"❌ {result['message']}")
        print("🔄 다른 방법을 계속 시도중...")