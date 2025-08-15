#!/bin/bash
# GitOps 배포 상태 모니터링 스크립트
# Usage: ./scripts/gitops-monitor.sh

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

APP_NAME="blacklist"
NAMESPACE="blacklist"

echo -e "${BLUE}🔍 GitOps 배포 상태 모니터링${NC}"
echo "=================================="

# 1. GitHub Actions 상태 확인
echo -e "\n${YELLOW}📋 1. GitHub Actions 파이프라인 상태${NC}"
if command -v gh &> /dev/null; then
    LATEST_RUN=$(gh api repos/jclee94/blacklist/actions/runs -q '.workflow_runs[0]')
    STATUS=$(echo "$LATEST_RUN" | jq -r '.conclusion')
    BRANCH=$(echo "$LATEST_RUN" | jq -r '.head_branch')
    URL=$(echo "$LATEST_RUN" | jq -r '.html_url')
    
    if [[ "$STATUS" == "success" ]]; then
        echo -e "  ✅ 최신 빌드: ${GREEN}성공${NC} (브랜치: $BRANCH)"
    else
        echo -e "  ❌ 최신 빌드: ${RED}$STATUS${NC} (브랜치: $BRANCH)"
        echo "  🔗 URL: $URL"
    fi
else
    echo -e "  ⚠️  GitHub CLI 설치 필요"
fi

# 2. Kubernetes 클러스터 상태 확인
echo -e "\n${YELLOW}☸️  2. Kubernetes 배포 상태${NC}"
if command -v kubectl &> /dev/null; then
    # 팟 상태 확인
    POD_STATUS=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name="$APP_NAME" --no-headers 2>/dev/null | head -1)
    if [[ -n "$POD_STATUS" ]]; then
        POD_NAME=$(echo "$POD_STATUS" | awk '{print $1}')
        READY=$(echo "$POD_STATUS" | awk '{print $2}')
        STATUS=$(echo "$POD_STATUS" | awk '{print $3}')
        AGE=$(echo "$POD_STATUS" | awk '{print $5}')
        
        if [[ "$STATUS" == "Running" && "$READY" == "1/1" ]]; then
            echo -e "  ✅ 팟 상태: ${GREEN}$STATUS${NC} ($READY) - $AGE"
        else
            echo -e "  ❌ 팟 상태: ${RED}$STATUS${NC} ($READY) - $AGE"
        fi
        
        # 최근 로그 확인 (에러만)
        echo -e "\n  📝 최근 로그 (에러/경고):"
        kubectl logs -n "$NAMESPACE" "$POD_NAME" --tail=20 | grep -E "(ERROR|WARN|Exception|Failed)" | head -5 || echo "    📗 에러 로그 없음"
    else
        echo -e "  ❌ 팟을 찾을 수 없음"
    fi
    
    # 서비스 상태 확인
    SERVICE_IP=$(kubectl get svc -n "$NAMESPACE" "$APP_NAME" -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo "N/A")
    echo -e "  🌐 서비스 IP: $SERVICE_IP"
    
    # Ingress 상태 확인
    INGRESS_HOST=$(kubectl get ingress -n "$NAMESPACE" "$APP_NAME" -o jsonpath='{.spec.rules[0].host}' 2>/dev/null || echo "N/A")
    echo -e "  🚪 Ingress Host: $INGRESS_HOST"
    
else
    echo -e "  ⚠️  kubectl 설치 필요"
fi

# 3. ArgoCD 애플리케이션 상태 확인
echo -e "\n${YELLOW}🎯 3. ArgoCD 애플리케이션 상태${NC}"
if command -v argocd &> /dev/null; then
    argocd app get "$APP_NAME" --output wide 2>/dev/null || echo "  ⚠️  ArgoCD CLI 설정 또는 애플리케이션 없음"
else
    echo -e "  ⚠️  ArgoCD CLI 설치 필요"
fi

# 4. 애플리케이션 헬스체크
echo -e "\n${YELLOW}🏥 4. 애플리케이션 헬스체크${NC}"
HEALTH_URL="http://localhost:32542/health"

if curl -sf "$HEALTH_URL" &>/dev/null; then
    HEALTH_DATA=$(curl -s "$HEALTH_URL" | jq -r '.status, .version' 2>/dev/null || echo "healthy unknown")
    STATUS=$(echo "$HEALTH_DATA" | head -1)
    VERSION=$(echo "$HEALTH_DATA" | tail -1)
    echo -e "  ✅ 애플리케이션: ${GREEN}$STATUS${NC} (v$VERSION)"
    
    # IP 통계 표시
    STATS=$(curl -s "$HEALTH_URL" | jq -r '.details | "총 IP: \(.total_ips), 활성: \(.active_ips), REGTECH: \(.regtech_count), SECUDIUM: \(.secudium_count)"' 2>/dev/null || echo "통계 정보 없음")
    echo -e "  📊 $STATS"
else
    echo -e "  ❌ 애플리케이션: ${RED}접근 불가${NC}"
    echo -e "     URL: $HEALTH_URL"
fi

# 5. 이미지 버전 정보
echo -e "\n${YELLOW}📦 5. 컨테이너 이미지 정보${NC}"
if command -v kubectl &> /dev/null && [[ -n "${POD_NAME:-}" ]]; then
    IMAGE=$(kubectl get pod -n "$NAMESPACE" "$POD_NAME" -o jsonpath='{.spec.containers[0].image}' 2>/dev/null || echo "N/A")
    echo -e "  🏷️  현재 이미지: $IMAGE"
    
    # 이미지 생성 시간 확인
    if command -v docker &> /dev/null; then
        IMAGE_DATE=$(docker inspect "$IMAGE" --format='{{.Created}}' 2>/dev/null | cut -d'T' -f1 || echo "N/A")
        echo -e "  📅 이미지 생성일: $IMAGE_DATE"
    fi
fi

echo -e "\n${BLUE}모니터링 완료 ✨${NC}"