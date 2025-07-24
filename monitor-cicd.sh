#!/bin/bash

echo "===== CI/CD 배포 모니터링 ====="
echo ""

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# 반복 모니터링
for i in {1..10}; do
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] 모니터링 중... (${i}/10)${NC}"
    
    # 현재 이미지 확인
    CURRENT_IMAGE=$(kubectl get deployment blacklist -n blacklist -o jsonpath='{.spec.template.spec.containers[0].image}')
    echo "현재 이미지: $CURRENT_IMAGE"
    
    # Pod 상태
    kubectl get pods -n blacklist | grep blacklist- | head -3
    
    # 버전 확인
    VERSION=$(curl -s http://192.168.50.110:32542/health 2>/dev/null | jq -r '.details.version' 2>/dev/null || echo "N/A")
    if [ "$VERSION" = "3.0.1-cicd-test" ]; then
        echo -e "${GREEN}✅ 새 버전이 배포되었습니다: $VERSION${NC}"
        echo ""
        echo "CI/CD 파이프라인 성공!"
        echo "- GitHub Actions → Docker Build → Registry Push → ArgoCD → Kubernetes"
        exit 0
    else
        echo "현재 버전: $VERSION"
    fi
    
    echo "---"
    sleep 15
done

echo -e "${RED}타임아웃: 새 버전이 아직 배포되지 않았습니다${NC}"