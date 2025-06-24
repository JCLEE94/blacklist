#!/usr/bin/env python3
"""
REGTECH HAR 파일 완전 분석 스크립트
모든 요청, 인증, 쿠키, 헤더 정보 추출
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Any
from urllib.parse import unquote

class HARAnalyzer:
    """HAR 파일 완전 분석기"""
    
    def __init__(self, har_file_path: str):
        self.har_file_path = har_file_path
        self.har_data = None
        self.analysis_result = {}
    
    def load_har_file(self) -> bool:
        """HAR 파일 로드"""
        try:
            with open(self.har_file_path, 'r', encoding='utf-8') as f:
                self.har_data = json.load(f)
            print(f"✅ HAR 파일 로드 성공: {self.har_file_path}")
            return True
        except Exception as e:
            print(f"❌ HAR 파일 로드 실패: {e}")
            return False
    
    def analyze_complete_structure(self) -> Dict[str, Any]:
        """전체 HAR 구조 완전 분석"""
        if not self.har_data:
            return {"error": "HAR data not loaded"}
        
        log = self.har_data.get('log', {})
        entries = log.get('entries', [])
        pages = log.get('pages', [])
        
        analysis = {
            "summary": {
                "total_requests": len(entries),
                "total_pages": len(pages),
                "har_version": log.get('version', 'unknown'),
                "creator": log.get('creator', {}),
                "analysis_timestamp": "2025-06-21"
            },
            "pages": [],
            "requests": [],
            "authentication": {
                "cookies_found": [],
                "auth_headers": [],
                "session_tokens": [],
                "csrf_tokens": []
            },
            "regtech_specific": {
                "excel_download_requests": [],
                "login_attempts": [],
                "blacklist_requests": []
            },
            "security_analysis": {
                "cors_headers": [],
                "csrf_protection": [],
                "content_security_policy": []
            }
        }
        
        # 페이지 분석
        for page in pages:
            analysis["pages"].append({
                "id": page.get('id'),
                "title": page.get('title'),
                "started": page.get('startedDateTime'),
                "timing": page.get('pageTimings', {})
            })
        
        # 요청별 상세 분석
        for i, entry in enumerate(entries):
            request_analysis = self._analyze_request(entry, i)
            analysis["requests"].append(request_analysis)
            
            # 인증 관련 정보 추출
            self._extract_authentication_info(entry, analysis["authentication"])
            
            # REGTECH 특화 분석
            self._analyze_regtech_specific(entry, analysis["regtech_specific"])
            
            # 보안 헤더 분석
            self._analyze_security_headers(entry, analysis["security_analysis"])
        
        self.analysis_result = analysis
        return analysis
    
    def _analyze_request(self, entry: Dict, index: int) -> Dict[str, Any]:
        """개별 요청 상세 분석"""
        request = entry.get('request', {})
        response = entry.get('response', {})
        
        return {
            "index": index,
            "method": request.get('method'),
            "url": request.get('url'),
            "status": response.get('status'),
            "started_time": entry.get('startedDateTime'),
            "total_time": entry.get('time'),
            "timing_breakdown": entry.get('timings', {}),
            "request_headers": {h['name']: h['value'] for h in request.get('headers', [])},
            "response_headers": {h['name']: h['value'] for h in response.get('headers', [])},
            "request_cookies": request.get('cookies', []),
            "response_cookies": response.get('cookies', []),
            "post_data": request.get('postData', {}),
            "query_string": request.get('queryString', []),
            "server_ip": entry.get('serverIPAddress'),
            "error": response.get('_error'),
            "content_type": response.get('content', {}).get('mimeType'),
            "content_size": response.get('content', {}).get('size', 0)
        }
    
    def _extract_authentication_info(self, entry: Dict, auth_data: Dict):
        """인증 관련 정보 추출"""
        request = entry.get('request', {})
        response = entry.get('response', {})
        
        # 요청 쿠키 검사
        for cookie in request.get('cookies', []):
            if any(keyword in cookie.get('name', '').lower() 
                   for keyword in ['session', 'jsessionid', 'auth', 'token']):
                auth_data['cookies_found'].append({
                    'name': cookie.get('name'),
                    'value': cookie.get('value'),
                    'domain': cookie.get('domain'),
                    'path': cookie.get('path'),
                    'request_url': request.get('url')
                })
        
        # 응답 쿠키 검사
        for cookie in response.get('cookies', []):
            if any(keyword in cookie.get('name', '').lower() 
                   for keyword in ['session', 'jsessionid', 'auth', 'token']):
                auth_data['cookies_found'].append({
                    'name': cookie.get('name'),
                    'value': cookie.get('value'),
                    'domain': cookie.get('domain'),
                    'path': cookie.get('path'),
                    'response_url': request.get('url'),
                    'expires': cookie.get('expires')
                })
        
        # 인증 헤더 검사
        for header in request.get('headers', []):
            header_name = header.get('name', '').lower()
            if any(keyword in header_name for keyword in ['authorization', 'authentication', 'token']):
                auth_data['auth_headers'].append({
                    'name': header.get('name'),
                    'value': header.get('value'),
                    'url': request.get('url')
                })
        
        # POST 데이터에서 토큰 검사
        post_data = request.get('postData', {})
        if post_data.get('text'):
            # CSRF 토큰 찾기
            csrf_patterns = [r'_token=([^&]+)', r'csrf_token=([^&]+)', r'authenticity_token=([^&]+)']
            for pattern in csrf_patterns:
                matches = re.findall(pattern, post_data.get('text', ''))
                for match in matches:
                    auth_data['csrf_tokens'].append({
                        'token': unquote(match),
                        'url': request.get('url'),
                        'pattern': pattern
                    })
    
    def _analyze_regtech_specific(self, entry: Dict, regtech_data: Dict):
        """REGTECH 특화 분석"""
        request = entry.get('request', {})
        url = request.get('url', '')
        
        # Excel 다운로드 요청
        if 'advisoryListDownloadXlsx' in url:
            post_data = request.get('postData', {})
            regtech_data['excel_download_requests'].append({
                'url': url,
                'method': request.get('method'),
                'post_data': post_data,
                'status': entry.get('response', {}).get('status'),
                'error': entry.get('response', {}).get('_error'),
                'content_disposition': next((h['value'] for h in entry.get('response', {}).get('headers', []) 
                                           if h['name'] == 'Content-Disposition'), None)
            })
        
        # 로그인 관련 요청
        if any(keyword in url.lower() for keyword in ['login', '로그인', 'addLogin']):
            regtech_data['login_attempts'].append({
                'url': url,
                'method': request.get('method'),
                'post_data': request.get('postData', {}),
                'status': entry.get('response', {}).get('status')
            })
        
        # 블랙리스트 관련 요청
        if any(keyword in url.lower() for keyword in ['blacklist', 'advisory', 'security']):
            regtech_data['blacklist_requests'].append({
                'url': url,
                'method': request.get('method'),
                'status': entry.get('response', {}).get('status')
            })
    
    def _analyze_security_headers(self, entry: Dict, security_data: Dict):
        """보안 헤더 분석"""
        response_headers = entry.get('response', {}).get('headers', [])
        
        for header in response_headers:
            header_name = header.get('name', '').lower()
            header_value = header.get('value', '')
            
            # CORS 헤더
            if 'access-control' in header_name:
                security_data['cors_headers'].append({
                    'name': header.get('name'),
                    'value': header_value,
                    'url': entry.get('request', {}).get('url')
                })
            
            # CSP 헤더
            if 'content-security-policy' in header_name:
                security_data['content_security_policy'].append({
                    'name': header.get('name'),
                    'value': header_value,
                    'url': entry.get('request', {}).get('url')
                })
    
    def generate_comprehensive_report(self) -> str:
        """종합 분석 보고서 생성"""
        if not self.analysis_result:
            self.analyze_complete_structure()
        
        report = []
        report.append("=" * 80)
        report.append("🔍 REGTECH HAR 파일 완전 분석 보고서")
        report.append("=" * 80)
        
        # 1. 요약 정보
        summary = self.analysis_result['summary']
        report.append(f"\n📊 요약 정보:")
        report.append(f"  - 총 요청 수: {summary['total_requests']}")
        report.append(f"  - 총 페이지 수: {summary['total_pages']}")
        report.append(f"  - HAR 버전: {summary['har_version']}")
        report.append(f"  - 생성자: {summary.get('creator', {}).get('name', 'Unknown')}")
        
        # 2. REGTECH 특화 분석
        regtech = self.analysis_result['regtech_specific']
        report.append(f"\n🎯 REGTECH 특화 분석:")
        report.append(f"  - Excel 다운로드 요청: {len(regtech['excel_download_requests'])}개")
        report.append(f"  - 로그인 시도: {len(regtech['login_attempts'])}개")
        report.append(f"  - 블랙리스트 관련 요청: {len(regtech['blacklist_requests'])}개")
        
        # 3. Excel 다운로드 상세 분석
        if regtech['excel_download_requests']:
            report.append(f"\n📋 Excel 다운로드 요청 상세:")
            for i, req in enumerate(regtech['excel_download_requests']):
                report.append(f"  요청 {i+1}:")
                report.append(f"    - URL: {req['url']}")
                report.append(f"    - Method: {req['method']}")
                report.append(f"    - Status: {req['status']}")
                report.append(f"    - Error: {req.get('error', 'None')}")
                report.append(f"    - Content-Disposition: {req.get('content_disposition', 'None')}")
                
                if req.get('post_data'):
                    report.append(f"    - POST 파라미터:")
                    post_params = req['post_data'].get('params', [])
                    for param in post_params:
                        report.append(f"      • {param.get('name')}: {param.get('value')}")
        
        # 4. 인증 정보 분석
        auth = self.analysis_result['authentication']
        report.append(f"\n🔐 인증 정보 분석:")
        report.append(f"  - 발견된 쿠키: {len(auth['cookies_found'])}개")
        report.append(f"  - 인증 헤더: {len(auth['auth_headers'])}개")
        report.append(f"  - CSRF 토큰: {len(auth['csrf_tokens'])}개")
        
        if auth['cookies_found']:
            report.append(f"\n🍪 발견된 쿠키:")
            for cookie in auth['cookies_found']:
                report.append(f"    - {cookie['name']}: {cookie.get('value', 'N/A')[:50]}...")
        else:
            report.append(f"\n❌ 인증 쿠키 없음 - 비인증 세션으로 요청됨")
        
        # 5. 보안 분석
        security = self.analysis_result['security_analysis']
        report.append(f"\n🛡️ 보안 분석:")
        report.append(f"  - CORS 헤더: {len(security['cors_headers'])}개")
        report.append(f"  - CSP 헤더: {len(security['content_security_policy'])}개")
        
        # 6. 핵심 발견사항
        report.append(f"\n🎯 핵심 발견사항:")
        
        # 인증 상태 확인
        has_auth_cookies = len(auth['cookies_found']) > 0
        has_csrf_tokens = len(auth['csrf_tokens']) > 0
        
        if not has_auth_cookies:
            report.append(f"  ❌ 인증 쿠키 없음 - 로그아웃 상태에서 요청")
            report.append(f"  💡 이는 인증 없이도 Excel 다운로드가 가능할 수 있음을 시사")
        
        if regtech['excel_download_requests']:
            excel_req = regtech['excel_download_requests'][0]
            if excel_req.get('error') == 'net::ERR_ABORTED':
                report.append(f"  ⚠️ Excel 다운로드 요청이 중단됨 (ERR_ABORTED)")
                report.append(f"  💡 브라우저에서 수동으로 중단했거나 타임아웃 발생")
            
            if excel_req.get('content_disposition'):
                report.append(f"  ✅ 서버에서 Excel 파일명 응답: {excel_req['content_disposition']}")
                report.append(f"  💡 서버는 파일 다운로드를 준비했음")
        
        # 7. 권장사항
        report.append(f"\n💡 권장사항:")
        
        if not has_auth_cookies:
            report.append(f"  1. 인증 없이 Excel 다운로드 엔드포인트 직접 호출 시도")
            report.append(f"  2. POST 파라미터 그대로 사용하여 요청")
            report.append(f"  3. 브라우저 헤더 정확히 모방")
        
        report.append(f"  4. 요청 타임아웃을 충분히 길게 설정 (60초 이상)")
        report.append(f"  5. stream=True로 대용량 파일 처리")
        report.append(f"  6. Content-Disposition 헤더 확인하여 파일명 추출")
        
        return "\n".join(report)
    
    def extract_working_request_code(self) -> str:
        """실제 동작하는 요청 코드 생성"""
        if not self.analysis_result:
            self.analyze_complete_structure()
        
        excel_requests = self.analysis_result['regtech_specific']['excel_download_requests']
        if not excel_requests:
            return "# Excel 다운로드 요청을 찾을 수 없습니다."
        
        excel_req = excel_requests[0]
        post_data = excel_req.get('post_data', {})
        params = post_data.get('params', [])
        
        code = []
        code.append("#!/usr/bin/env python3")
        code.append('"""')
        code.append("HAR 분석 기반 실제 동작하는 REGTECH 수집 코드")
        code.append('"""')
        code.append("import requests")
        code.append("from datetime import datetime, timedelta")
        code.append("")
        code.append("def collect_regtech_data():")
        code.append('    """HAR 분석 결과를 바탕으로 한 정확한 요청"""')
        code.append("")
        code.append("    # 기본 설정")
        code.append('    base_url = "https://regtech.fsec.or.kr"')
        code.append('    endpoint = "/fcti/securityAdvisory/advisoryListDownloadXlsx"')
        code.append("")
        code.append("    # HAR에서 추출한 정확한 헤더")
        code.append("    headers = {")
        
        # 주요 헤더 추출
        req_headers = self.analysis_result['requests'][0]['request_headers']
        essential_headers = [
            'User-Agent', 'Accept', 'Accept-Encoding', 'Accept-Language',
            'Content-Type', 'Origin', 'Referer', 'Sec-Fetch-Dest',
            'Sec-Fetch-Mode', 'Sec-Fetch-Site', 'Cache-Control', 'Pragma'
        ]
        
        for header_name in essential_headers:
            if header_name in req_headers:
                code.append(f'        "{header_name}": "{req_headers[header_name]}",')
        
        code.append("    }")
        code.append("")
        code.append("    # HAR에서 추출한 정확한 POST 파라미터")
        code.append("    form_data = {")
        
        for param in params:
            name = param.get('name')
            value = param.get('value')
            if name in ['startDate', 'endDate']:
                if name == 'startDate':
                    code.append(f'        "{name}": (datetime.now() - timedelta(days=90)).strftime("%Y%m%d"),  # 3개월 전')
                else:
                    code.append(f'        "{name}": datetime.now().strftime("%Y%m%d"),  # 오늘')
            else:
                code.append(f'        "{name}": "{value}",')
        
        code.append("    }")
        code.append("")
        code.append("    # 요청 실행")
        code.append("    session = requests.Session()")
        code.append("    try:")
        code.append("        response = session.post(")
        code.append("            f'{base_url}{endpoint}',")
        code.append("            data=form_data,")
        code.append("            headers=headers,")
        code.append("            timeout=120,  # 충분한 타임아웃")
        code.append("            stream=True   # 대용량 파일 처리")
        code.append("        )")
        code.append("")
        code.append("        print(f'Status: {response.status_code}')")
        code.append("        print(f'Content-Type: {response.headers.get(\"Content-Type\")}')")
        code.append("        print(f'Content-Disposition: {response.headers.get(\"Content-Disposition\")}')")
        code.append("")
        code.append("        if response.status_code == 200:")
        code.append("            content_type = response.headers.get('Content-Type', '')")
        code.append("            if 'excel' in content_type or 'spreadsheet' in content_type:")
        code.append("                filename = f'regtech_{datetime.now().strftime(\"%Y%m%d_%H%M%S\")}.xlsx'")
        code.append("                with open(filename, 'wb') as f:")
        code.append("                    f.write(response.content)")
        code.append("                print(f'✅ Excel 파일 저장: {filename}')")
        code.append("                return True")
        code.append("            else:")
        code.append("                print(f'❌ 예상하지 못한 응답: {response.text[:200]}')")
        code.append("        else:")
        code.append("            print(f'❌ HTTP 오류: {response.status_code}')")
        code.append("")
        code.append("    except Exception as e:")
        code.append("        print(f'❌ 요청 실패: {e}')")
        code.append("")
        code.append("    return False")
        code.append("")
        code.append('if __name__ == "__main__":')
        code.append("    collect_regtech_data()")
        
        return "\n".join(code)

