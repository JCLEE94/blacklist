#!/bin/bash

echo "🚀 ArgoCD 완전 자동화 설정 스크립트"
echo "===================================="
echo ""

# 환경 변수 설정
ARGOCD_API_TOKEN="${ARGOCD_API_TOKEN:-eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJhcmdvY2QiLCJzdWIiOiJhZG1pbjphcGlLZXkiLCJuYmYiOjE3NTE1ODkwMTAsImlhdCI6MTc1MTU4OTAxMCwianRpIjoiNjg0Y2NhYmQtMWUwNi00M2E1LTlkMGEtMzRlNzE4NGMzNDUzIn0.0wNIBxenEi2_ALlhjzkmlMyWtid7gfsJj8no2CEjI}"
ARGOCD_SERVER="${ARGOCD_SERVER:-argo.jclee.me}"
ARGOCD_ADMIN_USER="${ARGOCD_ADMIN_USER:-admin}"
ARGOCD_ADMIN_PASS="${ARGOCD_ADMIN_PASS:-bingogo1}"
ARGOCD_USER="${ARGOCD_USER:-jclee}"
ARGOCD_USER_PASS="${ARGOCD_USER_PASS:-bingogo1}"
GITHUB_USER="${GITHUB_USER:-JCLEE94}"
GITHUB_TOKEN="${GITHUB_TOKEN:-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}"
REGISTRY_URL="${REGISTRY_URL:-registry.jclee.me}"
REGISTRY_USER="${REGISTRY_USER:-qws9411}"
REGISTRY_PASS="${REGISTRY_PASS:-bingogo1}"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# 스크립트 경로
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

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

print_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

# ArgoCD 로그인
argocd_login() {
    print_step "ArgoCD 로그인 중..."
    
    # API Token으로 로그인 시도
    if argocd login "$ARGOCD_SERVER" \
        --auth-token "$ARGOCD_API_TOKEN" \
        --grpc-web \
        --insecure &> /dev/null; then
        print_success "ArgoCD API Token으로 로그인 성공"
        return 0
    fi
    
    # 실패 시 사용자/비밀번호로 로그인
    if argocd login "$ARGOCD_SERVER" \
        --username "$ARGOCD_ADMIN_USER" \
        --password "$ARGOCD_ADMIN_PASS" \
        --grpc-web \
        --insecure &> /dev/null; then
        print_success "ArgoCD 사용자/비밀번호로 로그인 성공"
        return 0
    fi
    
    print_error "ArgoCD 로그인 실패"
    return 1
}

# GitHub Repository 등록 (중복 체크)
setup_github_repo() {
    print_step "GitHub Repository 설정 중..."
    
    local repo_url="https://github.com/$GITHUB_USER/blacklist"
    
    # 이미 등록된 repository 확인
    if argocd repo list --grpc-web | grep -q "$repo_url"; then
        print_warning "Repository가 이미 등록되어 있습니다: $repo_url"
        return 0
    fi
    
    # Private repository 등록
    print_info "Private Repository 등록 중: $repo_url"
    
    argocd repo add "$repo_url" \
        --username "$GITHUB_USER" \
        --password "$GITHUB_TOKEN" \
        --grpc-web
    
    if [ $? -eq 0 ]; then
        print_success "GitHub Repository 등록 완료"
    else
        print_error "GitHub Repository 등록 실패"
        return 1
    fi
}

# Private Registry 설정 (중복 체크)
setup_private_registry() {
    print_step "Private Registry 설정 중..."
    
    # ArgoCD namespace에 registry secret 생성 (중복 체크)
    if kubectl get secret regcred -n argocd &> /dev/null; then
        print_warning "Registry secret이 이미 존재합니다 (argocd namespace)"
    else
        kubectl create secret docker-registry regcred \
            --docker-server="$REGISTRY_URL" \
            --docker-username="$REGISTRY_USER" \
            --docker-password="$REGISTRY_PASS" \
            -n argocd
        print_success "Registry secret 생성 완료 (argocd namespace)"
    fi
    
    # blacklist namespace에도 secret 생성 (중복 체크)
    kubectl create namespace blacklist --dry-run=client -o yaml | kubectl apply -f - &> /dev/null
    
    if kubectl get secret regcred -n blacklist &> /dev/null; then
        print_warning "Registry secret이 이미 존재합니다 (blacklist namespace)"
    else
        kubectl create secret docker-registry regcred \
            --docker-server="$REGISTRY_URL" \
            --docker-username="$REGISTRY_USER" \
            --docker-password="$REGISTRY_PASS" \
            -n blacklist
        print_success "Registry secret 생성 완료 (blacklist namespace)"
    fi
}

