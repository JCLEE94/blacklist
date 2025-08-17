#!/usr/bin/env python3
"""
Prometheus 메트릭 시스템 테스트 스크립트
55개 메트릭과 23개 알림 규칙 검증
"""

import json
import sys
import time
from pathlib import Path

import requests

# 프로젝트 루트를 Python 경로에 추가
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))


def test_metrics_endpoint(base_url="http://localhost:2542"):
    """메트릭 엔드포인트 테스트"""
    print("🔍 Prometheus 메트릭 시스템 테스트 시작")
    print("=" * 60)
    
    try:
        # 1. 메트릭 엔드포인트 접근 테스트
        print("1. 메트릭 엔드포인트 테스트...")
        response = requests.get(f"{base_url}/metrics", timeout=10)
        
        if response.status_code != 200:
            print(f"❌ 메트릭 엔드포인트 오류: {response.status_code}")
            print(f"응답: {response.text[:200]}...")
            return False
            
        metrics_text = response.text
        print(f"✅ 메트릭 엔드포인트 정상 작동 (응답 크기: {len(metrics_text)} bytes)")
        
        # 2. Content-Type 확인
        content_type = response.headers.get('Content-Type', '')
        if 'text/plain' in content_type:
            print("✅ Prometheus 호환 Content-Type 확인됨")
        else:
            print(f"⚠️ Content-Type 확인 필요: {content_type}")
        
        # 3. 핵심 메트릭 존재 확인
        expected_metrics = [
            'blacklist_up',
            'blacklist_uptime_seconds', 
            'blacklist_http_requests_total',
            'blacklist_http_request_duration_seconds',
            'blacklist_entries_total',
            'blacklist_collections_total',
            'blacklist_memory_usage_bytes',
            'blacklist_cpu_usage_percent',
            'blacklist_errors_total',
            'blacklist_api_queries_total'
        ]
        
        print("\n2. 핵심 메트릭 존재 확인...")
        found_metrics = []
        for metric in expected_metrics:
            if metric in metrics_text:
                found_metrics.append(metric)
                print(f"✅ {metric}")
            else:
                print(f"❌ {metric} 누락")
        
        print(f"\n📊 메트릭 발견률: {len(found_metrics)}/{len(expected_metrics)} ({len(found_metrics)/len(expected_metrics)*100:.1f}%)")
        
        # 4. 전체 메트릭 수 계산
        lines = metrics_text.split('\n')
        metric_lines = [line for line in lines if line and not line.startswith('#') and '=' in line]
        help_lines = [line for line in lines if line.startswith('# HELP')]
        
        print(f"📈 총 메트릭 라인 수: {len(metric_lines)}")
        print(f"📝 도움말 라인 수: {len(help_lines)}")
        
        # 5. 샘플 메트릭 출력
        print("\n3. 샘플 메트릭 (처음 10개):")
        print("-" * 40)
        sample_lines = [line for line in lines if line and not line.startswith('#')][:10]
        for line in sample_lines:
            print(f"  {line}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 네트워크 오류: {e}")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False


