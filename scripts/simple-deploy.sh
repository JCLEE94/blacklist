#!/bin/bash

# Simple Kubernetes Deployment Script
# 사용법: ./simple-deploy.sh [production|staging|development]

set -euo pipefail

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 기본값
ENVIRONMENT="${1:-production}"
REGISTRY="registry.jclee.me"
IMAGE_NAME="blacklist"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# 로깅 함수
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

# 환경별 설정
setup_environment() {
    case $ENVIRONMENT in
        production|prod)
            NAMESPACE="blacklist"
            DEPLOYMENT="blacklist"
            KUSTOMIZE_DIR="k8s/overlays/production"
            ;;
        staging|stage)
            NAMESPACE="blacklist-staging"
            DEPLOYMENT="staging-blacklist"
            KUSTOMIZE_DIR="k8s/overlays/staging"
            ;;
        development|dev)
            NAMESPACE="blacklist-dev"
            DEPLOYMENT="dev-blacklist"
            KUSTOMIZE_DIR="k8s/overlays/development"
            ;;
        *)
            error "Unknown environment: $ENVIRONMENT"
            ;;
    esac
}

# 배포 실행
deploy() {
    log "Deploying to $ENVIRONMENT environment"
    
    # 네임스페이스 생성
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    
    # Kustomize가 있으면 사용
    if [ -d "$KUSTOMIZE_DIR" ]; then
        log "Using Kustomize from $KUSTOMIZE_DIR"
        cd $KUSTOMIZE_DIR
        kustomize edit set image blacklist=${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
        kustomize build . | kubectl apply -f -
        cd - > /dev/null
    else
        # 직접 이미지 업데이트
        log "Updating image directly"
        kubectl set image deployment/${DEPLOYMENT} \
            ${IMAGE_NAME}=${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} \
            -n $NAMESPACE --record
    fi
    
    # 배포 대기
    log "Waiting for rollout to complete..."
    kubectl rollout status deployment/${DEPLOYMENT} -n $NAMESPACE --timeout=5m
    
    success "Deployment completed!"
}

# 상태 확인
check_status() {
    log "Checking deployment status..."
    
    # Pod 상태
    echo
    echo "=== Pods ==="
    kubectl get pods -n $NAMESPACE -l app=blacklist
    
    # 서비스 상태
    echo
    echo "=== Services ==="
    kubectl get svc -n $NAMESPACE
    
    # HPA 상태 (있으면)
    echo
    echo "=== HPA ==="
    kubectl get hpa -n $NAMESPACE 2>/dev/null || echo "No HPA configured"
    
    # 최근 이벤트
    echo
    echo "=== Recent Events ==="
    kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | tail -10
}

# 헬스 체크
health_check() {
    log "Running health check..."
    
    kubectl run health-check-$(date +%s) --rm -i --restart=Never \
        --image=curlimages/curl:latest -n $NAMESPACE -- \
        curl -f http://${DEPLOYMENT}:8541/health 2>/dev/null && \
        success "Health check passed" || \
        warning "Health check failed"
}

# 롤백
rollback() {
    log "Rolling back deployment..."
    kubectl rollout undo deployment/${DEPLOYMENT} -n $NAMESPACE
    kubectl rollout status deployment/${DEPLOYMENT} -n $NAMESPACE --timeout=5m
    success "Rollback completed!"
}

# 메인 함수
main() {
    # 환경 설정
    setup_environment
    
    # 작업 선택
    case "${2:-deploy}" in
        deploy)
            deploy
            check_status
            health_check
            ;;
        status)
            check_status
            ;;
        health)
            health_check
            ;;
        rollback)
            rollback
            ;;
        *)
            echo "Usage: $0 [production|staging|development] [deploy|status|health|rollback]"
            exit 1
            ;;
    esac
}

# 실행
main "$@"