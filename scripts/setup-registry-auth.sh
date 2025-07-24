#!/bin/bash

echo "===== Docker Registry 인증 설정 ====="
echo ""

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# 레지스트리 정보
REGISTRY_URL="registry.jclee.me"
REGISTRY_USER="admin"
REGISTRY_PASS="${DOCKER_REGISTRY_PASS:-}"

# 비밀번호 입력
if [ -z "$REGISTRY_PASS" ]; then
    read -sp "Registry 비밀번호 입력: " REGISTRY_PASS
    echo ""
fi

# 1. Docker 로그인
echo -e "${YELLOW}1. Docker 로그인${NC}"
echo "$REGISTRY_PASS" | docker login $REGISTRY_URL -u $REGISTRY_USER --password-stdin

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker 로그인 성공${NC}"
else
    echo -e "${RED}❌ Docker 로그인 실패${NC}"
    exit 1
fi

# 2. Kubernetes Secret 생성/업데이트
echo ""
echo -e "${YELLOW}2. Kubernetes Secret 업데이트${NC}"

# 기존 secret 삭제
kubectl delete secret regcred -n blacklist --ignore-not-found=true

# 새 secret 생성
kubectl create secret docker-registry regcred \
  --docker-server=$REGISTRY_URL \
  --docker-username=$REGISTRY_USER \
  --docker-password=$REGISTRY_PASS \
  --namespace=blacklist

echo -e "${GREEN}✅ Kubernetes Secret 생성됨${NC}"

# 3. ArgoCD namespace에도 secret 생성
echo ""
echo -e "${YELLOW}3. ArgoCD namespace Secret 생성${NC}"

kubectl delete secret regcred -n argocd --ignore-not-found=true
kubectl create secret docker-registry regcred \
  --docker-server=$REGISTRY_URL \
  --docker-username=$REGISTRY_USER \
  --docker-password=$REGISTRY_PASS \
  --namespace=argocd

echo -e "${GREEN}✅ ArgoCD Secret 생성됨${NC}"

# 4. GitHub Actions Secret 설정 안내
echo ""
echo -e "${YELLOW}4. GitHub Actions Secret 설정${NC}"
echo "다음 값들을 GitHub Repository Settings → Secrets에 추가하세요:"
echo ""
echo "DOCKER_REGISTRY_URL: $REGISTRY_URL"
echo "DOCKER_REGISTRY_USER: $REGISTRY_USER"
echo "DOCKER_REGISTRY_PASS: [입력한 비밀번호]"
echo ""
echo "GitHub에서 설정하려면:"
echo "https://github.com/JCLEE94/blacklist/settings/secrets/actions"

echo ""
echo -e "${GREEN}===== 설정 완료 =====${NC}"
echo ""
echo "이제 다음 명령으로 이미지를 푸시할 수 있습니다:"
echo "docker push $REGISTRY_URL/jclee94/blacklist:latest"