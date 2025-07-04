#!/bin/bash
set -e

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 함수: 로그 출력
log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# ArgoCD 서버 정보
ARGOCD_SERVER="argo.jclee.me"
ARGOCD_NAMESPACE="argocd"

echo "🚀 ArgoCD 환경 설정"
echo "=================="

# 1. ArgoCD CLI 확인
if ! command -v argocd &> /dev/null; then
    error "ArgoCD CLI가 설치되어 있지 않습니다"
    echo "설치: curl -sSL -o /tmp/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64"
    exit 1
fi

# 2. Kubernetes 연결 확인
if ! kubectl cluster-info &> /dev/null; then
    error "Kubernetes 클러스터에 연결할 수 없습니다"
    exit 1
fi

# 3. ArgoCD 네임스페이스 확인
if ! kubectl get namespace $ARGOCD_NAMESPACE &> /dev/null; then
    error "ArgoCD 네임스페이스가 존재하지 않습니다"
    exit 1
fi

# 4. 레지스트리 시크릿 생성 (존재하지 않는 경우)
create_registry_secret() {
    local namespace=$1
    local secret_name="regcred"
    
    if kubectl get secret $secret_name -n $namespace &> /dev/null; then
        log "$namespace 네임스페이스에 레지스트리 시크릿이 이미 존재합니다"
    else
        log "$namespace 네임스페이스에 레지스트리 시크릿 생성 중..."
        kubectl create secret docker-registry $secret_name \
            --docker-server=registry.jclee.me \
            --docker-username=${REGISTRY_USERNAME:-"your-username"} \
            --docker-password=${REGISTRY_PASSWORD:-"your-password"} \
            -n $namespace
    fi
}

# 5. 네임스페이스 생성
log "네임스페이스 생성 중..."
kubectl create namespace blacklist-staging --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace blacklist-prod --dry-run=client -o yaml | kubectl apply -f -

# 6. 레지스트리 시크릿 생성
create_registry_secret "blacklist-staging"
create_registry_secret "blacklist-prod"

# 7. ArgoCD 레지스트리 시크릿 생성
if ! kubectl get secret registry-credentials -n argocd &> /dev/null; then
    log "ArgoCD 레지스트리 시크릿 생성 중..."
    kubectl create secret docker-registry registry-credentials \
        --docker-server=registry.jclee.me \
        --docker-username=${REGISTRY_USERNAME:-"your-username"} \
        --docker-password=${REGISTRY_PASSWORD:-"your-password"} \
        -n argocd
fi

# 8. ArgoCD Image Updater 설정 적용
if [ -f "k8s/argocd-image-updater-config.yaml" ]; then
    log "ArgoCD Image Updater 설정 적용 중..."
    # 임시 파일로 시크릿 부분 수정
    sed "s/<base64-encoded-docker-config>/$(kubectl get secret registry-credentials -n argocd -o jsonpath='{.data.\.dockerconfigjson}')/" \
        k8s/argocd-image-updater-config.yaml | kubectl apply -f -
else
    warning "ArgoCD Image Updater 설정 파일이 없습니다"
fi

# 9. ArgoCD Applications 생성
log "ArgoCD Applications 생성 중..."

# 스테이징 애플리케이션
if argocd app get blacklist-staging --grpc-web &> /dev/null; then
    warning "blacklist-staging 애플리케이션이 이미 존재합니다"
else
    log "스테이징 애플리케이션 생성 중..."
    kubectl apply -f k8s/argocd-app-staging.yaml
    success "스테이징 애플리케이션 생성 완료"
fi

# 프로덕션 애플리케이션
if argocd app get blacklist-production --grpc-web &> /dev/null; then
    warning "blacklist-production 애플리케이션이 이미 존재합니다"
else
    log "프로덕션 애플리케이션 생성 중..."
    kubectl apply -f k8s/argocd-app-production.yaml
    success "프로덕션 애플리케이션 생성 완료"
fi

# 10. 애플리케이션 상태 확인
log "애플리케이션 상태 확인 중..."
echo ""
echo "📊 ArgoCD Applications:"
argocd app list --grpc-web | grep blacklist || true

# 11. 초기 동기화 (스테이징만)
read -p "스테이징 환경을 초기 동기화하시겠습니까? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log "스테이징 환경 동기화 중..."
    argocd app sync blacklist-staging --grpc-web || true
fi

# 12. 검증 스크립트 생성
cat > /tmp/verify-argocd.sh << 'EOF'
#!/bin/bash

echo "🔍 ArgoCD 설정 검증"
echo "=================="

# 네임스페이스 확인
echo -e "\n📁 네임스페이스:"
kubectl get namespace | grep blacklist

# 시크릿 확인
echo -e "\n🔐 레지스트리 시크릿:"
kubectl get secret -n blacklist-staging | grep regcred || echo "  스테이징: 없음"
kubectl get secret -n blacklist-prod | grep regcred || echo "  프로덕션: 없음"

# ArgoCD 애플리케이션 확인
echo -e "\n🚀 ArgoCD 애플리케이션:"
argocd app list --grpc-web | grep blacklist || echo "  애플리케이션 없음"

# Image Updater 확인
echo -e "\n🔄 Image Updater 설정:"
kubectl get cm argocd-image-updater-config -n argocd &> /dev/null && echo "  ✓ 설정됨" || echo "  ✗ 설정 안됨"
EOF

chmod +x /tmp/verify-argocd.sh

echo ""
echo "✅ ArgoCD 환경 설정 완료!"
echo ""
echo "다음 명령으로 상태를 확인할 수 있습니다:"
echo "  /tmp/verify-argocd.sh"
echo ""
echo "애플리케이션 접근:"
echo "  - 스테이징: https://blacklist-staging.jclee.me"
echo "  - 프로덕션: https://blacklist.jclee.me (수동 배포 필요)"
echo ""
echo "ArgoCD UI: https://$ARGOCD_SERVER"