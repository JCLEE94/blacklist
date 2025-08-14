#!/usr/bin/env python3
"""
UI 기능 종합 검증 스크립트
프로덕션 환경에서 모든 UI 기능이 의도대로 작동하는지 확인
"""

import json
import logging
import requests
import time
from typing import Dict, List, Any
from urllib.parse import urljoin

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UIFunctionVerifier:
    """UI 기능 검증 클래스"""
    
    def __init__(self, base_url: str = "http://blacklist.jclee.me"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 10
        self.verification_results = []
        
    def verify_all_functions(self) -> Dict[str, Any]:
        """모든 UI 기능 검증 실행"""
        logger.info(f"🔍 UI 기능 종합 검증 시작: {self.base_url}")
        
        tests = [
            ("CSP 헤더 검증", self.verify_csp_headers),
            ("메인 페이지 로딩", self.verify_main_page),
            ("CSS 리소스 로딩", self.verify_css_loading),
            ("JavaScript 리소스 로딩", self.verify_js_loading),
            ("API 엔드포인트 접근", self.verify_api_endpoints),
            ("네비게이션 메뉴", self.verify_navigation),
            ("데이터 관리 페이지", self.verify_data_management),
            ("블랙리스트 검색", self.verify_blacklist_search),
            ("연결 상태 페이지", self.verify_connection_status),
            ("시스템 로그 페이지", self.verify_system_logs),
            ("수집 제어 기능", self.verify_collection_controls),
            ("통계 및 분석", self.verify_analytics),
            ("헬스체크 엔드포인트", self.verify_health_endpoints)
        ]
        
        results = {
            "total_tests": len(tests),
            "passed": 0,
            "failed": 0,
            "details": []
        }
        
        for test_name, test_func in tests:
            try:
                logger.info(f"📋 테스트 실행: {test_name}")
                result = test_func()
                if result["success"]:
                    results["passed"] += 1
                    logger.info(f"✅ {test_name}: 성공")
                else:
                    results["failed"] += 1
                    logger.error(f"❌ {test_name}: 실패 - {result.get('error', 'Unknown error')}")
                
                results["details"].append({
                    "test": test_name,
                    "success": result["success"],
                    "error": result.get("error"),
                    "details": result.get("details")
                })
                
            except Exception as e:
                results["failed"] += 1
                logger.error(f"❌ {test_name}: 예외 발생 - {str(e)}")
                results["details"].append({
                    "test": test_name,
                    "success": False,
                    "error": f"Exception: {str(e)}"
                })
        
        # 결과 요약
        success_rate = (results["passed"] / results["total_tests"]) * 100
        logger.info(f"\n📊 검증 결과 요약:")
        logger.info(f"   총 테스트: {results['total_tests']}")
        logger.info(f"   성공: {results['passed']}")
        logger.info(f"   실패: {results['failed']}")
        logger.info(f"   성공률: {success_rate:.1f}%")
        
        results["success_rate"] = success_rate
        return results
    
    def verify_csp_headers(self) -> Dict[str, Any]:
        """CSP 헤더 검증"""
        try:
            response = self.session.head(self.base_url)
            csp_header = response.headers.get('Content-Security-Policy', '')
            
            # 'sel' 대신 'self'가 있는지 확인
            if "'self'" in csp_header and "'sel'" not in csp_header:
                return {"success": True, "details": "CSP 헤더가 올바르게 설정됨"}
            else:
                return {
                    "success": False, 
                    "error": "CSP 헤더에 'sel' 오타가 여전히 존재",
                    "details": csp_header
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def verify_main_page(self) -> Dict[str, Any]:
        """메인 페이지 로딩 검증"""
        try:
            response = self.session.get(self.base_url)
            if response.status_code == 200:
                # HTML 기본 구조 확인
                content = response.text
                required_elements = ['<title>', '<nav', '<main', '</html>']
                missing = [elem for elem in required_elements if elem not in content]
                
                if not missing:
                    return {"success": True, "details": "메인 페이지 정상 로딩"}
                else:
                    return {
                        "success": False, 
                        "error": f"HTML 요소 누락: {missing}"
                    }
            else:
                return {
                    "success": False, 
                    "error": f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def verify_css_loading(self) -> Dict[str, Any]:
        """CSS 리소스 로딩 검증"""
        try:
            # Bootstrap CSS 확인
            css_urls = [
                urljoin(self.base_url, "/static/css/bootstrap.min.css"),
                urljoin(self.base_url, "/static/css/style.css"),
                "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
            ]
            
            loaded_css = []
            failed_css = []
            
            for css_url in css_urls:
                try:
                    response = self.session.get(css_url, timeout=5)
                    if response.status_code == 200:
                        loaded_css.append(css_url)
                    else:
                        failed_css.append(f"{css_url} (HTTP {response.status_code})")
                except Exception as e:
                    failed_css.append(f"{css_url} (Error: {str(e)})")
            
            if loaded_css:
                return {
                    "success": True, 
                    "details": f"로딩된 CSS: {len(loaded_css)}개"
                }
            else:
                return {
                    "success": False, 
                    "error": "CSS 파일을 로딩할 수 없음",
                    "details": failed_css
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def verify_js_loading(self) -> Dict[str, Any]:
        """JavaScript 리소스 로딩 검증"""
        try:
            js_urls = [
                urljoin(self.base_url, "/static/js/bootstrap.min.js"),
                urljoin(self.base_url, "/static/js/app.js"),
                "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"
            ]
            
            loaded_js = []
            failed_js = []
            
            for js_url in js_urls:
                try:
                    response = self.session.get(js_url, timeout=5)
                    if response.status_code == 200:
                        loaded_js.append(js_url)
                    else:
                        failed_js.append(f"{js_url} (HTTP {response.status_code})")
                except Exception as e:
                    failed_js.append(f"{js_url} (Error: {str(e)})")
            
            if loaded_js:
                return {
                    "success": True, 
                    "details": f"로딩된 JS: {len(loaded_js)}개"
                }
            else:
                return {
                    "success": False, 
                    "error": "JavaScript 파일을 로딩할 수 없음",
                    "details": failed_js
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def verify_api_endpoints(self) -> Dict[str, Any]:
        """API 엔드포인트 검증"""
        try:
            api_endpoints = [
                "/api/health",
                "/api/blacklist/active", 
                "/api/fortigate",
                "/api/collection/status",
                "/api/v2/analytics/trends",
                "/api/v2/sources/status"
            ]
            
            working_apis = []
            broken_apis = []
            
            for endpoint in api_endpoints:
                try:
                    url = urljoin(self.base_url, endpoint)
                    response = self.session.get(url, timeout=5)
                    if response.status_code == 200:
                        working_apis.append(endpoint)
                    else:
                        broken_apis.append(f"{endpoint} (HTTP {response.status_code})")
                except Exception as e:
                    broken_apis.append(f"{endpoint} (Error: {str(e)})")
            
            success_rate = len(working_apis) / len(api_endpoints)
            if success_rate >= 0.8:  # 80% 이상 성공하면 통과
                return {
                    "success": True, 
                    "details": f"작동하는 API: {len(working_apis)}/{len(api_endpoints)}"
                }
            else:
                return {
                    "success": False, 
                    "error": f"API 성공률 부족: {success_rate:.1%}",
                    "details": {"working": working_apis, "broken": broken_apis}
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def verify_navigation(self) -> Dict[str, Any]:
        """네비게이션 메뉴 검증"""
        try:
            response = self.session.get(self.base_url)
            if response.status_code != 200:
                return {"success": False, "error": f"HTTP {response.status_code}"}
            
            content = response.text
            nav_items = [
                'data-management', 
                'blacklist-search', 
                'connection-status', 
                'system-logs'
            ]
            
            found_items = []
            missing_items = []
            
            for item in nav_items:
                if item in content:
                    found_items.append(item)
                else:
                    missing_items.append(item)
            
            if len(found_items) >= len(nav_items) * 0.75:  # 75% 이상 발견
                return {
                    "success": True, 
                    "details": f"네비게이션 항목 발견: {len(found_items)}/{len(nav_items)}"
                }
            else:
                return {
                    "success": False, 
                    "error": f"네비게이션 항목 부족",
                    "details": {"found": found_items, "missing": missing_items}
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def verify_data_management(self) -> Dict[str, Any]:
        """데이터 관리 페이지 검증"""
        try:
            url = urljoin(self.base_url, "/data-management")
            response = self.session.get(url)
            
            if response.status_code == 200:
                content = response.text
                expected_elements = ['collection', 'export', 'import']
                found = sum(1 for elem in expected_elements if elem in content.lower())
                
                if found >= 2:
                    return {"success": True, "details": f"데이터 관리 요소 {found}개 발견"}
                else:
                    return {"success": False, "error": "데이터 관리 기능 요소 부족"}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def verify_blacklist_search(self) -> Dict[str, Any]:
        """블랙리스트 검색 기능 검증"""
        try:
            url = urljoin(self.base_url, "/blacklist-search")
            response = self.session.get(url)
            
            if response.status_code == 200:
                content = response.text.lower()
                search_elements = ['search', 'input', 'button']
                found = sum(1 for elem in search_elements if elem in content)
                
                if found >= 2:
                    return {"success": True, "details": "검색 기능 요소 정상"}
                else:
                    return {"success": False, "error": "검색 기능 요소 부족"}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def verify_connection_status(self) -> Dict[str, Any]:
        """연결 상태 페이지 검증"""
        try:
            url = urljoin(self.base_url, "/connection-status")
            response = self.session.get(url)
            
            if response.status_code == 200:
                return {"success": True, "details": "연결 상태 페이지 접근 가능"}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def verify_system_logs(self) -> Dict[str, Any]:
        """시스템 로그 페이지 검증"""
        try:
            url = urljoin(self.base_url, "/system-logs")
            response = self.session.get(url)
            
            if response.status_code == 200:
                return {"success": True, "details": "시스템 로그 페이지 접근 가능"}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def verify_collection_controls(self) -> Dict[str, Any]:
        """수집 제어 기능 검증"""
        try:
            status_url = urljoin(self.base_url, "/api/collection/status")
            response = self.session.get(status_url)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and 'collection_enabled' in data:
                    return {"success": True, "details": f"수집 상태: {data.get('collection_enabled')}"}
                else:
                    return {"success": False, "error": "수집 상태 데이터 형식 오류"}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def verify_analytics(self) -> Dict[str, Any]:
        """통계 및 분석 기능 검증"""
        try:
            analytics_urls = [
                "/api/v2/analytics/trends",
                "/api/v2/sources/status"
            ]
            
            working_count = 0
            for url in analytics_urls:
                try:
                    response = self.session.get(urljoin(self.base_url, url))
                    if response.status_code == 200:
                        working_count += 1
                except:
                    pass
            
            if working_count >= 1:
                return {"success": True, "details": f"분석 API {working_count}개 작동"}
            else:
                return {"success": False, "error": "분석 API 접근 불가"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def verify_health_endpoints(self) -> Dict[str, Any]:
        """헬스체크 엔드포인트 검증"""
        try:
            health_urls = ["/health", "/healthz", "/ready", "/api/health"]
            working_count = 0
            
            for url in health_urls:
                try:
                    response = self.session.get(urljoin(self.base_url, url))
                    if response.status_code == 200:
                        working_count += 1
                except:
                    pass
            
            if working_count >= 3:
                return {"success": True, "details": f"헬스체크 {working_count}개 정상"}
            else:
                return {"success": False, "error": f"헬스체크 부족: {working_count}개만 작동"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}


def main():
    """메인 실행 함수"""
    verifier = UIFunctionVerifier()
    results = verifier.verify_all_functions()
    
    # 결과를 JSON 파일로 저장
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    result_file = f"ui_verification_results_{timestamp}.json"
    
    try:
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"📄 검증 결과 저장됨: {result_file}")
    except Exception as e:
        logger.error(f"결과 저장 실패: {e}")
    
    # 최종 결과 출력
    if results["success_rate"] >= 80:
        logger.info("🎉 UI 기능 검증 성공! 모든 주요 기능이 정상 작동합니다.")
        return 0
    else:
        logger.error("⚠️  UI 기능 검증 실패. 일부 기능에 문제가 있습니다.")
        return 1


if __name__ == "__main__":
    exit(main())