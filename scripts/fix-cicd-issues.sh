#!/bin/bash
set -e

echo "🔧 CI/CD 파이프라인 문제 해결 스크립트"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}🔹 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Step 1: Check and fix GitHub authentication
print_step "1. GitHub 인증 상태 확인 및 수정"
if gh auth status &>/dev/null; then
    print_success "GitHub 인증 상태 정상"
else
    print_warning "GitHub 인증이 필요합니다"
    echo "다음 명령을 실행하세요:"
    echo "  gh auth login"
    echo "  gh auth refresh"
    echo ""
    read -p "GitHub 인증을 완료했습니까? (y/n): " auth_complete
    if [ "$auth_complete" != "y" ]; then
        print_error "GitHub 인증을 완료한 후 다시 실행하세요"
        exit 1
    fi
fi

# Step 2: Check git status and stage files
print_step "2. Git 상태 확인 및 변경사항 준비"
git_status=$(git status --porcelain 2>/dev/null || echo "")
if [ -n "$git_status" ]; then
    print_warning "작업 디렉토리에 변경사항이 있습니다"
    echo "$git_status"
    echo ""
    
    # Ask if user wants to add all changes
    read -p "모든 변경사항을 추가하시겠습니까? (y/n): " add_all
    if [ "$add_all" = "y" ]; then
        git add .
        print_success "모든 변경사항이 스테이징됨"
        
        # Commit with a default message
        commit_msg="fix: CI/CD pipeline improvements and Docker Compose migration"
        git commit -m "$commit_msg"
        print_success "변경사항이 커밋됨: $commit_msg"
    fi
fi

# Step 3: Check unpushed commits and push
print_step "3. 푸시되지 않은 커밋 확인 및 푸시"
unpushed=$(git log origin/main..HEAD --oneline 2>/dev/null | wc -l || echo "0")
if [ "$unpushed" -gt 0 ]; then
    print_warning "$unpushed 개의 커밋이 푸시 대기 중입니다"
    git log origin/main..HEAD --oneline
    echo ""
    
    read -p "이 커밋들을 푸시하시겠습니까? (y/n): " push_commits
    if [ "$push_commits" = "y" ]; then
        print_step "푸시 중..."
        if git push origin main; then
            print_success "커밋이 성공적으로 푸시됨"
        else
            print_error "푸시 실패. 수동으로 푸시하세요: git push origin main"
            exit 1
        fi
    else
        print_warning "커밋이 푸시되지 않았습니다. GitHub Actions가 트리거되지 않습니다."
    fi
else
    print_success "모든 커밋이 이미 푸시됨"
fi

# Step 4: Verify Docker build locally
print_step "4. Docker 빌드 테스트 (선택사항)"
if command -v docker &> /dev/null && docker info &> /dev/null; then
    read -p "로컬 Docker 빌드를 테스트하시겠습니까? (y/n): " test_build
    if [ "$test_build" = "y" ]; then
        print_step "Docker 빌드 테스트 중..."
        if docker build -f docker/Dockerfile -t blacklist-cicd-test . &> /tmp/docker-build.log; then
            print_success "Docker 빌드 성공"
            docker rmi blacklist-cicd-test &> /dev/null || true
        else
            print_error "Docker 빌드 실패"
            echo "로그:"
            tail -20 /tmp/docker-build.log
        fi
    fi
else
    print_warning "Docker를 사용할 수 없어 빌드 테스트 스킵"
fi

# Step 5: Check GitHub Actions workflow
print_step "5. GitHub Actions 워크플로우 상태 확인"
repo_url=$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\).git/\1/')
actions_url="https://github.com/$repo_url/actions"

print_success "GitHub Actions 페이지: $actions_url"

# Step 6: Provide next steps
echo ""
echo "🎯 다음 단계:"
echo "========================================="
echo "1. GitHub Actions 페이지에서 워크플로우 실행 확인:"
echo "   $actions_url"
echo ""
echo "2. 빌드가 실패하는 경우, 다음 명령으로 로그 확인:"
echo "   gh run list"
echo "   gh run view <run-id> --log"
echo ""
echo "3. 레지스트리 인증 문제가 있는 경우, GitHub Secrets 확인:"
echo "   - REGISTRY_USERNAME"
echo "   - REGISTRY_PASSWORD"
echo ""
echo "4. 즉시 수동 배포가 필요한 경우:"
echo "   make docker-build"
echo "   make docker-push"
echo "   docker-compose pull && docker-compose up -d"
echo ""
echo "5. 전체 상태 확인:"
echo "   make validate-cicd"
echo ""

print_success "CI/CD 파이프라인 문제 해결 프로세스 완료!"
echo "GitHub Actions에서 빌드 상태를 확인하세요."