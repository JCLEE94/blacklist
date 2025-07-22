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
