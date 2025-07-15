#!/bin/bash

echo "🔐 GitHub Repository Secrets 설정 스크립트"
echo "========================================"
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# GitHub CLI 확인
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ GitHub CLI가 설치되어 있지 않습니다.${NC}"
    echo ""
    echo "설치 방법:"
    echo "  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg"
    echo "  echo \"deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main\" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null"
    echo "  sudo apt update && sudo apt install gh"
    echo ""
    echo "또는 수동으로 설정하세요:"
    echo ""
fi

# Repository 정보
REPO_OWNER="jclee"
REPO_NAME="blacklist"

echo -e "${BLUE}GitHub Repository:${NC} $REPO_OWNER/$REPO_NAME"
echo ""

# Registry 정보
REGISTRY_URL="registry.jclee.me"
REGISTRY_USERNAME="admin"
REGISTRY_PASSWORD="bingogo1"

echo "📝 설정할 시크릿:"
echo "  - REGISTRY_USERNAME: $REGISTRY_USERNAME"
echo "  - REGISTRY_PASSWORD: ********"
echo ""

# GitHub CLI로 설정
if command -v gh &> /dev/null; then
    echo -e "${BLUE}GitHub CLI를 사용한 자동 설정:${NC}"
    echo ""
    
    # 인증 확인
    if ! gh auth status &>/dev/null; then
        echo -e "${YELLOW}GitHub CLI 로그인이 필요합니다:${NC}"
        echo "  gh auth login"
        echo ""
    else
        # 시크릿 설정
        echo "시크릿 설정 중..."
        
        # REGISTRY_USERNAME
        echo -n "$REGISTRY_USERNAME" | gh secret set REGISTRY_USERNAME --repo="$REPO_OWNER/$REPO_NAME"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ REGISTRY_USERNAME 설정 완료${NC}"
        else
            echo -e "${RED}✗ REGISTRY_USERNAME 설정 실패${NC}"
        fi
        
        # REGISTRY_PASSWORD
        echo -n "$REGISTRY_PASSWORD" | gh secret set REGISTRY_PASSWORD --repo="$REPO_OWNER/$REPO_NAME"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ REGISTRY_PASSWORD 설정 완료${NC}"
        else
            echo -e "${RED}✗ REGISTRY_PASSWORD 설정 실패${NC}"
        fi
        
        echo ""
        echo -e "${GREEN}✅ GitHub Secrets 설정 완료!${NC}"
    fi
else
    echo -e "${YELLOW}수동 설정 방법:${NC}"
fi

echo ""
echo "🌐 웹브라우저에서 수동 설정하는 방법:"
echo ""
echo "1. GitHub 저장소로 이동:"
echo "   https://github.com/$REPO_OWNER/$REPO_NAME"
echo ""
echo "2. Settings → Secrets and variables → Actions 클릭"
echo ""
echo "3. 'New repository secret' 버튼 클릭"
echo ""
echo "4. 다음 시크릿 추가:"
echo ""
echo "   첫 번째 시크릿:"
echo "   - Name: REGISTRY_USERNAME"
echo "   - Value: $REGISTRY_USERNAME"
echo ""
echo "   두 번째 시크릿:"
echo "   - Name: REGISTRY_PASSWORD"  
echo "   - Value: $REGISTRY_PASSWORD"
echo ""
echo "5. 각각 'Add secret' 버튼 클릭하여 저장"
echo ""

# 현재 시크릿 확인
if command -v gh &> /dev/null && gh auth status &>/dev/null; then
    echo -e "${BLUE}현재 설정된 시크릿 목록:${NC}"
    gh secret list --repo="$REPO_OWNER/$REPO_NAME" 2>/dev/null || echo "시크릿을 조회할 수 없습니다."
    echo ""
fi

echo "📌 참고사항:"
echo "  - 시크릿은 암호화되어 저장되며, 설정 후에는 값을 볼 수 없습니다"
echo "  - CI/CD 파이프라인에서 \${{ secrets.REGISTRY_USERNAME }} 형태로 사용됩니다"
echo "  - 변경이 필요한 경우 같은 이름으로 다시 설정하면 덮어쓰기됩니다"
echo ""

# 테스트 방법 안내
echo -e "${BLUE}설정 확인 방법:${NC}"
echo "1. 코드를 push하여 GitHub Actions 실행"
echo "2. Actions 탭에서 'GitOps Pipeline' 워크플로우 확인"
echo "3. 'Build and push' 단계에서 Docker login 성공 여부 확인"
echo ""

# 추가 시크릿 안내
echo -e "${YELLOW}선택적 시크릿 (필요시 추가):${NC}"
echo "  - REGTECH_USERNAME: REGTECH 수집 계정"
echo "  - REGTECH_PASSWORD: REGTECH 수집 비밀번호"
echo "  - SECUDIUM_USERNAME: SECUDIUM 수집 계정"
echo "  - SECUDIUM_PASSWORD: SECUDIUM 수집 비밀번호"
echo "  - CLOUDFLARE_TUNNEL_TOKEN: Cloudflare Tunnel 토큰"
echo "  - CF_API_TOKEN: Cloudflare API 토큰"
echo ""