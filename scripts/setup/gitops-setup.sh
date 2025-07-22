#!/bin/bash
# GitOps CI/CD 자동화 설정 스크립트
set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log() { echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"; }
success() { echo -e "${GREEN}✅${NC} $1"; }
warning() { echo -e "${YELLOW}⚠️${NC} $1"; }
error() { echo -e "${RED}❌${NC} $1"; }

# 프로젝트 정보
GITHUB_ORG="${GITHUB_ORG:-JCLEE94}"
APP_NAME="${APP_NAME:-blacklist}"
NAMESPACE="${NAMESPACE:-blacklist}"

log "GitOps CI/CD 구축 시작..."
log "프로젝트: ${GITHUB_ORG}/${APP_NAME}"
log "네임스페이스: ${NAMESPACE}"

# 1. 기존 파일 백업
log "기존 파일 백업 중..."
if [ -d ".github/workflows" ]; then
    mkdir -p backup/workflows
    cp -r .github/workflows/* backup/workflows/ 2>/dev/null || true
    success "워크플로우 백업 완료"
fi

# 2. GitHub CLI 확인
log "GitHub CLI 상태 확인..."
if ! command -v gh &> /dev/null; then
    error "GitHub CLI가 설치되어 있지 않습니다."
    echo "설치: brew install gh (macOS) 또는 https://cli.github.com/"
    exit 1
fi

if ! gh auth status &> /dev/null; then
    warning "GitHub CLI 로그인이 필요합니다."
    gh auth login
fi
success "GitHub CLI 준비 완료"

# 3. GitHub Secrets 설정
log "GitHub Secrets 설정 중..."
set_secret() {
    local name=$1
    local value=$2
    if gh secret list | grep -q "^${name}"; then
        warning "Secret '${name}' 이미 존재 - 건너뜀"
    else
        echo -n "${value}" | gh secret set "${name}"
        success "Secret '${name}' 설정 완료"
    fi
}

set_secret "REGISTRY_URL" "registry.jclee.me"
set_secret "REGISTRY_USERNAME" "admin"
set_secret "REGISTRY_PASSWORD" "bingogo1"
set_secret "CHARTMUSEUM_URL" "https://charts.jclee.me"
set_secret "CHARTMUSEUM_USERNAME" "admin"
set_secret "CHARTMUSEUM_PASSWORD" "bingogo1"
set_secret "ARGOCD_SERVER" "argo.jclee.me"
set_secret "ARGOCD_USERNAME" "admin"
set_secret "ARGOCD_PASSWORD" "bingogo1"

# 4. GitHub Variables 설정 (새 버전의 gh 필요)
log "GitHub Variables 설정 중..."
if gh variable list &> /dev/null; then
    set_variable() {
        local name=$1
        local value=$2
        if gh variable list | grep -q "^${name}"; then
            warning "Variable '${name}' 이미 존재 - 업데이트"
            gh variable set "${name}" -b "${value}"
        else
            gh variable set "${name}" -b "${value}"
            success "Variable '${name}' 설정 완료"
        fi
    }

    set_variable "GITHUB_ORG" "${GITHUB_ORG}"
    set_variable "APP_NAME" "${APP_NAME}"
    set_variable "NAMESPACE" "${NAMESPACE}"
else
    warning "GitHub CLI가 variable 명령을 지원하지 않습니다. 수동으로 설정해주세요."
    echo "  Settings > Secrets and variables > Actions > Variables 에서:"
    echo "  - GITHUB_ORG = ${GITHUB_ORG}"
    echo "  - APP_NAME = ${APP_NAME}"
    echo "  - NAMESPACE = ${NAMESPACE}"
fi

# 5. Helm Chart 업데이트
log "Helm Chart 확인 및 업데이트..."
if [ ! -f "charts/${APP_NAME}/Chart.yaml" ]; then
    warning "Helm Chart가 없습니다. 생성 중..."
    mkdir -p charts/${APP_NAME}/templates
    
    cat > charts/${APP_NAME}/Chart.yaml << EOF
apiVersion: v2
name: ${APP_NAME}
description: ${APP_NAME} GitOps Application
type: application
version: 1.0.0
appVersion: "1.0.0"
EOF

    cat > charts/${APP_NAME}/values.yaml << EOF
replicaCount: 2

image:
  repository: registry.jclee.me/${GITHUB_ORG}/${APP_NAME}
  pullPolicy: Always
  tag: "latest"

imagePullSecrets:
  - name: regcred

service:
  type: NodePort
  port: 80
  targetPort: 2541
  nodePort: 32452

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: ${APP_NAME}.jclee.me
      paths:
        - path: /
          pathType: Prefix

resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 200m
    memory: 256Mi

env:
  - name: PORT
    value: "2541"
  - name: ENVIRONMENT
    value: "production"

probes:
  liveness:
    httpGet:
      path: /health
      port: 2541
    initialDelaySeconds: 30
    periodSeconds: 10
  readiness:
    httpGet:
      path: /health
      port: 2541
    initialDelaySeconds: 5
    periodSeconds: 5
EOF
    success "Helm Chart 생성 완료"
else
    success "기존 Helm Chart 사용"
fi

# 6. Kubernetes 설정
log "Kubernetes 환경 설정..."
export KUBECONFIG=${KUBECONFIG:-~/.kube/config}

# 네임스페이스 생성
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
success "네임스페이스 '${NAMESPACE}' 준비 완료"

# Registry Secret 생성
kubectl create secret docker-registry regcred \
  --docker-server=registry.jclee.me \
  --docker-username=admin \
  --docker-password=bingogo1 \
  --namespace=${NAMESPACE} \
  --dry-run=client -o yaml | kubectl apply -f -
success "Registry Secret 생성 완료"

# 7. ArgoCD 설정
log "ArgoCD 설정..."
if command -v argocd &> /dev/null; then
    # ArgoCD 로그인
    argocd login argo.jclee.me --username admin --password bingogo1 --insecure || {
        warning "ArgoCD 로그인 실패 - 수동으로 설정 필요"
    }
    
    # Helm Repository 추가
    if ! argocd repo list | grep -q "https://charts.jclee.me"; then
        argocd repo add https://charts.jclee.me \
          --type helm \
          --username admin \
          --password bingogo1 \
          --insecure-skip-server-verification || {
            warning "Helm Repository 추가 실패"
        }
    fi
    success "ArgoCD Helm Repository 설정 완료"
    
    # Application 생성
    if [ -f "argocd-application.yaml" ]; then
        kubectl apply -f argocd-application.yaml
        success "ArgoCD Application 생성 완료"
    fi
else
    warning "ArgoCD CLI가 설치되어 있지 않습니다."
    echo "설치: brew install argocd (macOS)"
fi

# 8. 배포 검증 스크립트 생성
log "배포 검증 스크립트 생성..."
cat > scripts/verify-deployment.sh << 'EOF'
#!/bin/bash
# 배포 검증 스크립트

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "🚀 배포 검증 시작..."

# 1. GitHub Actions 확인
echo -n "1. GitHub Actions 상태: "
if gh run list --limit 1 | grep -q "completed"; then
    echo -e "${GREEN}✅ 성공${NC}"
else
    echo -e "${YELLOW}⏳ 진행 중${NC}"
fi

# 2. ArgoCD 동기화 확인
echo -n "2. ArgoCD 동기화 상태: "
if command -v argocd &> /dev/null; then
    if argocd app get blacklist-blacklist &> /dev/null; then
        echo -e "${GREEN}✅ 동기화됨${NC}"
    else
        echo -e "${RED}❌ 확인 필요${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ ArgoCD CLI 없음${NC}"
fi

# 3. Pod 상태 확인
echo -n "3. Pod 상태: "
POD_STATUS=$(kubectl get pods -n blacklist -l app=blacklist -o jsonpath='{.items[0].status.phase}' 2>/dev/null)
if [ "$POD_STATUS" = "Running" ]; then
    echo -e "${GREEN}✅ Running${NC}"
    IMAGE=$(kubectl get pods -n blacklist -l app=blacklist -o jsonpath='{.items[0].spec.containers[0].image}' 2>/dev/null)
    echo "   이미지: $IMAGE"
else
    echo -e "${RED}❌ Not Running${NC}"
fi

# 4. 헬스체크
echo -n "4. 애플리케이션 헬스체크: "
if curl -sf http://blacklist.jclee.me/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 정상${NC}"
else
    echo -e "${RED}❌ 실패${NC}"
fi

echo ""
echo "📊 전체 상태 요약:"
kubectl get all -n blacklist 2>/dev/null || echo "네임스페이스 확인 필요"
EOF

chmod +x scripts/verify-deployment.sh
success "배포 검증 스크립트 생성 완료"

# 9. 최종 안내
echo ""
success "GitOps CI/CD 설정 완료!"
echo ""
log "다음 단계:"
echo "1. 변경사항 커밋 및 푸시:"
echo "   git add ."
echo "   git commit -m 'feat: GitOps CI/CD 구성'"
echo "   git push origin main"
echo ""
echo "2. 배포 확인 (2-3분 후):"
echo "   ./scripts/verify-deployment.sh"
echo ""
echo "3. ArgoCD 대시보드:"
echo "   https://argo.jclee.me"
echo ""
echo "4. 애플리케이션 확인:"
echo "   http://blacklist.jclee.me"
echo ""
warning "참고: 첫 배포는 5-10분 정도 소요될 수 있습니다."