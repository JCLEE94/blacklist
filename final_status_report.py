#!/usr/bin/env python3
"""
최종 시스템 상태 보고서
"""
import os
import requests
import subprocess
from datetime import datetime

def check_docker_status():
    """Docker 컨테이너 상태 확인"""
    print("\n🐳 Docker 컨테이너 상태")
    print("-" * 50)
    
    result = subprocess.run(['docker', 'ps', '--filter', 'name=blacklist'], 
                          capture_output=True, text=True)
    if 'blacklist-prod' in result.stdout:
        print("✅ 컨테이너 실행 중: blacklist-prod")
        
        # 상세 정보
        result = subprocess.run(['docker', 'inspect', 'blacklist-prod'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            import json
            info = json.loads(result.stdout)[0]
            print(f"   - 이미지: {info['Config']['Image']}")
            print(f"   - 포트: {info['NetworkSettings']['Ports']}")
            print(f"   - 상태: {info['State']['Status']}")
    else:
        print("❌ 컨테이너가 실행되지 않음")

def check_api_health():
    """API 헬스 체크"""
    print("\n🔍 API 상태 확인")
    print("-" * 50)
    
    try:
        response = requests.get('http://192.168.50.215:2541/health', timeout=5)
        print(f"📊 헬스 체크 응답: {response.status_code}")
        if response.status_code == 503:
            print("⚠️  애플리케이션 초기화 오류 발생")
            print(f"   오류: {response.json().get('message', 'Unknown error')}")
        elif response.status_code == 200:
            print("✅ 애플리케이션 정상 작동")
    except Exception as e:
        print(f"❌ API 접속 실패: {e}")

def check_collection_status():
    """수집 기능 상태"""
    print("\n📥 수집 기능 상태")
    print("-" * 50)
    
    # REGTECH
    print("1. REGTECH 수집기")
    print("   - 상태: ❌ 인증 실패 (외부 서버 정책 변경)")
    print("   - 오류: 로그인 후 error=true 리다이렉트")
    
    # SECUDIUM  
    print("\n2. SECUDIUM 수집기")
    print("   - 상태: ❌ 중복 로그인")
    print("   - 오류: 동일 ID로 이미 로그인된 사용자 존재")

def check_data_files():
    """데이터 파일 확인"""
    print("\n📁 데이터 파일 상태")
    print("-" * 50)
    
    data_dirs = ['data/regtech', 'data/secudium', 'instance']
    
    for dir_path in data_dirs:
        if os.path.exists(dir_path):
            files = os.listdir(dir_path)
            print(f"✅ {dir_path}: {len(files)}개 파일")
            if files:
                for f in files[:3]:  # 처음 3개만 표시
                    print(f"   - {f}")
        else:
            print(f"❌ {dir_path}: 디렉토리 없음")

def generate_summary():
    """최종 요약"""
    print("\n" + "=" * 60)
    print("📊 최종 시스템 상태 요약")
    print("=" * 60)
    
    issues = [
        {
            "component": "API 라우팅",
            "status": "❌ 실패",
            "issue": "routes_unified.py line 61 오류로 인한 초기화 실패",
            "impact": "모든 API 엔드포인트 404 응답"
        },
        {
            "component": "REGTECH 수집",
            "status": "❌ 실패",
            "issue": "외부 서버의 인증 정책 변경",
            "impact": "REGTECH 데이터 수집 불가"
        },
        {
            "component": "SECUDIUM 수집",
            "status": "❌ 실패", 
            "issue": "중복 로그인 감지",
            "impact": "SECUDIUM 데이터 수집 불가"
        },
        {
            "component": "Docker 컨테이너",
            "status": "✅ 정상",
            "issue": "없음",
            "impact": "컨테이너는 정상 실행 중"
        }
    ]
    
    print("\n주요 이슈:")
    for i, issue in enumerate(issues, 1):
        print(f"\n{i}. {issue['component']}")
        print(f"   상태: {issue['status']}")
        print(f"   문제: {issue['issue']}")
        print(f"   영향: {issue['impact']}")
    
    print("\n권장 조치:")
    print("1. routes_unified.py 오류 수정 필요")
    print("2. REGTECH/SECUDIUM 대체 수집 방법 검토")
    print("3. 테스트 데이터로 시스템 검증 진행")

def main():
    print("🚀 블랙리스트 시스템 최종 상태 보고서")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    check_docker_status()
    check_api_health()
    check_collection_status()
    check_data_files()
    generate_summary()

if __name__ == '__main__':
    main()