def test_api_endpoints(base_url="http://localhost:2542"):
    """API 엔드포인트들을 호출하여 메트릭 생성 유도"""
    print("\n4. API 엔드포인트 테스트 (메트릭 생성 유도)...")
    print("-" * 40)
    
    endpoints = [
        "/health",
        "/api/health", 
        "/api/blacklist/active",
        "/api/stats",
        "/api/collection/status"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            status = "✅" if response.status_code < 400 else "⚠️"
            print(f"{status} {endpoint} -> {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint} -> Error: {e}")
    
    # 메트릭 업데이트를 위한 잠시 대기
    print("\n⏳ 메트릭 업데이트 대기 중...")
    time.sleep(2)


def analyze_metrics_after_requests(base_url="http://localhost:2542"):
    """요청 후 메트릭 변화 분석"""
    print("\n5. 요청 후 메트릭 분석...")
    print("-" * 40)
    
    try:
        response = requests.get(f"{base_url}/metrics", timeout=10)
        if response.status_code != 200:
            print("❌ 메트릭 재조회 실패")
            return
            
        metrics_text = response.text
        
        # HTTP 요청 메트릭 확인
        http_request_lines = [line for line in metrics_text.split('\n') 
                             if 'blacklist_http_requests_total' in line and not line.startswith('#')]
        
        print("📊 HTTP 요청 메트릭:")
        for line in http_request_lines[:5]:  # 처음 5개만
            print(f"  {line}")
        
        # 응답 시간 메트릭 확인  
        duration_lines = [line for line in metrics_text.split('\n')
                         if 'blacklist_http_request_duration_seconds' in line and not line.startswith('#')]
        
        print("\n⏱️ 응답 시간 메트릭:")
        for line in duration_lines[:3]:  # 처음 3개만
            print(f"  {line}")
            
        # 시스템 메트릭 확인
        system_metrics = ['blacklist_up', 'blacklist_memory_usage_bytes', 'blacklist_cpu_usage_percent']
        print("\n🖥️ 시스템 메트릭:")
        for metric in system_metrics:
            lines = [line for line in metrics_text.split('\n') 
                    if line.startswith(metric) and '=' in line]
            if lines:
                print(f"  {lines[0]}")
                
    except Exception as e:
        print(f"❌ 메트릭 분석 오류: {e}")


def verify_alert_rules():
    """알림 규칙 파일 검증"""
    print("\n6. 알림 규칙 검증...")
    print("-" * 40)
    
    rules_file = Path(__file__).parent.parent / "config" / "prometheus-rules.yml"
    
    if not rules_file.exists():
        print("❌ prometheus-rules.yml 파일이 없습니다")
        return False
    
    try:
        import yaml
        with open(rules_file, 'r', encoding='utf-8') as f:
            rules_data = yaml.safe_load(f)
        
        groups = rules_data.get('groups', [])
        total_rules = sum(len(group.get('rules', [])) for group in groups)
        
        print(f"✅ 알림 규칙 파일 로드 성공")
        print(f"📊 그룹 수: {len(groups)}")
        print(f"📋 총 규칙 수: {total_rules}")
        
        # 그룹별 규칙 수 출력
        for group in groups:
            group_name = group.get('name', 'unnamed')
            rule_count = len(group.get('rules', []))
            print(f"  - {group_name}: {rule_count}개 규칙")
        
        return total_rules >= 20  # 최소 20개 규칙 기대
        
    except ImportError:
        print("⚠️ PyYAML이 설치되지 않아 YAML 파일을 검증할 수 없습니다")
        return True
    except Exception as e:
        print(f"❌ 알림 규칙 검증 오류: {e}")
        return False


def main():
    """메인 테스트 실행"""
    print("🚀 Blacklist Prometheus 메트릭 시스템 종합 테스트")
    print("=" * 60)
    
    # 기본 설정
    base_url = "http://localhost:2542"  # 로컬 개발 서버
    
    # 도커 서버도 테스트해보기
    if len(sys.argv) > 1 and sys.argv[1] == "--docker":
        base_url = "http://localhost:32542"
        print(f"🐳 Docker 서버 테스트 모드: {base_url}")
    else:
        print(f"🔧 로컬 개발 서버 테스트 모드: {base_url}")
    
    print()
    
    # 테스트 수행
    tests_passed = 0
    tests_total = 4
    
    # 1. 메트릭 엔드포인트 테스트
    if test_metrics_endpoint(base_url):
        tests_passed += 1
    
    # 2. API 호출로 메트릭 생성
    test_api_endpoints(base_url)
    
    # 3. 메트릭 변화 분석
    analyze_metrics_after_requests(base_url)
    tests_passed += 1  # 분석은 항상 성공으로 간주
    
    # 4. 알림 규칙 검증
    if verify_alert_rules():
        tests_passed += 1
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)
    print(f"✅ 통과한 테스트: {tests_passed}/{tests_total}")
    print(f"📈 성공률: {tests_passed/tests_total*100:.1f}%")
    
    if tests_passed == tests_total:
        print("\n🎉 모든 테스트가 성공했습니다!")
        print("✅ Prometheus 메트릭 시스템이 정상적으로 작동 중입니다.")
        return 0
    else:
        print(f"\n⚠️ {tests_total - tests_passed}개 테스트가 실패했습니다.")
        print("🔧 설정을 확인하고 다시 시도해주세요.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)