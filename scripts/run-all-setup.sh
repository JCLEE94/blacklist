#!/bin/bash
# 전체 GitOps CI/CD 설정 실행 스크립트 - Blacklist Management System
set -e

echo "🚀 Blacklist Management System - 전체 GitOps CI/CD 설정"
echo "======================================================"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 실행 단계 추적
CURRENT_STEP=0
TOTAL_STEPS=6

step() {
    CURRENT_STEP=$((CURRENT_STEP + 1))
    echo -e "\n${YELLOW}=== Step $CURRENT_STEP/$TOTAL_STEPS: $1 ===${NC}"
}

# 사전 요구사항 확인
check_prerequisites() {
    step "사전 요구사항 확인"
    
    local missing_tools=()
    
    # 필수 도구들 확인
    tools=("git" "kubectl" "helm" "argocd" "curl" "python3")
    for tool in "${tools[@]}"; do
        if ! command -v $tool >/dev/null 2>&1; then
            missing_tools+=($tool)
        else
            log_success "$tool 설치됨"
        fi
    done
    
    # GitHub CLI 확인 (선택사항)
    if ! command -v gh >/dev/null 2>&1; then
        log_warning "GitHub CLI가 설치되지 않음 - GitHub Secrets 수동 설정 필요"
    else
        log_success "GitHub CLI 설치됨"
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "다음 도구들이 설치되지 않았습니다: ${missing_tools[*]}"
        echo ""
        echo "설치 명령어:"
        echo "# Ubuntu/Debian:"
        echo "sudo apt-get update && sudo apt-get install -y git curl python3"
        echo ""
        echo "# Kubernetes 도구들:"
        echo "# kubectl: https://kubernetes.io/docs/tasks/tools/install-kubectl/"
        echo "# helm: https://helm.sh/docs/intro/install/"
        echo "# argocd: https://argo-cd.readthedocs.io/en/stable/cli_installation/"
        echo ""
        echo "# GitHub CLI:"
        echo "# https://cli.github.com/manual/installation"
        exit 1
    fi
    
    # Git 저장소 확인
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Git 저장소가 아닙니다. Git 저장소에서 실행해주세요."
        exit 1
    fi
    
    # Kubernetes 클러스터 연결 확인
    if ! kubectl cluster-info > /dev/null 2>&1; then
        log_warning "Kubernetes 클러스터에 연결할 수 없습니다."
        log_info "kubectl config를 확인하거나 클러스터를 시작해주세요."
    else
        log_success "Kubernetes 클러스터 연결됨"
    fi
    
    log_success "사전 요구사항 확인 완료"
}

# 1단계: GitOps CI/CD 초기 설정
setup_gitops_config() {
    step "GitOps CI/CD 초기 설정"
    
    if [ -f "scripts/setup-gitops-cicd.sh" ]; then
        log_info "GitOps CI/CD 초기 설정 스크립트 실행 중..."
        chmod +x scripts/setup-gitops-cicd.sh
        ./scripts/setup-gitops-cicd.sh
        log_success "GitOps CI/CD 초기 설정 완료"
    else
        log_error "scripts/setup-gitops-cicd.sh 파일을 찾을 수 없습니다."
        exit 1
    fi
}

# 2단계: Helm Charts 생성
generate_helm_charts() {
    step "Helm Charts 생성"
    
    if [ -f "scripts/generate-helm-charts.sh" ]; then
        log_info "Helm Charts 생성 스크립트 실행 중..."
        chmod +x scripts/generate-helm-charts.sh
        ./scripts/generate-helm-charts.sh
        log_success "Helm Charts 생성 완료"
        
        # Helm Chart 검증
        if [ -d "charts/blacklist" ]; then
            log_info "Helm Chart 문법 검증 중..."
            if helm lint charts/blacklist; then
                log_success "Helm Chart 문법 검증 완료"
            else
                log_warning "Helm Chart 문법 검증에서 경고가 발생했습니다."
            fi
        fi
    else
        log_error "scripts/generate-helm-charts.sh 파일을 찾을 수 없습니다."
        exit 1
    fi
}

