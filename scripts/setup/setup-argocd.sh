#!/bin/bash
# ArgoCD 설치 및 설정
# GitOps 템플릿 기반 ArgoCD 설정

set -e

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
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

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# ArgoCD 버전
ARGOCD_VERSION="${ARGOCD_VERSION:-stable}"

log_info "Starting ArgoCD installation..."

# ArgoCD 설치
log_info "Installing ArgoCD version: $ARGOCD_VERSION"
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/$ARGOCD_VERSION/manifests/install.yaml

# ArgoCD 서버가 준비될 때까지 대기
log_info "Waiting for ArgoCD server to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd

# ArgoCD Image Updater 설치
log_info "Installing ArgoCD Image Updater..."
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj-labs/argocd-image-updater/stable/manifests/install.yaml

# Image Updater가 준비될 때까지 대기
kubectl wait --for=condition=available --timeout=300s deployment/argocd-image-updater -n argocd || log_warn "Image updater may take more time to be ready"

# ArgoCD 서비스 타입 변경 (선택사항)
if [ "$ARGOCD_SERVICE_TYPE" = "LoadBalancer" ]; then
    log_info "Changing ArgoCD service type to LoadBalancer..."
    kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "LoadBalancer"}}'
elif [ "$ARGOCD_SERVICE_TYPE" = "NodePort" ]; then
    log_info "Changing ArgoCD service type to NodePort..."
    kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "NodePort"}}'
else
    log_info "Keeping ArgoCD service type as ClusterIP (default)"
fi

# ArgoCD admin 비밀번호 가져오기
log_info "Retrieving ArgoCD admin password..."
ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)

# GitHub 인증을 위한 Secret 생성
if [ -n "$GITHUB_TOKEN" ]; then
    log_info "Creating GitHub credentials secret for ArgoCD..."
    kubectl create secret generic github-creds \
        --from-literal=type=git \
        --from-literal=url=https://github.com/JCLEE94/blacklist \
        --from-literal=username=not-used \
        --from-literal=password=${GITHUB_TOKEN} \
        --namespace=argocd \
        --dry-run=client -o yaml | kubectl apply -f -
fi

# ArgoCD Image Updater 설정
log_info "Configuring ArgoCD Image Updater..."
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-image-updater-config
  namespace: argocd
data:
  registries.conf: |
    registries:
    - name: harbor
      api_url: https://registry.jclee.me
      prefix: registry.jclee.me
      insecure: true
      credentials: pullsecret:argocd/harbor-registry
  git.commit-message-template: |
    build: automatic update of {{ .AppName }}

    {{ range .AppChanges -}}
    updates image {{ .Image }} to {{ .NewTag }}
    {{ end -}}

    [skip ci]
EOF

# ArgoCD RBAC 설정 (Image Updater를 위한 권한)
log_info "Configuring RBAC for ArgoCD Image Updater..."
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  policy.default: role:readonly
  policy.csv: |
    p, role:image-updater, applications, get, */*, allow
    p, role:image-updater, applications, update, */*, allow
    g, argocd-image-updater, role:image-updater
EOF

# ArgoCD 서버 정보 출력
echo ""
log_info "ArgoCD installation completed!"
echo ""
echo "=========================================="
echo "ArgoCD Access Information:"
echo "=========================================="

# 서비스 타입에 따른 접속 정보
SERVICE_TYPE=$(kubectl get svc argocd-server -n argocd -o jsonpath='{.spec.type}')
if [ "$SERVICE_TYPE" = "LoadBalancer" ]; then
    ARGOCD_URL=$(kubectl get svc argocd-server -n argocd -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    if [ -z "$ARGOCD_URL" ]; then
        ARGOCD_URL=$(kubectl get svc argocd-server -n argocd -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    fi
    echo "URL: https://$ARGOCD_URL"
elif [ "$SERVICE_TYPE" = "NodePort" ]; then
    NODE_PORT=$(kubectl get svc argocd-server -n argocd -o jsonpath='{.spec.ports[?(@.name=="https")].nodePort}')
    NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
    echo "URL: https://$NODE_IP:$NODE_PORT"
else
    echo "Port-forward command:"
    echo "  kubectl port-forward svc/argocd-server -n argocd 8080:443"
    echo "URL: https://localhost:8080"
fi

echo "Username: admin"
echo "Password: $ARGOCD_PASSWORD"
echo ""
echo "=========================================="

# ArgoCD CLI 로그인 명령어
echo ""
log_info "ArgoCD CLI login command:"
echo "argocd login localhost:8080 --username admin --password '$ARGOCD_PASSWORD' --insecure"
echo ""

# 포트 포워딩 시작 여부 확인
read -p "Do you want to start port-forwarding now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Starting port-forward to ArgoCD server..."
    log_info "Access ArgoCD at: https://localhost:8080"
    log_info "Press Ctrl+C to stop port-forwarding"
    kubectl port-forward svc/argocd-server -n argocd 8080:443
fi