# ArgoCD Image Updater 설정 (중복 체크)
setup_image_updater() {
    print_step "ArgoCD Image Updater 설정 중..."
    
    # Image Updater가 설치되어 있는지 확인
    if ! kubectl get deployment argocd-image-updater -n argocd &> /dev/null; then
        print_warning "ArgoCD Image Updater가 설치되지 않았습니다."
        print_info "설치 방법: kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj-labs/argocd-image-updater/stable/manifests/install.yaml"
        return 1
    fi
    
    # Registry access secret 생성 (중복 체크)
    if kubectl get secret argocd-image-updater-secret -n argocd &> /dev/null; then
        print_warning "Image Updater secret이 이미 존재합니다"
    else
        kubectl create secret generic argocd-image-updater-secret \
            --from-literal=registries="$REGISTRY_URL:$REGISTRY_USER:$REGISTRY_PASS" \
            -n argocd
        print_success "Image Updater secret 생성 완료"
    fi
    
    # ConfigMap 업데이트
    cat > /tmp/argocd-image-updater-config.yaml << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-image-updater-config
  namespace: argocd
data:
  registries.conf: |
    registries:
    - name: PrivateRegistry
      api_url: https://$REGISTRY_URL
      prefix: $REGISTRY_URL
      credentials: secret:argocd/argocd-image-updater-secret#registries
      default: true
EOF
    
    kubectl apply -f /tmp/argocd-image-updater-config.yaml
    rm -f /tmp/argocd-image-updater-config.yaml
    
    # Image Updater 재시작
    kubectl rollout restart deployment argocd-image-updater -n argocd
    print_success "ArgoCD Image Updater 설정 완료"
}

# ArgoCD Application 생성 (중복 체크)
create_argocd_application() {
    print_step "ArgoCD Application 생성 중..."
    
    # 이미 존재하는 application 확인
    if argocd app get blacklist --grpc-web &> /dev/null; then
        print_warning "ArgoCD Application 'blacklist'가 이미 존재합니다"
        
        # 기존 앱 업데이트 여부 확인
        read -p "기존 Application을 업데이트하시겠습니까? (y/N): " update_app
        if [[ ! "$update_app" =~ ^[Yy]$ ]]; then
            return 0
        fi
        
        # 기존 앱 삭제
        argocd app delete blacklist --grpc-web --yes
        print_info "기존 Application 삭제 완료"
    fi
    
    # 새 Application 생성을 위한 manifest
    cat > /tmp/argocd-app-blacklist.yaml << EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: blacklist
  namespace: argocd
  annotations:
    argocd-image-updater.argoproj.io/image-list: blacklist=$REGISTRY_URL/blacklist:~latest
    argocd-image-updater.argoproj.io/blacklist.update-strategy: latest
    argocd-image-updater.argoproj.io/blacklist.pull-secret: secret:blacklist/regcred
    argocd-image-updater.argoproj.io/write-back-method: git
spec:
  project: default
  source:
    repoURL: https://github.com/$GITHUB_USER/blacklist
    targetRevision: main
    path: k8s
  destination:
    server: https://kubernetes.default.svc
    namespace: blacklist
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
    - CreateNamespace=true
    - PrunePropagationPolicy=foreground
    - PruneLast=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
EOF
    
    # Application 생성
    kubectl apply -f /tmp/argocd-app-blacklist.yaml
    rm -f /tmp/argocd-app-blacklist.yaml
    
    print_success "ArgoCD Application 생성 완료"
    
    # 초기 동기화
    print_info "초기 동기화 실행 중..."
    argocd app sync blacklist --grpc-web --timeout 300
}

