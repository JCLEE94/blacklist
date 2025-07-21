#!/bin/bash
# 안정적인 배포 스크립트
set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 설정
NAMESPACE="blacklist"
APP_NAME="blacklist"
REGISTRY="registry.jclee.me"
ARGOCD_APP="blacklist"

# 로깅 함수
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 사전 체크
pre_check() {
    log "사전 체크 시작..."
    
    # kubectl 체크
    if ! command -v kubectl &> /dev/null; then
        error "kubectl이 설치되지 않았습니다"
        exit 1
    fi
    
    # ArgoCD CLI 체크
    if ! command -v argocd &> /dev/null; then
        warning "ArgoCD CLI가 설치되지 않았습니다. 수동 동기화가 필요할 수 있습니다."
    fi
    
    # 클러스터 연결 확인
    if ! kubectl cluster-info &> /dev/null; then
        error "Kubernetes 클러스터에 연결할 수 없습니다"
        exit 1
    fi
    
    success "사전 체크 완료"
}

# 네임스페이스 생성
create_namespace() {
    log "네임스페이스 확인/생성..."
    
    if kubectl get namespace $NAMESPACE &> /dev/null; then
        log "네임스페이스 $NAMESPACE가 이미 존재합니다"
    else
        kubectl create namespace $NAMESPACE
        success "네임스페이스 $NAMESPACE 생성 완료"
    fi
}

# 시크릿 생성
create_secrets() {
    log "시크릿 생성..."
    
    # Registry 시크릿
    if ! kubectl get secret regcred -n $NAMESPACE &> /dev/null; then
        kubectl create secret docker-registry regcred \
            --docker-server=$REGISTRY \
            --docker-username="${REGISTRY_USERNAME:-admin}" \
            --docker-password="${REGISTRY_PASSWORD:-bingogo1}" \
            -n $NAMESPACE
        success "Registry 시크릿 생성 완료"
    else
        log "Registry 시크릿이 이미 존재합니다"
    fi
    
    # 애플리케이션 시크릿
    if ! kubectl get secret blacklist-secrets -n $NAMESPACE &> /dev/null; then
        kubectl create secret generic blacklist-secrets \
            --from-literal=REGTECH_USERNAME="${REGTECH_USERNAME:-nextrade}" \
            --from-literal=REGTECH_PASSWORD="${REGTECH_PASSWORD:-Sprtmxm1@3}" \
            --from-literal=SECUDIUM_USERNAME="${SECUDIUM_USERNAME:-nextrade}" \
            --from-literal=SECUDIUM_PASSWORD="${SECUDIUM_PASSWORD:-Sprtmxm1@3}" \
            -n $NAMESPACE
        success "애플리케이션 시크릿 생성 완료"
    else
        log "애플리케이션 시크릿이 이미 존재합니다"
    fi
}

# Kubernetes 리소스 적용
apply_k8s_resources() {
    log "Kubernetes 리소스 적용..."
    
    # Kustomize 사용
    if [ -f "k8s/kustomization.yaml" ]; then
        kubectl apply -k k8s/ -n $NAMESPACE
        success "Kustomize 리소스 적용 완료"
    else
        # 개별 파일 적용
        for file in k8s/*.yaml; do
            if [[ ! "$file" =~ "argocd" ]]; then
                kubectl apply -f "$file" -n $NAMESPACE
            fi
        done
        success "Kubernetes 리소스 적용 완료"
    fi
}

# ArgoCD 애플리케이션 생성/업데이트
setup_argocd() {
    log "ArgoCD 설정..."
    
    if command -v argocd &> /dev/null; then
        # ArgoCD 로그인 확인
        if argocd app list &> /dev/null; then
            # 애플리케이션 확인
            if argocd app get $ARGOCD_APP &> /dev/null; then
                log "ArgoCD 애플리케이션이 이미 존재합니다. 동기화 중..."
                argocd app sync $ARGOCD_APP --grpc-web
            else
                log "ArgoCD 애플리케이션 생성 중..."
                kubectl apply -f k8s/argocd-app-stable.yaml
            fi
            success "ArgoCD 설정 완료"
        else
            warning "ArgoCD에 로그인되어 있지 않습니다. 수동으로 동기화해주세요."
            kubectl apply -f k8s/argocd-app-stable.yaml
        fi
    else
        log "ArgoCD CLI가 없습니다. manifest로 애플리케이션을 생성합니다."
        kubectl apply -f k8s/argocd-app-stable.yaml
    fi
}

# 배포 상태 확인
check_deployment() {
    log "배포 상태 확인..."
    
    # Deployment 상태 확인
    kubectl rollout status deployment/$APP_NAME -n $NAMESPACE --timeout=300s || {
        error "배포 실패. 롤백을 고려하세요."
        kubectl rollout undo deployment/$APP_NAME -n $NAMESPACE
        exit 1
    }
    
    # Pod 상태 확인
    log "Pod 상태:"
    kubectl get pods -n $NAMESPACE -l app=$APP_NAME
    
    # Service 상태 확인
    log "Service 상태:"
    kubectl get svc -n $NAMESPACE
    
    success "배포 완료"
}

# 헬스체크
health_check() {
    log "헬스체크 수행..."
    
    # NodePort 확인
    NODE_PORT=$(kubectl get svc $APP_NAME-service -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "32452")
    
    # 헬스체크 시도
    MAX_RETRIES=30
    RETRY_COUNT=0
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -f "http://localhost:${NODE_PORT}/health" &> /dev/null; then
            success "헬스체크 성공"
            curl -s "http://localhost:${NODE_PORT}/health" | python3 -m json.tool
            return 0
        fi
        
        RETRY_COUNT=$((RETRY_COUNT + 1))
        log "헬스체크 대기 중... ($RETRY_COUNT/$MAX_RETRIES)"
        sleep 5
    done
    
    error "헬스체크 실패"
    return 1
}

# 메인 실행
main() {
    echo "========================================="
    echo "    블랙리스트 시스템 안정적 배포 시작"
    echo "========================================="
    
    pre_check
    create_namespace
    create_secrets
    apply_k8s_resources
    setup_argocd
    check_deployment
    health_check
    
    echo ""
    success "배포가 성공적으로 완료되었습니다!"
    echo ""
    log "접속 정보:"
    echo "  - NodePort: http://localhost:32452"
    echo "  - 대시보드: http://localhost:32452/"
    echo "  - API 상태: http://localhost:32452/api/stats"
    echo "  - 헬스체크: http://localhost:32452/health"
    echo ""
}

# 실행
main "$@"