#!/usr/bin/env python3
"""
전체 UI 기능 테스트 및 검증
모든 API 엔드포인트와 웹 UI 기능을 체계적으로 테스트
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Any

# 테스트 설정 - 환경변수 기반
import os
BASE_URL = os.getenv('TEST_BASE_URL', "http://localhost:9999")
TEST_IPS = os.getenv('TEST_IPS', "8.8.8.8,1.1.1.1,192.168.1.1,10.0.0.1").split(',')

class BlacklistUITester:
    """블랙리스트 UI 전체 기능 테스트"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = {}
        
    def log(self, message: str, level: str = "INFO"):
        """테스트 로그"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def test_endpoint(self, endpoint: str, method: str = "GET", 
                     data: Dict = None, headers: Dict = None) -> Dict[str, Any]:
        """API 엔드포인트 테스트"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers, timeout=10)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, headers=headers, timeout=10)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, headers=headers, timeout=10)
            else:
                response = self.session.request(method, url, json=data, headers=headers, timeout=10)
            
            result = {
                "success": True,
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "content_type": response.headers.get("Content-Type", ""),
                "response_size": len(response.content)
            }
            
            # JSON 응답 파싱 시도
            try:
                result["json_data"] = response.json()
            except:
                result["text_data"] = response.text[:500]  # 처음 500자만
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status_code": None,
                "response_time": None
            }
    
    def test_basic_endpoints(self):
        """기본 API 엔드포인트 테스트"""
        self.log("🔍 기본 API 엔드포인트 테스트 시작")
        
        basic_endpoints = [
            ("/health", "GET"),
            ("/api/health", "GET"), 
            ("/api/stats", "GET"),
            ("/api/blacklist/active", "GET"),
            ("/api/fortigate", "GET"),
            ("/", "GET"),  # 메인 페이지
        ]
        
        results = {}
        for endpoint, method in basic_endpoints:
            self.log(f"Testing {method} {endpoint}")
            result = self.test_endpoint(endpoint, method)
            results[endpoint] = result
            
            if result["success"]:
                self.log(f"✅ {endpoint}: {result['status_code']} ({result['response_time']:.3f}s)")
            else:
                self.log(f"❌ {endpoint}: {result['error']}", "ERROR")
        
        self.test_results["basic_endpoints"] = results
        return results
    
    def test_search_functionality(self):
        """IP 검색 기능 테스트"""
        self.log("🔎 IP 검색 기능 테스트 시작")
        
        results = {}
        
        # 단일 IP 검색
        for ip in TEST_IPS:
            endpoint = f"/api/search/{ip}"
            self.log(f"Testing single IP search: {ip}")
            result = self.test_endpoint(endpoint)
            results[f"search_{ip}"] = result
            
            if result["success"]:
                self.log(f"✅ IP {ip}: {result['status_code']}")
            else:
                self.log(f"❌ IP {ip}: {result['error']}", "ERROR")
        
        # 배치 IP 검색
        self.log("Testing batch IP search")
        batch_data = {"ips": TEST_IPS}
        result = self.test_endpoint("/api/search", "POST", batch_data)
        results["batch_search"] = result
        
        if result["success"]:
            self.log(f"✅ Batch search: {result['status_code']}")
        else:
            self.log(f"❌ Batch search: {result['error']}", "ERROR")
        
        self.test_results["search_functionality"] = results
        return results
    
    def test_collection_management(self):
        """수집 관리 기능 테스트"""
        self.log("📊 수집 관리 기능 테스트 시작")
        
        results = {}
        
        collection_endpoints = [
            ("/api/collection/status", "GET"),
            ("/api/collection/regtech/status", "GET"),
            ("/api/collection/secudium/status", "GET"),
            ("/api/collection/regtech/trigger", "POST"),
            ("/api/collection/secudium/trigger", "POST"),
        ]
        
        for endpoint, method in collection_endpoints:
            self.log(f"Testing {method} {endpoint}")
            result = self.test_endpoint(endpoint, method)
            results[endpoint] = result
            
            if result["success"]:
                self.log(f"✅ {endpoint}: {result['status_code']}")
            else:
                self.log(f"❌ {endpoint}: {result['error']}", "ERROR")
            
            # 수집 트리거 후 잠시 대기
            if "trigger" in endpoint and result["success"]:
                time.sleep(2)
        
        self.test_results["collection_management"] = results
        return results
    
    def test_advanced_features(self):
        """고급 기능 테스트"""
        self.log("⚡ 고급 기능 테스트 시작")
        
        results = {}
        
        advanced_endpoints = [
            ("/api/v2/blacklist/enhanced", "GET"),
            ("/api/v2/analytics/trends", "GET"),
            ("/api/v2/sources/status", "GET"),
            ("/api/stats/detection-trends", "GET"),
            ("/api/monitoring/system", "GET"),
            ("/api/monitoring/performance", "GET"),
        ]
        
        for endpoint, method in advanced_endpoints:
            self.log(f"Testing {method} {endpoint}")
            result = self.test_endpoint(endpoint, method)
            results[endpoint] = result
            
            if result["success"]:
                self.log(f"✅ {endpoint}: {result['status_code']}")
            else:
                self.log(f"❌ {endpoint}: {result['error']}", "ERROR")
        
        self.test_results["advanced_features"] = results
        return results
    
    def test_web_ui_pages(self):
        """웹 UI 페이지 테스트"""
        self.log("🌐 웹 UI 페이지 테스트 시작")
        
        results = {}
        
        ui_pages = [
            ("/", "메인 페이지"),
            ("/dashboard", "대시보드"),
            ("/search", "검색 페이지"),
            ("/collection", "수집 관리"),
            ("/analytics", "분석 페이지"),
            ("/admin", "관리자 페이지"),
        ]
        
        for endpoint, description in ui_pages:
            self.log(f"Testing UI page: {description}")
            result = self.test_endpoint(endpoint)
            results[endpoint] = result
            
            if result["success"]:
                # HTML 페이지인지 확인
                is_html = "text/html" in result.get("content_type", "")
                self.log(f"✅ {description}: {result['status_code']} (HTML: {is_html})")
            else:
                self.log(f"❌ {description}: {result['error']}", "ERROR")
        
        self.test_results["web_ui_pages"] = results
        return results
    
    def test_bulk_operations(self):
        """벌크 작업 테스트"""
        self.log("📦 벌크 작업 테스트 시작")
        
        results = {}
        
        # 벌크 IP 임포트 테스트
        bulk_data = {
            "ips": [
                {"ip": "203.104.144.10", "source": "TEST", "threat_type": "malware"},
                {"ip": "185.220.101.32", "source": "TEST", "threat_type": "botnet"}
            ],
            "source": "BULK_TEST"
        }
        
        self.log("Testing bulk IP import")
        result = self.test_endpoint("/api/bulk/import", "POST", bulk_data)
        results["bulk_import"] = result
        
        if result["success"]:
            self.log(f"✅ Bulk import: {result['status_code']}")
        else:
            self.log(f"❌ Bulk import: {result['error']}", "ERROR")
        
        # 벌크 내보내기 테스트
        self.log("Testing bulk export")
        result = self.test_endpoint("/api/bulk/export", "GET")
        results["bulk_export"] = result
        
        if result["success"]:
            self.log(f"✅ Bulk export: {result['status_code']}")
        else:
            self.log(f"❌ Bulk export: {result['error']}", "ERROR")
        
        self.test_results["bulk_operations"] = results
        return results
    
    def test_real_time_features(self):
        """실시간 기능 테스트"""
        self.log("⏱️ 실시간 기능 테스트 시작")
        
        results = {}
        
        realtime_endpoints = [
            ("/api/realtime/stats", "GET"),
            ("/api/realtime/alerts", "GET"),
            ("/api/realtime/collection-status", "GET"),
        ]
        
        for endpoint, method in realtime_endpoints:
            self.log(f"Testing {method} {endpoint}")
            result = self.test_endpoint(endpoint, method)
            results[endpoint] = result
            
            if result["success"]:
                self.log(f"✅ {endpoint}: {result['status_code']}")
            else:
                self.log(f"❌ {endpoint}: {result['error']}", "ERROR")
        
        self.test_results["realtime_features"] = results
        return results
    
    def run_comprehensive_test(self):
        """전체 기능 종합 테스트"""
        self.log("🚀 블랙리스트 UI 전체 기능 테스트 시작")
        self.log(f"Base URL: {self.base_url}")
        
        start_time = time.time()
        
        # 각 기능별 테스트 실행
        test_functions = [
            self.test_basic_endpoints,
            self.test_search_functionality,
            self.test_collection_management,
            self.test_advanced_features,
            self.test_web_ui_pages,
            self.test_bulk_operations,
            self.test_real_time_features,
        ]
        
        for test_func in test_functions:
            try:
                test_func()
                self.log(f"✅ {test_func.__name__} 완료")
            except Exception as e:
                self.log(f"❌ {test_func.__name__} 실패: {e}", "ERROR")
            
            time.sleep(1)  # 테스트 간 간격
        
        # 결과 요약
        self.generate_test_summary()
        
        end_time = time.time()
        self.log(f"🏁 전체 테스트 완료 (소요시간: {end_time - start_time:.2f}초)")
    
    def generate_test_summary(self):
        """테스트 결과 요약 생성"""
        self.log("📋 테스트 결과 요약 생성")
        
        total_tests = 0
        successful_tests = 0
        failed_tests = 0
        
        for category, tests in self.test_results.items():
            self.log(f"\n📂 {category.upper()}:")
            
            for test_name, result in tests.items():
                total_tests += 1
                
                if result["success"] and result.get("status_code") == 200:
                    successful_tests += 1
                    status = "✅ PASS"
                else:
                    failed_tests += 1
                    status = "❌ FAIL"
                
                response_time = result.get("response_time") or 0
                self.log(f"   {status} {test_name} ({response_time:.3f}s)")
        
        # 전체 요약
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        self.log("\n🎯 전체 테스트 결과:")
        self.log(f"   총 테스트: {total_tests}")
        self.log(f"   성공: {successful_tests}")
        self.log(f"   실패: {failed_tests}")
        self.log(f"   성공률: {success_rate:.1f}%")
        
        # 실패한 테스트가 있으면 상세 정보 출력
        if failed_tests > 0:
            self.log("\n❌ 실패한 테스트 상세:")
            for category, tests in self.test_results.items():
                for test_name, result in tests.items():
                    if not result["success"] or result.get("status_code") != 200:
                        error = result.get("error", f"HTTP {result.get('status_code', 'Unknown')}")
                        self.log(f"   {test_name}: {error}")
        
        # 결과를 JSON 파일로 저장
        with open("ui_test_results.json", "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        
        self.log("\n📄 상세 결과가 ui_test_results.json에 저장되었습니다.")

def main():
    """메인 함수"""
    tester = BlacklistUITester()
    tester.run_comprehensive_test()

if __name__ == "__main__":
    main()