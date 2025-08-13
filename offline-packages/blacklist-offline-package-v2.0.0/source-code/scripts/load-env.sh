#!/bin/bash

# 환경 변수 로드 스크립트
# 사용법: source scripts/load-env.sh

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# .env 파일 경로
ENV_FILE=".env"
ENV_EXAMPLE=".env.example"

# .env 파일 확인
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}경고: .env 파일이 없습니다.${NC}"
    
    # .env.example 파일 확인
    if [ -f "$ENV_EXAMPLE" ]; then
        echo -e "${YELLOW}.env.example 파일을 복사하여 .env 파일을 생성하세요:${NC}"
        echo "  cp $ENV_EXAMPLE $ENV_FILE"
        echo "  # 그 다음 .env 파일을 편집하여 실제 값을 입력하세요"
        return 1
    else
        echo -e "${RED}오류: .env.example 파일도 찾을 수 없습니다.${NC}"
        return 1
    fi
fi

# .env 파일 로드
echo -e "${GREEN}환경 변수를 로드합니다...${NC}"

# 기존 export 명령어 사용하여 환경 변수 로드
set -a  # 자동으로 변수를 export
source "$ENV_FILE"
set +a  # 자동 export 비활성화

# 필수 환경 변수 확인
REQUIRED_VARS=(
    "GITHUB_USERNAME"
    "GITHUB_TOKEN"
    "REGTECH_USERNAME"
    "REGTECH_PASSWORD"
    "SECUDIUM_USERNAME"
    "SECUDIUM_PASSWORD"
)

MISSING_VARS=()
for VAR in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!VAR}" ]; then
        MISSING_VARS+=("$VAR")
    fi
done

# 결과 출력
if [ ${#MISSING_VARS[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ 모든 필수 환경 변수가 설정되었습니다.${NC}"
    echo ""
    echo "로드된 주요 환경 변수:"
    echo "  - GITHUB_USERNAME: $GITHUB_USERNAME"
    echo "  - ARGOCD_SERVER: ${ARGOCD_SERVER:-argo.jclee.me}"
    echo "  - NAMESPACE: ${NAMESPACE:-blacklist}"
    echo ""
    echo -e "${GREEN}이제 배포 스크립트를 실행할 수 있습니다:${NC}"
    echo "  ./scripts/deploy.sh"
    echo "  ./scripts/k8s-management.sh deploy"
else
    echo -e "${RED}❌ 다음 필수 환경 변수가 설정되지 않았습니다:${NC}"
    for VAR in "${MISSING_VARS[@]}"; do
        echo "  - $VAR"
    done
    echo ""
    echo -e "${YELLOW}.env 파일을 편집하여 누락된 값을 입력하세요.${NC}"
    return 1
fi