# GitHub Actions Secrets 설정 안내
setup_github_actions() {
    print_step "GitHub Actions 설정 안내"
    echo ""
    echo "GitHub Repository에 다음 Secrets를 설정하세요:"
    echo "https://github.com/$GITHUB_USER/blacklist/settings/secrets/actions"
    echo ""
    echo "필수 Secrets:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "REGISTRY_USERNAME: $REGISTRY_USER"
    echo "REGISTRY_PASSWORD: $REGISTRY_PASS"
    echo "ARGOCD_AUTH_TOKEN: $ARGOCD_API_TOKEN"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# CI/CD 파이프라인 파일 생성
create_cicd_pipeline() {
    print_step "CI/CD 파이프라인 설정 중..."
    
    local workflow_dir="$PROJECT_ROOT/.github/workflows"
    local workflow_file="$workflow_dir/argocd-deploy.yml"
    
    # 이미 존재하는 workflow 확인
    if [ -f "$workflow_file" ]; then
        print_warning "CI/CD workflow가 이미 존재합니다"
        
        # 백업 생성
        cp "$workflow_file" "$workflow_file.backup.$(date +%Y%m%d_%H%M%S)"
        print_info "기존 workflow 백업 완료"
    fi
    
    # workflow 디렉토리 생성
    mkdir -p "$workflow_dir"
    
    # 새 workflow 생성
    cat > "$workflow_file" << 'EOF'
name: ArgoCD GitOps Deploy

on:
  push:
    branches: [main]
    paths-ignore:
      - '**.md'
      - 'docs/**'
      - '.github/**'
      - '!.github/workflows/argocd-deploy.yml'

env:
  REGISTRY: registry.jclee.me
  IMAGE_NAME: blacklist

jobs:
  build-and-push:
    runs-on: self-hosted
    permissions:
      contents: read
      packages: write
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v3
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    
    - name: Log in to Private Registry
      uses: docker/login-action@v2
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ secrets.REGISTRY_USERNAME }}
        password: ${{ secrets.REGISTRY_PASSWORD }}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v4
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=sha,prefix={{branch}}-
          type=raw,value=latest,enable={{is_default_branch}}
          type=raw,value={{date 'YYYYMMDD-HHmmss'}}
    
    - name: Build and push Docker image
      uses: docker/build-push-action@v4
      with:
        context: .
        file: ./deployment/Dockerfile
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:buildcache
        cache-to: type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:buildcache,mode=max
    
    - name: Trigger ArgoCD Sync
      run: |
        # ArgoCD will automatically detect new image via Image Updater
        echo "New image pushed. ArgoCD Image Updater will detect and sync automatically."
        echo "Image tags: ${{ steps.meta.outputs.tags }}"
EOF
    
    print_success "CI/CD 파이프라인 파일 생성 완료"
}

# 전체 상태 확인
verify_setup() {
    print_step "설정 검증 중..."
    echo ""
    
    # Repository 확인
    echo -e "${CYAN}GitHub Repository:${NC}"
    argocd repo list --grpc-web | grep blacklist || echo "❌ Repository 미등록"
    echo ""
    
    # Application 확인
    echo -e "${CYAN}ArgoCD Application:${NC}"
    argocd app get blacklist --grpc-web 2>/dev/null | grep -E "Name:|Health Status:|Sync Status:" || echo "❌ Application 미생성"
    echo ""
    
    # Image Updater 확인
    echo -e "${CYAN}Image Updater:${NC}"
    kubectl get deployment argocd-image-updater -n argocd &> /dev/null && echo "✅ Image Updater 실행 중" || echo "❌ Image Updater 미설치"
    echo ""
    
    # Registry Secret 확인
    echo -e "${CYAN}Registry Secrets:${NC}"
    kubectl get secret regcred -n argocd &> /dev/null && echo "✅ ArgoCD namespace: regcred 존재" || echo "❌ ArgoCD namespace: regcred 없음"
    kubectl get secret regcred -n blacklist &> /dev/null && echo "✅ Blacklist namespace: regcred 존재" || echo "❌ Blacklist namespace: regcred 없음"
}

# 메인 실행
main() {
    echo "설정 정보:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "ArgoCD Server: $ARGOCD_SERVER"
    echo "GitHub User: $GITHUB_USER"
    echo "Registry URL: $REGISTRY_URL"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # ArgoCD 도구 확인
    if ! command -v argocd &> /dev/null; then
        print_error "argocd CLI가 설치되지 않았습니다"
        echo "설치: curl -sSL -o /usr/local/bin/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64"
        exit 1
    fi
    
    # 단계별 실행
    argocd_login || exit 1
    setup_github_repo
    setup_private_registry
    setup_image_updater
    create_argocd_application
    create_cicd_pipeline
    setup_github_actions
    
    echo ""
    verify_setup
    
    echo ""
    print_success "ArgoCD 완전 자동화 설정 완료!"
    echo ""
    echo "🎯 다음 단계:"
    echo "1. GitHub에 Secrets 설정 (위 안내 참조)"
    echo "2. 코드 변경 후 git push"
    echo "3. ArgoCD가 자동으로 새 이미지 감지 및 배포"
    echo ""
    echo "📊 모니터링:"
    echo "- ArgoCD UI: https://$ARGOCD_SERVER"
    echo "- Application 상태: argocd app get blacklist --grpc-web"
    echo "- Image Updater 로그: kubectl logs -f deployment/argocd-image-updater -n argocd"
}

# 스크립트 실행
main "$@"