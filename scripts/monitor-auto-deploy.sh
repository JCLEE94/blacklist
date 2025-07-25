#!/bin/bash

echo "===== 자동 배포 모니터링 ====="
echo ""

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 시작 시간 기록
START_TIME=$(date +%s)

echo -e "${BLUE}📊 실시간 모니터링 시작...${NC}"
echo ""

# 모니터링 루프
for i in {1..20}; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] 경과 시간: ${ELAPSED}초${NC}"
    
    # 1. ArgoCD 상태
    SYNC_STATUS=$(kubectl get application blacklist -n argocd -o jsonpath='{.status.sync.status}' 2>/dev/null || echo "Unknown")
    HEALTH_STATUS=$(kubectl get application blacklist -n argocd -o jsonpath='{.status.health.status}' 2>/dev/null || echo "Unknown")
    echo "ArgoCD: Sync=$SYNC_STATUS, Health=$HEALTH_STATUS"
    
    # 2. Pod 상태
    echo "Pods:"
    kubectl get pods -n blacklist | grep blacklist- | head -3
    
    # 3. 버전 확인
    VERSION=$(curl -s http://192.168.50.110:32542/health 2>/dev/null | jq -r '.details.version' 2>/dev/null || echo "N/A")
    echo "현재 버전: $VERSION"
    
    # 성공 체크
    if [ "$VERSION" = "3.0.2-auto-deploy" ]; then
        echo ""
        echo -e "${GREEN}✅ 자동 배포 성공!${NC}"
        echo "- 소요 시간: ${ELAPSED}초"
        echo "- 새 버전: $VERSION"
        echo "- 배포 프로세스: GitHub → Docker → ArgoCD → Kubernetes"
        echo ""
        echo "🎉 자동 배포 시스템이 정상 작동합니다!"
        exit 0
    fi
    
    echo "---"
    sleep 10
done

echo "⏱️ 타임아웃: 자동 배포가 완료되지 않았습니다."