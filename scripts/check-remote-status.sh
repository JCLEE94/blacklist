#!/bin/bash

echo "🔍 원격 서버 상태 확인"
echo "===================="
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 서버 정보
REMOTE_HOST="192.168.50.110"
REMOTE_USER="jclee"

print_section() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

# SSH 연결 확인
check_ssh() {
    print_section "SSH 연결 확인"
    
    if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "echo 'SSH 연결 성공'" 2>/dev/null; then
        print_success "SSH 연결 정상"
    else
        print_error "SSH 연결 실패"
        return 1
    fi
}

# 시스템 정보
check_system_info() {
    print_section "시스템 정보"
    
    ssh "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
echo "호스트명: $(hostname)"
echo "OS: $(lsb_release -d 2>/dev/null | cut -f2 || cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "업타임: $(uptime -p)"
echo "메모리: $(free -h | grep Mem | awk '{print $3"/"$2}')"
echo "디스크: $(df -h / | tail -1 | awk '{print $3"/"$2" ("$5" 사용)"}')"
EOF
}

# 설치된 도구 확인
check_tools() {
    print_section "설치된 도구 확인"
    
    ssh "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
echo "Docker: $(docker --version 2>/dev/null || echo '❌ 설치되지 않음')"
echo "kubectl: $(kubectl version --client --short 2>/dev/null || echo '❌ 설치되지 않음')"
echo "ArgoCD CLI: $(argocd version --client --short 2>/dev/null || echo '❌ 설치되지 않음')"
echo "Git: $(git --version 2>/dev/null || echo '❌ 설치되지 않음')"
EOF
}

# Kubernetes 클러스터 연결 확인
check_k8s_connection() {
    print_section "Kubernetes 연결 상태"
    
    ssh "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
if kubectl cluster-info &> /dev/null; then
    echo "✅ Kubernetes 클러스터 연결 성공"
    echo "클러스터 정보:"
    kubectl cluster-info | head -2
    echo ""
    echo "노드 상태:"
    kubectl get nodes --no-headers | while read line; do
        echo "  $line"
    done
else
    echo "❌ Kubernetes 클러스터 연결 실패"
fi
EOF
}

# 블랙리스트 애플리케이션 상태
check_blacklist_app() {
    print_section "Blacklist 애플리케이션 상태"
    
    ssh "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
# 네임스페이스 확인
if kubectl get namespace blacklist &> /dev/null; then
    echo "✅ blacklist 네임스페이스 존재"
else
    echo "❌ blacklist 네임스페이스 없음"
    exit 0
fi

# Pod 상태 확인
echo ""
echo "Pod 상태:"
kubectl get pods -n blacklist --no-headers 2>/dev/null | while read line; do
    echo "  $line"
done

# 서비스 상태 확인
echo ""
echo "서비스 상태:"
kubectl get svc -n blacklist --no-headers 2>/dev/null | while read line; do
    echo "  $line"
done

# 배포 상태 확인
echo ""
echo "배포 상태:"
if kubectl get deployment blacklist -n blacklist &> /dev/null; then
    ready=$(kubectl get deployment blacklist -n blacklist -o jsonpath='{.status.readyReplicas}')
    desired=$(kubectl get deployment blacklist -n blacklist -o jsonpath='{.spec.replicas}')
    echo "  Ready: $ready/$desired"
    
    if [ "$ready" = "$desired" ] && [ "$ready" != "" ]; then
        echo "  ✅ 배포 정상"
    else
        echo "  ⚠️ 배포 불완전"
    fi
else
    echo "  ❌ 배포 없음"
fi
EOF
}

# ArgoCD 애플리케이션 상태
check_argocd_status() {
    print_section "ArgoCD 애플리케이션 상태"
    
    ssh "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
if argocd app get blacklist --grpc-web &> /dev/null; then
    echo "✅ ArgoCD 애플리케이션 연결 성공"
    echo ""
    argocd app get blacklist --grpc-web | grep -E "(Health Status|Sync Status|Last Sync)" || echo "상태 정보 없음"
else
    echo "❌ ArgoCD 애플리케이션 연결 실패"
    echo "ArgoCD 서버 연결을 확인하세요:"
    echo "  argocd login argo.jclee.me --username admin --password <password> --grpc-web"
fi
EOF
}

