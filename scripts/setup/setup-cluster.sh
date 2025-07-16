#!/bin/bash
# 클러스터 초기 설정 스크립트
# GitOps 템플릿 기반 클러스터 설정

set -e

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 환경 변수 확인
REGISTRY_URL="${REGISTRY_URL:-registry.jclee.me}"
REGISTRY_USER="${REGISTRY_USER:-admin}"
REGISTRY_PASS="${REGISTRY_PASS:-bingogo1}"

log_info "Starting cluster setup..."

# 네임스페이스 생성
log_info "Creating namespaces..."
for ns in argocd blacklist blacklist-dev blacklist-staging monitoring; do
    kubectl create namespace $ns --dry-run=client -o yaml | kubectl apply -f -
    log_info "Namespace '$ns' created or updated"
done

# NGINX Ingress Controller 설치
log_info "Installing NGINX Ingress Controller..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml

# Ingress Controller가 준비될 때까지 대기
log_info "Waiting for NGINX Ingress Controller to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/ingress-nginx-controller -n ingress-nginx || log_warn "Ingress controller may not be fully ready"

# Harbor Registry Secret 생성
log_info "Creating Harbor registry secrets in all namespaces..."
for ns in argocd blacklist blacklist-dev blacklist-staging; do
    kubectl create secret docker-registry harbor-registry \
        --docker-server=${REGISTRY_URL} \
        --docker-username=${REGISTRY_USER} \
        --docker-password=${REGISTRY_PASS} \
        --namespace=$ns \
        --dry-run=client -o yaml | kubectl apply -f -
    log_info "Registry secret created in namespace '$ns'"
done

# Blacklist 애플리케이션용 기본 Secret 생성
log_info "Creating default application secrets..."
for ns in blacklist blacklist-dev blacklist-staging; do
    kubectl create secret generic blacklist-secret \
        --from-literal=SECRET_KEY='change-me-in-production' \
        --from-literal=JWT_SECRET_KEY='change-me-in-production' \
        --from-literal=REGTECH_USERNAME='nextrade' \
        --from-literal=REGTECH_PASSWORD='Sprtmxm1@3' \
        --from-literal=SECUDIUM_USERNAME='nextrade' \
        --from-literal=SECUDIUM_PASSWORD='Sprtmxm1@3' \
        --namespace=$ns \
        --dry-run=client -o yaml | kubectl apply -f -
    log_info "Application secret created in namespace '$ns'"
done

# 기본 리소스 제한 설정
log_info "Setting up default resource quotas..."
for ns in blacklist-dev blacklist-staging; do
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ResourceQuota
metadata:
  name: default-quota
  namespace: $ns
spec:
  hard:
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
    persistentvolumeclaims: "10"
EOF
    log_info "Resource quota created in namespace '$ns'"
done

# Production 네임스페이스는 더 큰 리소스 할당
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ResourceQuota
metadata:
  name: default-quota
  namespace: blacklist
spec:
  hard:
    requests.cpu: "16"
    requests.memory: 32Gi
    limits.cpu: "32"
    limits.memory: 64Gi
    persistentvolumeclaims: "20"
EOF
log_info "Resource quota created in namespace 'blacklist' (production)"

# 클러스터 정보 출력
log_info "Cluster setup completed!"
echo ""
log_info "Cluster Information:"
kubectl cluster-info
echo ""
log_info "Namespaces created:"
kubectl get namespaces | grep -E "(argocd|blacklist|monitoring)"
echo ""
log_info "Secrets created:"
kubectl get secrets -A | grep -E "(harbor-registry|blacklist-secret)"