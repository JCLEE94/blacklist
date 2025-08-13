#!/bin/bash

# 🔍 Blacklist GitOps 배포 검증 스크립트
# =====================================

set -e

echo "🚀 Blacklist GitOps 배포 검증 시작..."
echo "====================================="

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 환경 변수
NAMESPACE=${K8S_NAMESPACE:-default}
APP_NAME="blacklist"
ARGOCD_SERVER=${ARGOCD_SERVER:-argo.jclee.me}
APP_URL="https://blacklist.jclee.me"

# 1. GitHub Actions 상태 확인
echo -e "\n📋 GitHub Actions 워크플로우 상태:"
echo "-----------------------------------"
WORKFLOW_STATUS=$(curl -s https://api.github.com/repos/JCLEE94/blacklist/actions/runs?per_page=1 | \
    grep -oP '"conclusion":\s*"\K[^"]+' | head -1 || echo "unknown")

if [ "$WORKFLOW_STATUS" = "success" ]; then
    echo -e "${GREEN}✅ 최근 워크플로우: 성공${NC}"
elif [ "$WORKFLOW_STATUS" = "failure" ]; then
    echo -e "${RED}❌ 최근 워크플로우: 실패${NC}"
else
    echo -e "${YELLOW}⚠️ 워크플로우 상태: $WORKFLOW_STATUS${NC}"
fi

# 2. Docker 이미지 확인
echo -e "\n🐳 Docker 이미지 상태:"
echo "----------------------"
LATEST_IMAGE="registry.jclee.me/jclee94/blacklist:latest"
echo "이미지: $LATEST_IMAGE"

# Docker Compose 상태 확인 (로컬)
if command -v docker-compose &> /dev/null; then
    echo -e "\n🐋 Docker Compose 상태:"
    docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || true
fi

# 3. Kubernetes 리소스 상태 (kubectl이 있는 경우)
if command -v kubectl &> /dev/null; then
    echo -e "\n⚙️ Kubernetes 리소스 상태:"
    echo "-------------------------"
    
    # Deployment 상태
    DEPLOYMENT_STATUS=$(kubectl get deployment $APP_NAME -n $NAMESPACE -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' 2>/dev/null || echo "Unknown")
    if [ "$DEPLOYMENT_STATUS" = "True" ]; then
        echo -e "${GREEN}✅ Deployment: Available${NC}"
        kubectl get deployment $APP_NAME -n $NAMESPACE --no-headers 2>/dev/null || true
    else
        echo -e "${YELLOW}⚠️ Deployment 상태 확인 불가${NC}"
    fi
    
    # Pod 상태
    echo -e "\n📦 Pod 상태:"
    kubectl get pods -n $NAMESPACE -l app=$APP_NAME --no-headers 2>/dev/null || echo "Pod 정보 없음"
    
    # Service 상태
    echo -e "\n🔗 Service 상태:"
    kubectl get svc $APP_NAME -n $NAMESPACE --no-headers 2>/dev/null || echo "Service 정보 없음"
fi

# 4. ArgoCD 애플리케이션 상태 (argocd CLI가 있는 경우)
if command -v argocd &> /dev/null; then
    echo -e "\n🎯 ArgoCD 애플리케이션 상태:"
    echo "---------------------------"
    
    for env in production staging development; do
        APP_FULLNAME="${APP_NAME}-${env}"
        SYNC_STATUS=$(argocd app get $APP_FULLNAME --server $ARGOCD_SERVER --grpc-web -o json 2>/dev/null | \
            grep -oP '"sync":\s*{\s*"status":\s*"\K[^"]+' || echo "Unknown")
        
        if [ "$SYNC_STATUS" = "Synced" ]; then
            echo -e "${GREEN}✅ $APP_FULLNAME: Synced${NC}"
        else
            echo -e "${YELLOW}⚠️ $APP_FULLNAME: $SYNC_STATUS${NC}"
        fi
    done
fi

# 5. 애플리케이션 Health Check
echo -e "\n💚 애플리케이션 Health Check:"
echo "----------------------------"

# 로컬 Docker Compose 체크
LOCAL_URL="http://localhost:2541/health"
if curl -f -s -o /dev/null -w "%{http_code}" "$LOCAL_URL" | grep -q "200"; then
    echo -e "${GREEN}✅ 로컬 환경: 정상 ($LOCAL_URL)${NC}"
else
    echo -e "${YELLOW}⚠️ 로컬 환경: 응답 없음${NC}"
fi

# Production 환경 체크 (blacklist.jclee.me)
if [ -n "$APP_URL" ]; then
    HTTP_CODE=$(curl -f -s -o /dev/null -w "%{http_code}" "$APP_URL/health" || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✅ Production: 정상 ($APP_URL)${NC}"
        
        # 응답 시간 측정
        RESPONSE_TIME=$(curl -w "%{time_total}" -o /dev/null -s "$APP_URL/health")
        echo "   응답 시간: ${RESPONSE_TIME}초"
    else
        echo -e "${RED}❌ Production: HTTP $HTTP_CODE${NC}"
    fi
fi

# 6. 최근 로그 확인 (Docker)
echo -e "\n📜 최근 애플리케이션 로그 (Docker):"
echo "-----------------------------------"
if command -v docker &> /dev/null; then
    docker logs blacklist --tail 5 2>/dev/null || echo "Docker 로그 없음"
fi

# 7. 메트릭 수집
echo -e "\n📊 배포 메트릭:"
echo "---------------"

# Git 정보
CURRENT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
echo "현재 커밋: $CURRENT_COMMIT"
echo "현재 브랜치: $CURRENT_BRANCH"

# 배포 시간
if [ -f VERSION ]; then
    VERSION=$(cat VERSION)
    echo "현재 버전: $VERSION"
fi

# 8. 종합 상태
echo -e "\n📈 종합 배포 상태:"
echo "=================="

SUCCESS_COUNT=0
TOTAL_COUNT=5

# 체크 항목들
[ "$WORKFLOW_STATUS" = "success" ] && ((SUCCESS_COUNT++))
[ "$HTTP_CODE" = "200" ] && ((SUCCESS_COUNT++))
[ "$DEPLOYMENT_STATUS" = "True" ] && ((SUCCESS_COUNT++))
[ "$SYNC_STATUS" = "Synced" ] && ((SUCCESS_COUNT++))
[ -n "$CURRENT_COMMIT" ] && ((SUCCESS_COUNT++))

if [ $SUCCESS_COUNT -eq $TOTAL_COUNT ]; then
    echo -e "${GREEN}🎉 모든 검증 통과! ($SUCCESS_COUNT/$TOTAL_COUNT)${NC}"
    echo -e "${GREEN}✅ GitOps 배포가 성공적으로 완료되었습니다!${NC}"
elif [ $SUCCESS_COUNT -ge 3 ]; then
    echo -e "${YELLOW}⚠️ 부분 성공 ($SUCCESS_COUNT/$TOTAL_COUNT)${NC}"
    echo "일부 구성요소를 확인해주세요."
else
    echo -e "${RED}❌ 배포 검증 실패 ($SUCCESS_COUNT/$TOTAL_COUNT)${NC}"
    echo "배포 상태를 확인해주세요."
fi

echo -e "\n🔗 유용한 링크:"
echo "- GitHub Actions: https://github.com/JCLEE94/blacklist/actions"
echo "- ArgoCD: https://$ARGOCD_SERVER"
echo "- Production App: $APP_URL"
echo "- Docker Hub: https://hub.docker.com/r/jclee94/blacklist"

echo -e "\n✨ 배포 검증 완료!"