#!/bin/bash
set -e

echo "🔍 CI/CD 파이프라인 검증 스크립트 시작"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    if [ $2 -eq 0 ]; then
        echo -e "${GREEN}✅ $1${NC}"
    else
        echo -e "${RED}❌ $1${NC}"
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check Git status
echo "1. Git 상태 확인..."
git_status=$(git status --porcelain 2>/dev/null || echo "error")
if [ "$git_status" = "error" ]; then
    print_status "Git 저장소가 아닙니다" 1
    exit 1
elif [ -z "$git_status" ]; then
    print_status "작업 디렉토리가 깨끗합니다" 0
else
    print_warning "작업 디렉토리에 변경사항이 있습니다"
    echo "$git_status"
fi

# Check unpushed commits
echo "2. 푸시되지 않은 커밋 확인..."
unpushed=$(git log origin/main..HEAD --oneline 2>/dev/null | wc -l || echo "0")
if [ $unpushed -gt 0 ]; then
    print_warning "$unpushed 개의 커밋이 푸시 대기 중입니다"
    git log origin/main..HEAD --oneline
else
    print_status "모든 커밋이 푸시됨" 0
fi

# Check GitHub authentication
echo "3. GitHub 인증 상태 확인..."
gh_auth=$(gh auth status 2>&1 | grep "Logged in" || echo "not_logged_in")
if [[ $gh_auth == *"Logged in"* ]]; then
    print_status "GitHub 인증됨" 0
else
    print_status "GitHub 인증 필요" 1
    echo "gh auth login 명령을 실행하세요"
fi

# Check Docker
echo "4. Docker 상태 확인..."
if command -v docker &> /dev/null; then
    docker_running=$(docker info 2>/dev/null && echo "running" || echo "not_running")
    if [ "$docker_running" = "running" ]; then
        print_status "Docker 실행 중" 0
    else
        print_status "Docker 실행되지 않음" 1
    fi
else
    print_status "Docker 설치되지 않음" 1
fi

# Check workflow files
echo "5. GitHub Actions 워크플로우 파일 확인..."
if [ -f ".github/workflows/main-deploy.yml" ]; then
    print_status "main-deploy.yml 존재" 0
else
    print_status "main-deploy.yml 없음" 1
fi

if [ -f ".github/workflows/github-pages.yml" ]; then
    print_status "github-pages.yml 존재" 0
else
    print_status "github-pages.yml 없음" 1
fi

# Check Dockerfile
echo "6. Dockerfile 확인..."
if [ -f "docker/Dockerfile" ]; then
    print_status "Dockerfile 존재" 0
    # Check if main entry point exists
    if [ -f "commands/scripts/main.py" ]; then
        print_status "메인 진입점 존재" 0
    else
        print_status "메인 진입점 없음" 1
    fi
else
    print_status "Dockerfile 없음" 1
fi

# Check requirements
echo "7. 요구사항 파일 확인..."
if [ -f "config/requirements.txt" ]; then
    print_status "requirements.txt 존재" 0
    req_count=$(wc -l < config/requirements.txt)
    echo "   📦 $req_count 개의 의존성"
else
    print_status "requirements.txt 없음" 1
fi

# Check docker-compose
echo "8. Docker Compose 설정 확인..."
if [ -f "docker-compose.yml" ]; then
    print_status "docker-compose.yml 존재" 0
    
    # Check image name
    image_name=$(grep "image:" docker-compose.yml | head -1 | awk '{print $2}')
    echo "   🐳 이미지: $image_name"
    
    # Check ports
    port_mapping=$(grep "ports:" -A1 docker-compose.yml | tail -1 | awk '{print $2}' | tr -d '"')
    echo "   🔌 포트: $port_mapping"
else
    print_status "docker-compose.yml 없음" 1
fi

# Test local build
echo "9. 로컬 Docker 빌드 테스트..."
if command -v docker &> /dev/null && docker info &> /dev/null; then
    echo "   Docker 빌드 테스트 중..."
    if docker build -f docker/Dockerfile -t blacklist-test . &> /tmp/docker-build.log; then
        print_status "Docker 빌드 성공" 0
        docker rmi blacklist-test &> /dev/null || true
    else
        print_status "Docker 빌드 실패" 1
        echo "   로그: /tmp/docker-build.log 확인"
        tail -10 /tmp/docker-build.log
    fi
else
    print_warning "Docker를 사용할 수 없어 빌드 테스트 스킵"
fi

echo "=================================================="
echo "🏁 CI/CD 파이프라인 검증 완료"

# Summary
echo ""
echo "📋 다음 단계:"
if [ $unpushed -gt 0 ]; then
    echo "1. 변경사항을 커밋하고 푸시하세요:"
    echo "   git add ."
    echo "   git commit -m 'fix: CI/CD pipeline improvements'"
    echo "   git push origin main"
fi

if [[ $gh_auth != *"Logged in"* ]]; then
    echo "2. GitHub 인증하세요:"
    echo "   gh auth login"
fi

echo "3. GitHub Actions 페이지에서 워크플로우 실행 확인:"
echo "   https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\).git/\1/')/actions"

echo ""
echo "🔧 수동 배포 명령:"
echo "   docker-compose pull && docker-compose up -d"