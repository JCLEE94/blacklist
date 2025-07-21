#!/bin/bash
# GitOps 설정 스크립트

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 설정
CONFIG_REPO="blacklist-k8s-config"
GITHUB_ORG="JCLEE94"
K8S_DIR="k8s-gitops"

# 함수 정의
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 메인 스크립트
main() {
    echo "========================================="
    echo "       GitOps 구조 설정 스크립트"
    echo "========================================="
    echo ""
    
    # 1. 현재 위치 확인
    if [ ! -f "main.py" ]; then
        error "블랙리스트 프로젝트 루트에서 실행해주세요"
    fi
    
    # 2. Git 상태 확인
    log "Git 상태 확인..."
    if [ -n "$(git status --porcelain)" ]; then
        warning "커밋되지 않은 변경사항이 있습니다. 계속하시겠습니까? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # 3. 설정 저장소 생성 안내
    log "GitHub에서 새 저장소를 생성해주세요:"
    echo ""
    echo "  저장소 이름: ${CONFIG_REPO}"
    echo "  설명: Kubernetes configurations for Blacklist system"
    echo "  공개/비공개: 비공개 권장"
    echo ""
    echo "생성하셨나요? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        error "먼저 GitHub에서 저장소를 생성해주세요"
    fi
    
    # 4. Personal Access Token 확인
    log "GitHub Personal Access Token이 필요합니다"
    echo "다음 권한이 필요합니다: repo, workflow"
    echo -n "TOKEN: "
    read -rs GITHUB_TOKEN
    echo ""
    
    # 5. k8s-gitops 디렉토리를 별도 저장소로 푸시
    log "K8s 설정을 별도 저장소로 분리..."
    
    # 임시 디렉토리로 복사
    TEMP_DIR=$(mktemp -d)
    cp -r ${K8S_DIR}/* ${TEMP_DIR}/
    
    # 새 Git 저장소 초기화
    cd ${TEMP_DIR}
    git init
    git add .
    git commit -m "feat: Initial GitOps configuration

- Base Kubernetes manifests
- Environment-specific overlays (dev, staging, prod)  
- ArgoCD application definitions
- Kustomization configurations"
    
    # 원격 저장소 추가 및 푸시
    git remote add origin https://${GITHUB_TOKEN}@github.com/${GITHUB_ORG}/${CONFIG_REPO}.git
    git branch -M main
    git push -u origin main || error "저장소 푸시 실패. 저장소가 존재하고 토큰이 올바른지 확인하세요"
    
    success "K8s 설정이 별도 저장소로 분리되었습니다"
    
    # 6. 원래 디렉토리로 돌아가기
    cd - > /dev/null
    
    # 7. .gitignore 업데이트
    log ".gitignore 업데이트..."
    if ! grep -q "k8s-gitops/" .gitignore; then
        echo "" >> .gitignore
        echo "# GitOps configurations (moved to separate repo)" >> .gitignore
        echo "k8s-gitops/" >> .gitignore
        echo "*.env.secret" >> .gitignore
    fi
    
    # 8. GitHub Secrets 설정 안내
    log "GitHub Secrets 설정이 필요합니다"
    echo ""
    echo "https://github.com/${GITHUB_ORG}/blacklist/settings/secrets/actions"
    echo ""
    echo "다음 시크릿을 추가해주세요:"
    echo "  - CONFIG_REPO_TOKEN: ${GITHUB_TOKEN}"
    echo "  - REGISTRY_USERNAME: admin"
    echo "  - REGISTRY_PASSWORD: <your-registry-password>"
    echo ""
    
    # 9. ArgoCD 애플리케이션 생성
    log "ArgoCD 애플리케이션을 생성하시겠습니까? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        if command -v argocd &> /dev/null; then
            log "ArgoCD에 로그인..."
            argocd login argo.jclee.me --username admin --grpc-web
            
            log "App of Apps 생성..."
            kubectl apply -f ${K8S_DIR}/argocd/applications/app-of-apps.yaml
            
            success "ArgoCD 애플리케이션이 생성되었습니다"
        else
            warning "ArgoCD CLI가 설치되지 않았습니다. 수동으로 생성해주세요"
            echo "kubectl apply -f ${K8S_DIR}/argocd/applications/app-of-apps.yaml"
        fi
    fi
    
    # 10. 완료
    echo ""
    success "GitOps 설정이 완료되었습니다!"
    echo ""
    echo "📋 다음 단계:"
    echo "1. GitHub Secrets 설정 완료"
    echo "2. 새 워크플로우 활성화: mv .github/workflows/gitops-cicd.yml .github/workflows/cicd.yml"
    echo "3. 첫 배포 테스트: git tag v1.0.0 && git push origin v1.0.0"
    echo "4. ArgoCD에서 배포 상태 확인: https://argo.jclee.me"
    echo ""
    echo "📚 설정 저장소: https://github.com/${GITHUB_ORG}/${CONFIG_REPO}"
    echo ""
    
    # 정리
    rm -rf ${TEMP_DIR}
}

# 실행
main "$@"