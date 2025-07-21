#!/usr/bin/env python3
"""
최종 시스템 안정성 검증 스크립트
"""
import subprocess
import json
import sys
from datetime import datetime

def check_system_stability():
    """최종 시스템 안정성 검증"""
    print("🔍 최종 시스템 안정성 검증 시작...")
    print(f"검증 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_checks = []
    
    # 1. 리소스 사용량 확인
    print("\n1️⃣ 리소스 사용량 확인...")
    try:
        result = subprocess.run(['kubectl', 'top', 'pods', '-n', 'blacklist'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:  # 헤더 제외
                for line in lines[1:]:
                    if 'blacklist' in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            cpu = parts[1]
                            memory = parts[2]
                            print(f"   CPU: {cpu}, Memory: {memory}")
                            all_checks.append("✅ 리소스 사용량 정상")
                        break
            else:
                all_checks.append("⚠️ 리소스 정보 없음")
        else:
            all_checks.append("❌ 리소스 확인 실패")
    except Exception as e:
        print(f"   오류: {e}")
        all_checks.append("❌ 리소스 확인 중 오류")
    
    # 2. Pod 상태 확인
    print("\n2️⃣ Pod 상태 확인...")
    try:
        result = subprocess.run(['kubectl', 'get', 'pods', '-n', 'blacklist', '-o', 'json'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            pods_data = json.loads(result.stdout)
            running_pods = 0
            total_pods = len(pods_data['items'])
            
            for pod in pods_data['items']:
                name = pod['metadata']['name']
                status = pod['status']['phase']
                ready = "0/0"
                
                if 'containerStatuses' in pod['status']:
                    ready_count = sum(1 for c in pod['status']['containerStatuses'] if c.get('ready', False))
                    total_count = len(pod['status']['containerStatuses'])
                    ready = f"{ready_count}/{total_count}"
                
                print(f"   {name}: {status} ({ready})")
                if status == 'Running':
                    running_pods += 1
            
            if running_pods == total_pods and running_pods > 0:
                all_checks.append("✅ 모든 Pod 정상 실행 중")
            else:
                all_checks.append(f"⚠️ Pod 상태: {running_pods}/{total_pods} 실행 중")
        else:
            all_checks.append("❌ Pod 상태 확인 실패")
    except Exception as e:
        print(f"   오류: {e}")
        all_checks.append("❌ Pod 상태 확인 중 오류")
    
    # 3. Service 상태 확인
    print("\n3️⃣ Service 상태 확인...")
    try:
        result = subprocess.run(['kubectl', 'get', 'svc', '-n', 'blacklist', '-o', 'json'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            svc_data = json.loads(result.stdout)
            
            for svc in svc_data['items']:
                name = svc['metadata']['name']
                svc_type = svc['spec'].get('type', 'ClusterIP')
                ports = svc['spec'].get('ports', [])
                
                # 포트 정보 안전하게 포맷팅
                port_list = []
                for p in ports:
                    port = p.get('port', '?')
                    protocol = p.get('protocol', '?')
                    port_list.append(f"{port}/{protocol}")
                
                ports_str = ', '.join(port_list)
                print(f"   {name}: {svc_type}, Ports: {ports_str}")
            
            all_checks.append("✅ Service 설정 정상")
        else:
            all_checks.append("❌ Service 상태 확인 실패")
    except Exception as e:
        print(f"   오류: {e}")
        all_checks.append("❌ Service 상태 확인 중 오류")
    
    # 4. ArgoCD 애플리케이션 상태 확인
    print("\n4️⃣ ArgoCD 애플리케이션 상태 확인...")
    try:
        result = subprocess.run(['argocd', 'app', 'get', 'blacklist', '--grpc-web'], 
                              capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            output = result.stdout
            if 'Health Status:' in output:
                for line in output.split('\n'):
                    if 'Health Status:' in line:
                        health_status = line.split(':')[1].strip()
                        print(f"   Health Status: {health_status}")
                        if 'Healthy' in health_status:
                            all_checks.append("✅ ArgoCD 애플리케이션 정상")
                        else:
                            all_checks.append(f"⚠️ ArgoCD 상태: {health_status}")
                        break
            else:
                all_checks.append("⚠️ ArgoCD 상태 정보 없음")
        else:
            all_checks.append("❌ ArgoCD 상태 확인 실패")
    except Exception as e:
        print(f"   오류: {e}")
        all_checks.append("❌ ArgoCD 상태 확인 중 오류")
    
    # 5. API 엔드포인트 확인
    print("\n5️⃣ API 엔드포인트 확인...")
    try:
        # kubectl port-forward를 백그라운드에서 실행
        port_forward = subprocess.Popen(['kubectl', 'port-forward', '-n', 'blacklist', 
                                       'deployment/blacklist', '8543:8541'], 
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 잠시 대기
        import time
        time.sleep(3)
        
        # API 테스트
        import urllib.request
        import urllib.error
        
        endpoints = ['/health', '/api/stats', '/api/collection/status']
        working_endpoints = 0
        
        for endpoint in endpoints:
            try:
                url = f'http://localhost:8543{endpoint}'
                with urllib.request.urlopen(url, timeout=5) as response:
                    if response.status == 200:
                        print(f"   ✅ {endpoint}: OK")
                        working_endpoints += 1
                    else:
                        print(f"   ❌ {endpoint}: {response.status}")
            except Exception as e:
                print(f"   ❌ {endpoint}: {str(e)}")
        
        # port-forward 종료
        port_forward.terminate()
        port_forward.wait()
        
        if working_endpoints == len(endpoints):
            all_checks.append("✅ 모든 API 엔드포인트 정상")
        else:
            all_checks.append(f"⚠️ API 엔드포인트: {working_endpoints}/{len(endpoints)} 정상")
            
    except Exception as e:
        print(f"   오류: {e}")
        all_checks.append("❌ API 엔드포인트 확인 중 오류")
    
    # 최종 결과 요약
    print("\n" + "="*60)
    print("🏁 최종 시스템 안정성 검증 결과")
    print("="*60)
    
    success_count = sum(1 for check in all_checks if check.startswith("✅"))
    warning_count = sum(1 for check in all_checks if check.startswith("⚠️"))
    error_count = sum(1 for check in all_checks if check.startswith("❌"))
    
    for check in all_checks:
        print(f"   {check}")
    
    print(f"\n📊 검증 요약:")
    print(f"   ✅ 성공: {success_count}")
    print(f"   ⚠️ 경고: {warning_count}")
    print(f"   ❌ 오류: {error_count}")
    
    if error_count == 0 and warning_count <= 1:
        print(f"\n🎉 시스템이 안정적으로 운영되고 있습니다!")
        return True
    elif error_count == 0:
        print(f"\n✅ 시스템이 전반적으로 안정적입니다. (경고 {warning_count}개)")
        return True
    else:
        print(f"\n⚠️ 시스템에 {error_count}개의 문제가 발견되었습니다.")
        return False

if __name__ == "__main__":
    success = check_system_stability()
    sys.exit(0 if success else 1)