# 3단계: GitHub Actions 워크플로우 생성
create_github_workflow() {
    step "GitHub Actions 워크플로우 생성"
    
    if [ -f "scripts/create-github-workflow.sh" ]; then
        log_info "GitHub Actions 워크플로우 생성 스크립트 실행 중..."
        chmod +x scripts/create-github-workflow.sh
        ./scripts/create-github-workflow.sh
        log_success "GitHub Actions 워크플로우 생성 완료"
        
        # 워크플로우 파일 검증
        if [ -f ".github/workflows/gitops-cicd.yaml" ]; then
            log_success "워크플로우 파일 생성 확인됨"
        else
            log_error "워크플로우 파일 생성에 실패했습니다."
            exit 1
        fi
    else
        log_error "scripts/create-github-workflow.sh 파일을 찾을 수 없습니다."
        exit 1
    fi
}

# 4단계: ArgoCD 애플리케이션 설정
setup_argocd_application() {
    step "ArgoCD 애플리케이션 설정"
    
    if [ -f "scripts/setup-argocd-app.sh" ]; then
        log_info "ArgoCD 애플리케이션 설정 스크립트 실행 중..."
        chmod +x scripts/setup-argocd-app.sh  
        ./scripts/setup-argocd-app.sh
        log_success "ArgoCD 애플리케이션 설정 완료"
        
        # ArgoCD 매니페스트 파일 검증
        if [ -f "argocd/application.yaml" ]; then
            log_success "ArgoCD 애플리케이션 매니페스트 생성 확인됨"
        else
            log_error "ArgoCD 애플리케이션 매니페스트 생성에 실패했습니다."
            exit 1
        fi
    else
        log_error "scripts/setup-argocd-app.sh 파일을 찾을 수 없습니다."
        exit 1
    fi
}

# 5단계: 스크립트 실행 권한 설정
set_script_permissions() {
    step "스크립트 실행 권한 설정"
    
    # 모든 스크립트에 실행 권한 부여
    find scripts/ -name "*.sh" -exec chmod +x {} \;
    find argocd/ -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true
    
    log_success "모든 스크립트에 실행 권한 설정 완료"
}

# 6단계: 배포 검증 준비
prepare_validation() {
    step "배포 검증 준비"
    
    if [ -f "scripts/validate-deployment.sh" ]; then
        chmod +x scripts/validate-deployment.sh
        log_success "배포 검증 스크립트 준비 완료"
    else
        log_error "scripts/validate-deployment.sh 파일을 찾을 수 없습니다."
        exit 1
    fi
}

# Git 상태 확인 및 커밋 준비
prepare_git_commit() {
    echo -e "\n${YELLOW}=== Git 상태 확인 및 커밋 준비 ===${NC}"
    
    # Git 상태 확인
    if [ -n "$(git status --porcelain)" ]; then
        log_info "변경된 파일들이 있습니다:"
        git status --short
        
        echo ""
        read -p "생성된 파일들을 Git에 추가하고 커밋하시겠습니까? (y/N): " commit_changes
        if [[ "$commit_changes" =~ ^[Yy]$ ]]; then
            log_info "파일 추가 중..."
            git add .
            
            log_info "커밋 생성 중..."
            git commit -m "feat: GitOps CI/CD 파이프라인 구성 완료

- GitHub Actions 워크플로우 추가 (코드 품질, 테스트, 빌드, 배포)
- Helm Charts 생성 (Blacklist Management System 특화)
- ArgoCD 애플리케이션 설정 (GitOps 자동화)
- 배포 검증 스크립트 추가
- 종합 설정 자동화 스크립트 완성

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
            
            log_success "커밋이 생성되었습니다."
            
            echo ""
            read -p "GitHub에 푸시하시겠습니까? (y/N): " push_changes
            if [[ "$push_changes" =~ ^[Yy]$ ]]; then
                log_info "GitHub에 푸시 중..."
                git push origin main
                log_success "GitHub에 푸시 완료!"
                log_info "GitHub Actions 워크플로우가 자동으로 시작됩니다."
            fi
        else
            log_info "수동으로 Git 작업을 수행해주세요:"
            echo "  git add ."
            echo "  git commit -m 'feat: GitOps CI/CD 파이프라인 구성'"
            echo "  git push origin main"
        fi
    else
        log_info "변경된 파일이 없습니다."
    fi
}

