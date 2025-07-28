#!/usr/bin/env python3
"""
Advanced Integration Test Suite for Blacklist Management System
고급 통합 테스트: 데이터베이스, 캐시, API 엔드포인트의 심화 테스트
"""

import subprocess
import time
import sys
import os
import signal
import requests
import json
import sqlite3
import threading
import concurrent.futures
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import tempfile
import shutil

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class AdvancedIntegrationTestSuite:
    def __init__(self):
        self.app_process = None
        self.base_url = "http://localhost:8542"  # 다른 포트 사용 (충돌 방지)
        self.test_results = []
        self.temp_db_path = None
        
    def setup_test_environment(self):
        """테스트 환경 설정"""
        print("🔧 Setting up test environment...")
        
        # 임시 데이터베이스 생성
        temp_dir = tempfile.mkdtemp()
        self.temp_db_path = os.path.join(temp_dir, "test_blacklist.db")
        
        # 환경 변수 설정
        os.environ['BLACKLIST_DB_PATH'] = self.temp_db_path
        os.environ['FLASK_ENV'] = 'testing'
        os.environ['CACHE_TYPE'] = 'simple'  # 메모리 캐시 사용
        
        # 테스트 데이터베이스 초기화
        self.initialize_test_database()
        
        print(f"✅ Test environment ready (DB: {self.temp_db_path})")
        
    def cleanup_test_environment(self):
        """테스트 환경 정리"""
        if self.temp_db_path and os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)
            os.rmdir(os.path.dirname(self.temp_db_path))
        
        # 환경 변수 정리
        for env_var in ['BLACKLIST_DB_PATH', 'FLASK_ENV', 'CACHE_TYPE']:
            if env_var in os.environ:
                del os.environ[env_var]
                
    def initialize_test_database(self):
        """테스트 데이터베이스 초기화 및 샘플 데이터 삽입"""
        # 기본 스키마 생성
        result = subprocess.run([
            sys.executable, "init_database.py", "--force"
        ], cwd=project_root, capture_output=True, env=os.environ.copy())
        
        if result.returncode != 0:
            print(f"Database initialization failed: {result.stderr}")
            # 수동으로 기본 테이블 생성
            conn = sqlite3.connect(self.temp_db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blacklist_ip (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip TEXT NOT NULL,
                    source TEXT NOT NULL,
                    detection_date TEXT NOT NULL,
                    original_ip TEXT,
                    is_active INTEGER DEFAULT 1
                )
            """)
            conn.commit()
            conn.close()
        
        # 샘플 테스트 데이터 삽입
        try:
            conn = sqlite3.connect(self.temp_db_path)
            cursor = conn.cursor()
            
            # 샘플 IP 데이터
            test_ips = [
                ('192.168.1.1', 'regtech', '2025-01-01', '192.168.1.1'),
                ('10.0.0.1', 'secudium', '2025-01-02', '10.0.0.1'),
                ('172.16.0.1', 'regtech', '2025-01-03', '172.16.0.1'),
                ('203.0.113.1', 'external', '2025-01-04', '203.0.113.1'),
                ('198.51.100.1', 'regtech', '2025-01-05', '198.51.100.1'),
            ]
            
            for ip, source, date, original_ip in test_ips:
                cursor.execute("""
                    INSERT OR IGNORE INTO blacklist_ip (ip, source, detection_date, original_ip, is_active)
                    VALUES (?, ?, ?, ?, 1)
                """, (ip, source, date, original_ip))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Test database initialized with {len(test_ips)} sample IPs")
        except Exception as e:
            print(f"Warning: Could not insert sample data: {e}")
        
    def start_application(self):
        """테스트용 애플리케이션 시작"""
        print("🚀 Starting application for advanced testing...")
        
        try:
            self.app_process = subprocess.Popen([
                sys.executable, "main.py", "--port", "8542", "--debug"
            ], 
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ.copy()
        )
            
            # 애플리케이션이 시작될 때까지 대기
            for attempt in range(30):
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
        """개별 테스트 실행 (향상된 에러 처리)"""
        print(f"\n📋 Running {test_name}...")
        start_time = time.time()
        
        try:
            result = test_func()
            duration = time.time() - start_time
            
            if result:
                print(f"✅ {test_name} - PASSED ({duration:.3f}s)")
                self.test_results.append((test_name, True, "", duration))
            else:
                print(f"❌ {test_name} - FAILED ({duration:.3f}s)")
                self.test_results.append((test_name, False, "Test returned False", duration))
        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ {test_name} - ERROR: {e} ({duration:.3f}s)")
            self.test_results.append((test_name, False, str(e), duration))
    
    def test_database_crud_operations(self):
        """데이터베이스 CRUD 작업 심화 테스트"""
        try:
            conn = sqlite3.connect(self.temp_db_path)
            cursor = conn.cursor()
            
            # Create: 새 IP 추가
            test_ip = "127.0.0.1"
            cursor.execute("""
                INSERT INTO blacklist_ip (ip, source, detection_date, original_ip, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (test_ip, "test", "2025-01-06", test_ip))
            
            # Read: IP 조회
            cursor.execute("SELECT * FROM blacklist_ip WHERE ip = ?", (test_ip,))
            result = cursor.fetchone()
            if not result:
                return False
                
            # Update: IP 상태 변경
            cursor.execute("UPDATE blacklist_ip SET is_active = 0 WHERE ip = ?", (test_ip,))
            
            # Verify update
            cursor.execute("SELECT is_active FROM blacklist_ip WHERE ip = ?", (test_ip,))
            result = cursor.fetchone()
            if result[0] != 0:
                return False
                
            # Delete: IP 삭제
            cursor.execute("DELETE FROM blacklist_ip WHERE ip = ?", (test_ip,))
            
            # Verify deletion
            cursor.execute("SELECT * FROM blacklist_ip WHERE ip = ?", (test_ip,))
            result = cursor.fetchone()
            if result:
                return False
                
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Database CRUD error: {e}")
            return False
    
    def test_database_concurrent_access(self):
        """데이터베이스 동시 접근 테스트"""
        def insert_test_data(thread_id):
            try:
                conn = sqlite3.connect(self.temp_db_path)
                cursor = conn.cursor()
                
                for i in range(10):
                    ip = f"192.168.{thread_id}.{i}"
                    cursor.execute("""
                        INSERT OR IGNORE INTO blacklist_ip 
                        (ip, source, detection_date, original_ip, is_active)
                        VALUES (?, ?, ?, ?, 1)
                    """, (ip, f"thread_{thread_id}", "2025-01-07", ip))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"Thread {thread_id} error: {e}")
                return False
        
        # 5개 스레드로 동시 삽입 테스트
        threads = []
        results = []
        
        for i in range(5):
            thread = threading.Thread(target=lambda tid=i: results.append(insert_test_data(tid)))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 결과 검증
        conn = sqlite3.connect(self.temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM blacklist_ip WHERE source LIKE 'thread_%'")
        count = cursor.fetchone()[0]
        conn.close()
        
        return count == 50  # 5 threads * 10 IPs each
    
    def test_api_response_consistency(self):
        """API 응답 일관성 테스트"""
        endpoints = [
            "/api/blacklist/active",
            "/api/fortigate",
            "/api/stats",
            "/health"
        ]
        
        # 각 엔드포인트를 10번씩 호출하여 일관성 확인
        for endpoint in endpoints:
            responses = []
            for _ in range(10):
                try:
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=2)
                    responses.append((response.status_code, len(response.text)))
                    time.sleep(0.1)  # 짧은 간격
                except Exception as e:
                    print(f"Request failed for {endpoint}: {e}")
                    return False
            
            # 모든 응답이 동일한 상태 코드를 가져야 함
            status_codes = [r[0] for r in responses]
            if len(set(status_codes)) > 1:
                print(f"Inconsistent status codes for {endpoint}: {set(status_codes)}")
                return False
                
            # /api/stats 같은 동적 엔드포인트는 제외하고, 정적 데이터는 길이가 같아야 함
            if endpoint in ["/api/blacklist/active", "/api/fortigate"]:
                response_lengths = [r[1] for r in responses]
                if len(set(response_lengths)) > 1:
                    print(f"Inconsistent response lengths for {endpoint}: {set(response_lengths)}")
                    return False
        
        return True
    
    def test_api_concurrent_load(self):
        """API 동시 부하 테스트"""
        def make_request(endpoint):
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                return response.status_code == 200
            except:
                return False
        
        endpoints = ["/health", "/api/stats", "/api/blacklist/active"]
        
        # 각 엔드포인트에 동시에 20개 요청
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            
            for endpoint in endpoints:
                for _ in range(20):
                    future = executor.submit(make_request, endpoint)
                    futures.append(future)
            
            # 결과 수집
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        success_rate = sum(results) / len(results)
        print(f"📊 Concurrent load test success rate: {success_rate:.1%}")
        
        return success_rate >= 0.95  # 95% 성공률 요구
    
    def test_memory_usage_stability(self):
        """메모리 사용량 안정성 테스트"""
        import psutil
        
        # 현재 Python 프로세스의 메모리 사용량 추적
        process = psutil.Process(self.app_process.pid)
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 100번의 API 호출 후 메모리 사용량 확인
        for i in range(100):
            try:
                requests.get(f"{self.base_url}/api/blacklist/active", timeout=2)
                if i % 20 == 0:  # 20번마다 메모리 체크
                    current_memory = process.memory_info().rss / 1024 / 1024
                    print(f"📈 Memory usage after {i} requests: {current_memory:.1f}MB")
            except:
                pass
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        print(f"📊 Memory usage: {initial_memory:.1f}MB → {final_memory:.1f}MB (+{memory_increase:.1f}MB)")
        
        # 메모리 증가량이 50MB 이하면 성공
        return memory_increase < 50
    
    def test_data_integrity_after_operations(self):
        """작업 후 데이터 무결성 테스트"""
        # API를 통한 데이터 조회
        response = requests.get(f"{self.base_url}/api/blacklist/active")
        if response.status_code != 200:
            return False
            
        api_ips = set(ip.strip() for ip in response.text.split('\n') if ip.strip())
        
        # 데이터베이스에서 직접 조회
        conn = sqlite3.connect(self.temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT ip FROM blacklist_ip WHERE is_active = 1")
        db_ips = set(row[0] for row in cursor.fetchall())
        conn.close()
        
        # API와 데이터베이스 결과가 일치해야 함
        if api_ips != db_ips:
            print(f"Data integrity issue: API={len(api_ips)}, DB={len(db_ips)}")
            print(f"API-only: {api_ips - db_ips}")
            print(f"DB-only: {db_ips - api_ips}")
            return False
            
        return True
    
    def test_error_handling_edge_cases(self):
        """에러 처리 엣지 케이스 테스트"""
        test_cases = [
            # 존재하지 않는 엔드포인트
            ("/api/nonexistent", 404),
            # 잘못된 HTTP 메소드
            # ("/api/blacklist/active", 405, "POST"),  # POST로 GET 엔드포인트 호출
            # 잘못된 파라미터
            ("/api/search/invalid-ip-format", [400, 404]),  # 잘못된 IP 형식
        ]
        
        for test_case in test_cases:
            endpoint = test_case[0]
            expected_codes = test_case[1] if isinstance(test_case[1], list) else [test_case[1]]
            method = test_case[2] if len(test_case) > 2 else "GET"
            
            try:
                if method == "GET":
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=2)
                elif method == "POST":
                    response = requests.post(f"{self.base_url}{endpoint}", timeout=2)
                
                if response.status_code not in expected_codes:
                    print(f"Unexpected status code for {endpoint}: {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"Error testing {endpoint}: {e}")
                return False
        
        return True
    
    def test_response_time_consistency(self):
        """응답 시간 일관성 테스트"""
        endpoint = "/health"
        response_times = []
        
        # 50번 요청하여 응답 시간 측정
        for _ in range(50):
            start_time = time.time()
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=2)
                if response.status_code == 200:
                    response_times.append(time.time() - start_time)
            except:
                pass
        
        if len(response_times) < 45:  # 90% 이상 성공
            return False
            
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        min_time = min(response_times)
        
        print(f"📊 Response times - Avg: {avg_time:.3f}s, Min: {min_time:.3f}s, Max: {max_time:.3f}s")
        
        # 평균 응답 시간이 100ms 이하, 최대 응답 시간이 1초 이하
        return avg_time < 0.1 and max_time < 1.0
    
    def run_all_tests(self):
        """모든 고급 통합 테스트 실행"""
        print("🧪 Blacklist Management System - Advanced Integration Test Suite")
        print(f"📁 Running from: {project_root}")
        print(f"🐍 Python: {sys.version}")
        print(f"⏰ Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # 환경 설정
        self.setup_test_environment()
        
        # 애플리케이션 시작
        if not self.start_application():
            return False
            
        try:
            # 고급 테스트 실행
            self.run_test("Database CRUD Operations", self.test_database_crud_operations)
            self.run_test("Database Concurrent Access", self.test_database_concurrent_access)
            self.run_test("API Response Consistency", self.test_api_response_consistency)
            self.run_test("API Concurrent Load", self.test_api_concurrent_load)
            self.run_test("Memory Usage Stability", self.test_memory_usage_stability)
            self.run_test("Data Integrity After Operations", self.test_data_integrity_after_operations)
            self.run_test("Error Handling Edge Cases", self.test_error_handling_edge_cases)
            self.run_test("Response Time Consistency", self.test_response_time_consistency)
            
        finally:
            # 정리
            self.stop_application()
            self.cleanup_test_environment()
        
        # 결과 요약
        self.print_summary()
        
        # 성공 여부 반환
        return all(result[1] for result in self.test_results)
    
    def print_summary(self):
        """테스트 결과 요약 출력 (향상된 분석)"""
        print("\n" + "=" * 60)
        print("📊 ADVANCED TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result[1])
        total = len(self.test_results)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        # 실행 시간 통계
        durations = [result[3] for result in self.test_results if len(result) > 3]
        total_time = sum(durations)
        avg_time = total_time / len(durations) if durations else 0
        max_time = max(durations) if durations else 0
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Total Time: {total_time:.3f}s")
        print(f"Average Time: {avg_time:.3f}s")
        print(f"Slowest Test: {max_time:.3f}s")
        
        if total - passed > 0:
            print("\n❌ Failed Tests:")
            for name, success, error, duration in self.test_results:
                if not success:
                    print(f"  - {name} ({duration:.3f}s): {error}")
        
        # 성능 분석
        slow_tests = [(name, duration) for name, success, error, duration in self.test_results 
                     if len(self.test_results[0]) > 3 and duration > 1.0]
        if slow_tests:
            print(f"\n⚠️  Slow Tests (>1.0s):")
            for name, duration in slow_tests:
                print(f"  - {name}: {duration:.3f}s")
        
        if success_rate == 100:
            print("\n🎉 All advanced tests passed!")
        elif success_rate >= 80:
            print(f"\n⚠️  Most tests passed ({success_rate:.1f}%)")
        else:
            print(f"\n❌ Many tests failed ({success_rate:.1f}%)")

def main():
    """메인 함수"""
    suite = AdvancedIntegrationTestSuite()
    success = suite.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())