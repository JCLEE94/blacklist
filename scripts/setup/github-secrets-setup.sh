#!/bin/bash
# GitHub Secrets 자동 설정 스크립트

echo "🔐 GitHub Secrets 설정 시작..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# GitHub 정보
GITHUB_OWNER="JCLEE94"
GITHUB_REPO="blacklist"

# 시크릿 값들
CLOUDFLARE_TUNNEL_TOKEN="eyJhIjoiYThkOWM2N2Y1ODZhY2RkMTVlZWJjYzY1Y2EzYWE1YmIiLCJ0IjoiOGVhNzg5MDYtMWEwNS00NGZiLWExYmItZTUxMjE3MmNiNWFiIiwicyI6Ill6RXlZVEUwWWpRdC1tVXlNUzAwWmpRMExXSTVaR0V0WkdNM05UY3pOV1ExT1RGbSJ9"
CF_API_TOKEN="5jAteBmuobDeS6ssH1UtMOrh5yQjClD-57ljpUtJ"

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# GitHub CLI 확인
check_gh_cli() {
    if ! command -v gh &> /dev/null; then
        print_error "GitHub CLI (gh)가 설치되지 않았습니다."
        echo "설치 방법:"
        echo "  Ubuntu/Debian: curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg"
        echo "                 echo 'deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main' | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null"
        echo "                 sudo apt update && sudo apt install gh"
        echo "  macOS: brew install gh"
        exit 1
    fi
}

# GitHub 인증 확인
check_gh_auth() {
    if ! gh auth status &> /dev/null; then
        print_error "GitHub CLI 인증이 필요합니다."
        echo "다음 명령어를 실행하세요:"
        echo "  gh auth login"
        exit 1
    fi
}

# 시크릿 생성 또는 업데이트
create_or_update_secret() {
    local secret_name="$1"
    local secret_value="$2"
    
    print_step "$secret_name 시크릿 설정 중..."
    
    # 시크릿 존재 여부 확인
    if gh secret list -R "$GITHUB_OWNER/$GITHUB_REPO" | grep -q "^$secret_name"; then
        print_step "$secret_name 시크릿 업데이트 중..."
        echo -n "$secret_value" | gh secret set "$secret_name" -R "$GITHUB_OWNER/$GITHUB_REPO"
    else
        print_step "$secret_name 시크릿 생성 중..."
        echo -n "$secret_value" | gh secret set "$secret_name" -R "$GITHUB_OWNER/$GITHUB_REPO"
    fi
    
    if [ $? -eq 0 ]; then
        print_success "$secret_name 시크릿 설정 완료"
    else
        print_error "$secret_name 시크릿 설정 실패"
        return 1
    fi
}

# 메인 실행
main() {
    echo "======================================"
    echo "GitHub Secrets 자동 설정"
    echo "======================================"
    echo ""
    
    # GitHub CLI 확인
    check_gh_cli
    
    # GitHub 인증 확인
    check_gh_auth
    
    # 저장소 확인
    print_step "GitHub 저장소 확인 중..."
    if gh repo view "$GITHUB_OWNER/$GITHUB_REPO" &> /dev/null; then
        print_success "저장소 확인 완료: $GITHUB_OWNER/$GITHUB_REPO"
    else
        print_error "저장소를 찾을 수 없습니다: $GITHUB_OWNER/$GITHUB_REPO"
        exit 1
    fi
    
    # Cloudflare 시크릿 설정
    create_or_update_secret "CLOUDFLARE_TUNNEL_TOKEN" "$CLOUDFLARE_TUNNEL_TOKEN"
    create_or_update_secret "CF_API_TOKEN" "$CF_API_TOKEN"
    
    # 현재 시크릿 목록 확인
    echo ""
    print_step "현재 설정된 시크릿 목록:"
    gh secret list -R "$GITHUB_OWNER/$GITHUB_REPO" | grep -E "(CLOUDFLARE_TUNNEL_TOKEN|CF_API_TOKEN|REGISTRY_USERNAME|REGISTRY_PASSWORD)"
    
    echo ""
    echo "====================================="
    echo "✅ GitHub Secrets 설정 완료!"
    echo "====================================="
    echo "설정된 시크릿:"
    echo "  - CLOUDFLARE_TUNNEL_TOKEN"
    echo "  - CF_API_TOKEN"
    echo ""
    echo "CI/CD 파이프라인이 이제 자동으로 Cloudflare를 설정합니다."
    echo "====================================="
}

# 명령행 옵션 처리
case "${1:-setup}" in
    setup)
        main
        ;;
    list)
        print_step "GitHub Secrets 목록:"
        gh secret list -R "$GITHUB_OWNER/$GITHUB_REPO"
        ;;
    delete)
        if [ -z "$2" ]; then
            print_error "삭제할 시크릿 이름을 지정하세요"
            echo "사용법: $0 delete <secret-name>"
            exit 1
        fi
        gh secret delete "$2" -R "$GITHUB_OWNER/$GITHUB_REPO"
        ;;
    *)
        echo "사용법: $0 [setup|list|delete <secret-name>]"
        exit 1
        ;;
esac