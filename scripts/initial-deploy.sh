#!/bin/bash

echo "🚀 Blacklist Management System - 최초 배포 스크립트"
echo "=================================================="
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 함수 정의
print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    print_step "사전 요구사항 확인 중..."
    
    # kubectl 확인
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl이 설치되지 않았습니다."
        exit 1
    fi
    
    # argocd CLI 확인
    if ! command -v argocd &> /dev/null; then
        print_warning "ArgoCD CLI가 설치되지 않았습니다. 설치를 진행합니다..."
        
        # ArgoCD CLI 설치
        curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
        sudo install -m 555 argocd-linux-amd64 /usr/local/bin/argocd
        rm argocd-linux-amd64
        
        if command -v argocd &> /dev/null; then
            print_success "ArgoCD CLI 설치 완료"
        else
            print_error "ArgoCD CLI 설치 실패"
            exit 1
        fi
    fi
    
    # Kubernetes 클러스터 연결 확인
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Kubernetes 클러스터에 연결할 수 없습니다."
        exit 1
    fi
    
    print_success "사전 요구사항 확인 완료"
}

setup_namespace() {
    print_step "네임스페이스 설정 중..."
    
    # blacklist 네임스페이스 생성
    kubectl create namespace blacklist --dry-run=client -o yaml | kubectl apply -f -
    
    print_success "네임스페이스 설정 완료"
}

setup_secrets() {
    print_step "시크릿 설정 중..."
    
    # Docker Registry 시크릿 생성 (사용자 입력 필요)
    echo ""
    echo "Docker Registry 인증 정보를 입력해주세요:"
    read -p "Registry Username: " REGISTRY_USERNAME
    read -s -p "Registry Password: " REGISTRY_PASSWORD
    echo ""
    
    kubectl create secret docker-registry regcred \
        --docker-server=registry.jclee.me \
        --docker-username="$REGISTRY_USERNAME" \
        --docker-password="$REGISTRY_PASSWORD" \
        -n blacklist \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # 애플리케이션 시크릿 생성
    echo ""
    echo "애플리케이션 인증 정보를 입력해주세요:"
    read -p "REGTECH Username: " REGTECH_USERNAME
    read -s -p "REGTECH Password: " REGTECH_PASSWORD
    echo ""
    read -p "SECUDIUM Username: " SECUDIUM_USERNAME
    read -s -p "SECUDIUM Password: " SECUDIUM_PASSWORD
    echo ""
    read -s -p "Flask Secret Key: " SECRET_KEY
    echo ""
    
    kubectl create secret generic blacklist-secret \
        --from-literal=REGTECH_USERNAME="$REGTECH_USERNAME" \
        --from-literal=REGTECH_PASSWORD="$REGTECH_PASSWORD" \
        --from-literal=SECUDIUM_USERNAME="$SECUDIUM_USERNAME" \
        --from-literal=SECUDIUM_PASSWORD="$SECUDIUM_PASSWORD" \
        --from-literal=SECRET_KEY="$SECRET_KEY" \
        -n blacklist \
        --dry-run=client -o yaml | kubectl apply -f -
    
    print_success "시크릿 설정 완료"
}

deploy_application() {
    print_step "애플리케이션 배포 중..."
    
    # Kubernetes 매니페스트 적용
    kubectl apply -k k8s/
    
    print_success "애플리케이션 매니페스트 적용 완료"
}

setup_argocd() {
    print_step "ArgoCD 설정 중..."
    
    # ArgoCD 서버 연결 정보
    ARGOCD_SERVER="argo.jclee.me"
    
    echo ""
    echo "ArgoCD 로그인 정보를 입력해주세요:"
    read -p "Username (기본값: admin): " ARGOCD_USERNAME
    ARGOCD_USERNAME=${ARGOCD_USERNAME:-admin}
    read -s -p "Password: " ARGOCD_PASSWORD
    echo ""
    
    # ArgoCD 로그인
    argocd login $ARGOCD_SERVER --username $ARGOCD_USERNAME --password $ARGOCD_PASSWORD --grpc-web --insecure
    
    # ArgoCD 애플리케이션 생성
    if argocd app get blacklist --grpc-web &> /dev/null; then
        print_warning "ArgoCD 애플리케이션이 이미 존재합니다. 업데이트를 진행합니다."
        kubectl apply -f k8s/argocd-app-clean.yaml
    else
        print_step "ArgoCD 애플리케이션 생성 중..."
        kubectl apply -f k8s/argocd-app-clean.yaml
    fi
    
    # 애플리케이션 동기화
    argocd app sync blacklist --grpc-web
    
    print_success "ArgoCD 설정 완료"
}

verify_deployment() {
    print_step "배포 검증 중..."
    
    # Pod 상태 확인
    echo "Pod 상태 확인 중..."
    kubectl get pods -n blacklist
    
    # 배포 상태 확인
    echo ""
    echo "배포 상태 확인 중..."
    kubectl rollout status deployment/blacklist -n blacklist --timeout=300s
    
    # 서비스 상태 확인
    echo ""
    echo "서비스 상태 확인 중..."
    kubectl get svc -n blacklist
    
    # ArgoCD 애플리케이션 상태 확인
    echo ""
    echo "ArgoCD 애플리케이션 상태 확인 중..."
    argocd app get blacklist --grpc-web | grep -E "(Health Status|Sync Status)"
    
    print_success "배포 검증 완료"
}

show_access_info() {
    echo ""
    echo "🎉 배포가 완료되었습니다!"
    echo "=========================="
    echo ""
    echo "📊 접속 정보:"
    echo "- ArgoCD 대시보드: https://argo.jclee.me/applications/blacklist"
    echo "- 프로덕션 서비스: https://blacklist.jclee.me"
    echo ""
    
    # NodePort 정보 표시
    NODE_PORT=$(kubectl get svc blacklist -n blacklist -o jsonpath='{.spec.ports[0].nodePort}')
    if [ ! -z "$NODE_PORT" ]; then
        echo "- NodePort 접속: http://<node-ip>:$NODE_PORT"
    fi
    
    echo ""
    echo "🔍 상태 확인 명령어:"
    echo "kubectl get pods -n blacklist"
    echo "argocd app get blacklist --grpc-web"
    echo ""
    echo "📚 자세한 사용법은 README.md를 참고하세요."
}

# 메인 실행 흐름
main() {
    echo "이 스크립트는 Blacklist Management System을 처음 배포할 때 사용합니다."
    echo ""
    read -p "계속하시겠습니까? (y/N): " confirm
    
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        echo "배포를 취소했습니다."
        exit 0
    fi
    
    check_prerequisites
    setup_namespace
    setup_secrets
    deploy_application
    setup_argocd
    verify_deployment
    show_access_info
}

# 스크립트 실행
main "$@"