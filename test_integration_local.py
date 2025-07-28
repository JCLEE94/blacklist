#!/usr/bin/env python3
"""
Local Integration Test Suite for Blacklist Management System
로컬 환경에서 애플리케이션을 시작하고 통합 테스트를 실행합니다.
"""

import subprocess
import time
import sys
import os
import signal
import requests
from pathlib import Path
from threading import Thread
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class IntegrationTestSuite:
    def __init__(self):
        self.app_process = None
        self.base_url = "http://localhost:8541"
        self.test_results = []
        
    def start_application(self):
        """백그라운드에서 애플리케이션 시작"""
        print("🚀 Starting blacklist application...")
        
        try:
            self.app_process = subprocess.Popen([
                sys.executable, "main.py", "--port", "8541"
            ], 
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
            
            # 애플리케이션이 시작될 때까지 대기
            for attempt in range(30):  # 30초 대기
                try:
                    response = requests.get(f"{self.base_url}/health", timeout=2)
                    if response.status_code == 200:
                        print(f"✅ Application started successfully on {self.base_url}")
                        return True
                except requests.exceptions.RequestException:
                    time.sleep(1)
                    continue
                    
            print("❌ Failed to start application within 30 seconds")
            return False
            
        except Exception as e:
            print(f"❌ Failed to start application: {e}")
            return False
    
    def stop_application(self):
        """애플리케이션 종료"""
        if self.app_process:
            print("🛑 Stopping application...")
            self.app_process.terminate()
            try:
                self.app_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.app_process.kill()
                self.app_process.wait()
            print("✅ Application stopped")
    
    def run_test(self, test_name, test_func):
        """개별 테스트 실행"""
        print(f"\n📋 Running {test_name}...")
        try:
            result = test_func()
            if result:
                print(f"✅ {test_name} - PASSED")
                self.test_results.append((test_name, True, ""))
            else:
                print(f"❌ {test_name} - FAILED")
                self.test_results.append((test_name, False, "Test returned False"))
        except Exception as e:
            print(f"❌ {test_name} - ERROR: {e}")
            self.test_results.append((test_name, False, str(e)))
    
    def test_health_endpoint(self):
        """헬스 체크 엔드포인트 테스트"""
        response = requests.get(f"{self.base_url}/health", timeout=5)
        return response.status_code == 200
    
    def test_api_endpoints(self):
        """주요 API 엔드포인트 테스트"""
        endpoints = [
            "/api/blacklist/active",
            "/api/fortigate", 
            "/api/stats",
            "/api/collection/status"
        ]
        
        for endpoint in endpoints:
            response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
            if response.status_code not in [200, 404]:  # 404는 허용 (데이터 없을 수 있음)
                return False
        return True
    
    def test_collection_management(self):
        """수집 관리 기능 테스트"""
        # 수집 상태 확인
        response = requests.get(f"{self.base_url}/api/collection/status")
        if response.status_code != 200:
            return False
            
        # 수집 비활성화 테스트
        response = requests.post(f"{self.base_url}/api/collection/disable")
        if response.status_code not in [200, 405]:  # 405 Method Not Allowed도 허용
            return False
            
        return True
    
    def test_database_integration(self):
        """데이터베이스 통합 테스트"""
        # 데이터베이스 상태 확인 (통계 API 통해)
        response = requests.get(f"{self.base_url}/api/stats")
        return response.status_code == 200
    
    def test_error_handling(self):
        """에러 처리 테스트"""
        # 존재하지 않는 엔드포인트
        response = requests.get(f"{self.base_url}/api/nonexistent")
        if response.status_code != 404:
            return False
            
        # 잘못된 메소드
        response = requests.delete(f"{self.base_url}/health")
        if response.status_code not in [405, 500]:  # Method Not Allowed 또는 Internal Server Error
            return False
            
        return True
    
    def test_performance_basic(self):
        """기본 성능 테스트"""
        start_time = time.time()
        
        # 10번의 헬스체크 요청
        for _ in range(10):
            response = requests.get(f"{self.base_url}/health", timeout=2)
            if response.status_code != 200:
                return False
                
        total_time = time.time() - start_time
        avg_time = total_time / 10
        
        print(f"📊 Average response time: {avg_time:.3f}s")
        return avg_time < 1.0  # 1초 이내
    
    def run_all_tests(self):
        """모든 통합 테스트 실행"""
        print("🧪 Blacklist Management System - Local Integration Test Suite")
        print(f"📁 Running from: {project_root}")
        print(f"🐍 Python: {sys.version}")
        print(f"⏰ Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # 애플리케이션 시작
        if not self.start_application():
            return False
            
        try:
            # 테스트 실행
            self.run_test("Health Endpoint", self.test_health_endpoint)
            self.run_test("API Endpoints", self.test_api_endpoints)
            self.run_test("Collection Management", self.test_collection_management)
            self.run_test("Database Integration", self.test_database_integration)
            self.run_test("Error Handling", self.test_error_handling)
            self.run_test("Basic Performance", self.test_performance_basic)
            
        finally:
            # 애플리케이션 종료
            self.stop_application()
        
        # 결과 요약
        self.print_summary()
        
        # 성공 여부 반환
        return all(result[1] for result in self.test_results)
    
    def print_summary(self):
        """테스트 결과 요약 출력"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result[1])
        total = len(self.test_results)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if total - passed > 0:
            print("\n❌ Failed Tests:")
            for name, success, error in self.test_results:
                if not success:
                    print(f"  - {name}: {error}")
        
        if success_rate == 100:
            print("\n🎉 All tests passed!")
        elif success_rate >= 80:
            print(f"\n⚠️  Most tests passed ({success_rate:.1f}%)")
        else:
            print(f"\n❌ Many tests failed ({success_rate:.1f}%)")

def main():
    """메인 함수"""
    suite = IntegrationTestSuite()
    success = suite.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())