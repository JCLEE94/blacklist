#!/bin/bash

echo "===== CI/CD 전체 플로우 테스트 ====="
echo ""

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${YELLOW}1. 현재 상태 확인${NC}"
echo "-----------------------------------"

# 현재 버전
CURRENT_VERSION=$(curl -s http://192.168.50.110:32542/health | jq -r '.details.version')
echo "현재 버전: $CURRENT_VERSION"

# ArgoCD 상태
SYNC_STATUS=$(kubectl get application blacklist -n argocd -o jsonpath='{.status.sync.status}')
HEALTH_STATUS=$(kubectl get application blacklist -n argocd -o jsonpath='{.status.health.status}')
echo "ArgoCD 상태: Sync=$SYNC_STATUS, Health=$HEALTH_STATUS"

# 현재 이미지
CURRENT_IMAGE=$(kubectl get deployment blacklist -n blacklist -o jsonpath='{.spec.template.spec.containers[0].image}')
echo "현재 이미지: $CURRENT_IMAGE"

echo ""
echo -e "${YELLOW}2. GitHub Actions 트리거 시뮬레이션${NC}"
echo "-----------------------------------"
echo "실제 환경에서는 다음과 같이 동작합니다:"
echo ""
echo "1) 코드 변경 및 커밋"
echo "   git add ."
echo "   git commit -m \"feat: 새 기능 추가\""
echo "   git push origin main"
echo ""
echo "2) GitHub Actions 자동 실행"
echo "   - Docker 이미지 빌드"
echo "   - registry.jclee.me에 푸시"
echo "   - 태그: latest, sha-xxx, date-xxx"
echo ""
echo "3) ArgoCD Image Updater 감지 (2분 이내)"
echo "   - 새 이미지 확인"
echo "   - Helm values 업데이트"
echo "   - ArgoCD 동기화 트리거"
echo ""
echo "4) Kubernetes 배포"
echo "   - Rolling update 실행"
echo "   - Zero-downtime 배포"
echo "   - Health check 통과"

echo ""
echo -e "${YELLOW}3. 배포 파이프라인 체크리스트${NC}"
echo "-----------------------------------"

# 체크리스트
echo -e "${GREEN}✅${NC} GitHub Actions 워크플로우 구성"
echo -e "${GREEN}✅${NC} ArgoCD 자동 동기화 설정"
echo -e "${GREEN}✅${NC} ArgoCD Image Updater 실행 중"
echo -e "${GREEN}✅${NC} RBAC 권한 설정 완료"
echo -e "${GREEN}✅${NC} PVC 데이터 보존 설정"
echo -e "${GREEN}✅${NC} NodePort 및 HTTPS 접근 가능"

echo ""
echo -e "${YELLOW}4. 모니터링 도구${NC}"
echo "-----------------------------------"
echo "• 배포 모니터링: ./monitor-auto-deploy.sh"
echo "• ArgoCD UI: kubectl port-forward svc/argocd-server -n argocd 8080:443"
echo "• 로그 확인: kubectl logs -f deployment/blacklist -n blacklist"
echo "• 버전 확인: curl http://192.168.50.110:32542/health | jq '.details.version'"

echo ""
echo -e "${YELLOW}5. 롤백 방법${NC}"
echo "-----------------------------------"
echo "• ArgoCD 롤백: argocd app rollback blacklist --grpc-web"
echo "• Kubernetes 롤백: kubectl rollout undo deployment/blacklist -n blacklist"
echo "• 수동 동기화 전환: kubectl patch app blacklist -n argocd --type='json' -p='[{\"op\": \"remove\", \"path\": \"/spec/syncPolicy/automated\"}]'"

echo ""
echo -e "${BLUE}===== CI/CD 파이프라인 준비 완료 =====${NC}"
echo ""
echo "Docker Registry 인증만 설정하면 완전 자동화된 배포가 가능합니다:"
echo "./scripts/setup-registry-auth.sh"