def main():
    """메인 실행 함수"""
    har_file = "/home/jclee/dev/blacklist/document/har_backup/regtech.fsec.or.kr.har"
    
    analyzer = HARAnalyzer(har_file)
    
    if not analyzer.load_har_file():
        return
    
    # 완전 분석 실행
    analysis = analyzer.analyze_complete_structure()
    
    # 보고서 생성
    report = analyzer.generate_comprehensive_report()
    print(report)
    
    # 실행 가능한 코드 생성
    working_code = analyzer.extract_working_request_code()
    
    # 결과 파일로 저장
    output_dir = Path(__file__).parent.parent / 'data' / 'har_analysis'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 분석 결과 JSON 저장
    with open(output_dir / 'har_complete_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    
    # 보고서 저장
    with open(output_dir / 'har_analysis_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    
    # 실행 코드 저장
    with open(output_dir / 'regtech_har_based_collector.py', 'w', encoding='utf-8') as f:
        f.write(working_code)
    
    print(f"\n📁 분석 결과 저장 위치:")
    print(f"  - 상세 분석: {output_dir / 'har_complete_analysis.json'}")
    print(f"  - 보고서: {output_dir / 'har_analysis_report.txt'}")
    print(f"  - 실행 코드: {output_dir / 'regtech_har_based_collector.py'}")

if __name__ == "__main__":
    main()