# 네트워크 연결성 확인
check_network() {
    print_section "네트워크 연결성 확인"
    
    ssh "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
# NodePort 서비스 확인
if kubectl get svc blacklist -n blacklist &> /dev/null; then
    nodeport=$(kubectl get svc blacklist -n blacklist -o jsonpath='{.spec.ports[0].nodePort}')
    if [ ! -z "$nodeport" ]; then
        echo "NodePort: $nodeport"
        
        # 로컬 접속 테스트
        if curl -s --connect-timeout 5 "http://localhost:$nodeport/health" > /dev/null; then
            echo "✅ 로컬 NodePort 접속 성공"
        else
            echo "❌ 로컬 NodePort 접속 실패"
        fi
    fi
fi

# 외부 연결 테스트
echo ""
echo "외부 연결 테스트:"
if ping -c 1 8.8.8.8 &> /dev/null; then
    echo "✅ 인터넷 연결 정상"
else
    echo "❌ 인터넷 연결 실패"
fi

if nslookup registry.jclee.me &> /dev/null; then
    echo "✅ Docker Registry DNS 해석 성공"
else
    echo "❌ Docker Registry DNS 해석 실패"
fi
EOF
}

# 로그 확인
check_logs() {
    print_section "최근 로그 확인"
    
    ssh "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
if kubectl get pods -n blacklist --no-headers 2>/dev/null | grep -q "blacklist"; then
    echo "최근 애플리케이션 로그 (마지막 10줄):"
    kubectl logs -n blacklist deployment/blacklist --tail=10 2>/dev/null || echo "로그 없음"
else
    echo "실행 중인 Pod가 없습니다."
fi
EOF
}

# 리소스 사용량
check_resources() {
    print_section "리소스 사용량"
    
    ssh "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
# 전체 노드 리소스
echo "노드 리소스 사용량:"
kubectl top nodes 2>/dev/null || echo "메트릭 서버 없음"

echo ""
# blacklist 네임스페이스 Pod 리소스
echo "blacklist Pod 리소스 사용량:"
kubectl top pods -n blacklist 2>/dev/null || echo "메트릭 서버 없음"
EOF
}

# 문제 해결 가이드
show_troubleshooting() {
    print_section "문제 해결 가이드"
    
    cat << 'EOF'
🔧 일반적인 문제 해결:

1. SSH 연결 실패:
   - 네트워크 연결 확인: ping 192.168.50.110
   - SSH 키 재설정: ./scripts/setup/remote-server-setup.sh

2. Kubernetes 연결 실패:
   - kubeconfig 파일 확인: ssh jclee@192.168.50.110 'ls -la ~/.kube/'
   - 클러스터 상태 확인: kubectl get nodes

3. Pod 실행 실패:
   - 상세 로그: ssh jclee@192.168.50.110 'kubectl describe pod -n blacklist'
   - 이벤트 확인: ssh jclee@192.168.50.110 'kubectl get events -n blacklist'

4. ArgoCD 연결 실패:
   - 로그인 재시도: ssh jclee@192.168.50.110 'argocd login argo.jclee.me --grpc-web'
   - 애플리케이션 동기화: ssh jclee@192.168.50.110 'argocd app sync blacklist --grpc-web'

5. 서비스 접속 실패:
   - 방화벽 확인: ssh jclee@192.168.50.110 'sudo ufw status'
   - 포트 리스닝 확인: ssh jclee@192.168.50.110 'netstat -tlnp | grep :32542'
EOF
}

# 메인 실행
main() {
    echo "원격 서버 ($REMOTE_HOST) 상태를 확인합니다."
    echo ""
    
    if ! check_ssh; then
        echo ""
        echo "SSH 연결이 실패했습니다. 먼저 다음 명령어를 실행하세요:"
        echo "./scripts/setup/remote-server-setup.sh"
        exit 1
    fi
    
    echo ""
    check_system_info
    echo ""
    check_tools
    echo ""
    check_k8s_connection
    echo ""
    check_blacklist_app
    echo ""
    check_argocd_status
    echo ""
    check_network
    echo ""
    check_logs
    echo ""
    check_resources
    echo ""
    show_troubleshooting
}

main "$@"