# 최종 안내
show_final_instructions() {
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}    GitOps CI/CD 설정 완료! 🎉        ${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    echo -e "\n${BLUE}📋 생성된 구성요소:${NC}"
    echo "   ✅ GitHub Actions 워크플로우 (.github/workflows/gitops-cicd.yaml)"
    echo "   ✅ Helm Charts (charts/blacklist/)"
    echo "   ✅ ArgoCD 애플리케이션 설정 (argocd/)"
    echo "   ✅ 배포 검증 스크립트 (scripts/validate-deployment.sh)"
    echo "   ✅ 설정 자동화 스크립트들 (scripts/)"
    
    echo -e "\n${BLUE}🚀 다음 단계:${NC}"
    echo "   1. GitHub Secrets 확인:"
    echo "      - REGISTRY_URL, REGISTRY_USERNAME, REGISTRY_PASSWORD"
    echo "      - CHARTMUSEUM_URL, CHARTMUSEUM_USERNAME, CHARTMUSEUM_PASSWORD"
    echo "      - ARGOCD_URL, ARGOCD_USERNAME, ARGOCD_PASSWORD"
    echo "      - REGTECH_USERNAME, REGTECH_PASSWORD"
    echo "      - SECUDIUM_USERNAME, SECUDIUM_PASSWORD"
    
    echo ""
    echo "   2. ArgoCD 애플리케이션 배포:"
    echo "      ./argocd/deploy-argocd-app.sh"
    
    echo ""
    echo "   3. 배포 검증:"
    echo "      ./scripts/validate-deployment.sh"
    
    echo ""
    echo "   4. GitHub Actions 실행 모니터링:"
    echo "      https://github.com/JCLEE94/blacklist/actions"
    
    echo -e "\n${BLUE}🔗 접속 정보:${NC}"
    echo "   - Health Check: http://blacklist.jclee.me:32542/health"
    echo "   - Dashboard: http://blacklist.jclee.me:32542/"
    echo "   - ArgoCD: https://argo.jclee.me/applications/blacklist-blacklist"
    
    echo -e "\n${BLUE}📚 추가 도움말:${NC}"
    echo "   - GitHub Actions 문제해결: 워크플로우 로그 확인"
    echo "   - ArgoCD 문제해결: argocd app get blacklist-blacklist --grpc-web"
    echo "   - Kubernetes 문제해결: kubectl get pods -n blacklist"
    echo "   - 전체 검증: ./scripts/validate-deployment.sh"
    
    echo -e "\n${GREEN}Happy GitOps! 🎯${NC}"
}

# 메인 실행 흐름
main() {
    log_info "Blacklist Management System GitOps CI/CD 전체 설정을 시작합니다..."
    
    # 사전 요구사항 확인
    check_prerequisites
    
    # 각 단계 실행
    setup_gitops_config
    generate_helm_charts
    create_github_workflow
    setup_argocd_application
    set_script_permissions
    prepare_validation
    
    # Git 작업
    prepare_git_commit
    
    # 최종 안내
    show_final_instructions
    
    log_success "전체 설정이 완료되었습니다! 🎉"
}

# 오류 처리
trap 'log_error "스크립트 실행 중 오류가 발생했습니다. 단계 $CURRENT_STEP/$TOTAL_STEPS에서 중단됨."; exit 1' ERR

# 메인 함수 실행
main "$@"