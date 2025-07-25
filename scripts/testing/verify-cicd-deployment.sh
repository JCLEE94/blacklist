#!/bin/bash

echo "===== CI/CD 배포 검증 스크립트 ====="
echo ""

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 검증 결과 추적
PASS_COUNT=0
FAIL_COUNT=0
TOTAL_TESTS=0

# 테스트 함수
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_result="$3"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "${BLUE}[$TOTAL_TESTS] $test_name${NC}"
    
    result=$(eval "$test_command" 2>&1)
    if [[ "$result" == *"$expected_result"* ]]; then
        echo -e "${GREEN}✅ PASS${NC}"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo -e "${RED}❌ FAIL${NC}"
        echo "Expected: $expected_result"
        echo "Got: $result"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    echo ""
}

echo -e "${YELLOW}1. GitHub Actions 워크플로우 검증${NC}"
echo "-----------------------------------"

# GitHub Actions 파일 존재 확인
run_test "GitHub Actions 워크플로우 파일 존재" \
    "ls -la .github/workflows/auto-deploy.yaml | grep -c auto-deploy.yaml" \
    "1"

# 워크플로우 구성 확인
run_test "Docker buildx 설정 확인" \
    "grep -c 'docker/setup-buildx-action@v2' .github/workflows/auto-deploy.yaml" \
    "1"

run_test "멀티 태그 전략 확인" \
    "grep -c 'registry.jclee.me/jclee94/blacklist:latest' .github/workflows/auto-deploy.yaml" \
    "1"

echo -e "${YELLOW}2. ArgoCD 설정 검증${NC}"
echo "-----------------------------------"

# ArgoCD 애플리케이션 상태
run_test "ArgoCD 애플리케이션 존재" \
    "kubectl get application blacklist -n argocd -o jsonpath='{.metadata.name}'" \
    "blacklist"

run_test "ArgoCD 자동 동기화 활성화" \
    "kubectl get application blacklist -n argocd -o jsonpath='{.spec.syncPolicy.automated.prune}'" \
    "true"

run_test "Self-heal 활성화" \
    "kubectl get application blacklist -n argocd -o jsonpath='{.spec.syncPolicy.automated.selfHeal}'" \
    "true"

run_test "Helm 차트 자동 업데이트" \
    "kubectl get application blacklist -n argocd -o jsonpath='{.spec.source.targetRevision}'" \
    "*"

echo -e "${YELLOW}3. ArgoCD Image Updater 검증${NC}"
echo "-----------------------------------"

# Image Updater 상태
run_test "Image Updater 실행 중" \
    "kubectl get pods -n argocd -l app.kubernetes.io/name=argocd-image-updater -o jsonpath='{.items[0].status.phase}'" \
    "Running"

run_test "Image Updater 어노테이션" \
    "kubectl get application blacklist -n argocd -o jsonpath='{.metadata.annotations.argocd-image-updater\.argoproj\.io/image-list}' | grep -c 'registry.jclee.me/jclee94/blacklist'" \
    "1"

run_test "Update Strategy 설정" \
    "kubectl get application blacklist -n argocd -o jsonpath='{.metadata.annotations.argocd-image-updater\.argoproj\.io/blacklist\.update-strategy}'" \
    "newest-build"

echo -e "${YELLOW}4. Kubernetes 리소스 검증${NC}"
echo "-----------------------------------"

# Deployment 상태
run_test "Deployment 실행 중" \
    "kubectl get deployment blacklist -n blacklist -o jsonpath='{.status.conditions[?(@.type==\"Available\")].status}'" \
    "True"

# PVC 상태
run_test "Data PVC 바운드" \
    "kubectl get pvc blacklist-data-pvc -n blacklist -o jsonpath='{.status.phase}'" \
    "Bound"

run_test "Logs PVC 바운드" \
    "kubectl get pvc blacklist-logs-pvc -n blacklist -o jsonpath='{.status.phase}'" \
    "Bound"

# Secret 존재
run_test "Docker Registry Secret 존재" \
    "kubectl get secret regcred -n blacklist -o jsonpath='{.type}'" \
    "kubernetes.io/dockerconfigjson"

echo -e "${YELLOW}5. RBAC 권한 검증${NC}"
echo "-----------------------------------"

run_test "Image Updater RBAC Role" \
    "kubectl get role argocd-image-updater-secrets -n blacklist -o jsonpath='{.metadata.name}'" \
    "argocd-image-updater-secrets"

run_test "Image Updater RoleBinding" \
    "kubectl get rolebinding argocd-image-updater-secrets -n blacklist -o jsonpath='{.metadata.name}'" \
    "argocd-image-updater-secrets"

echo -e "${YELLOW}6. 서비스 접근성 검증${NC}"
echo "-----------------------------------"

# NodePort 서비스
run_test "NodePort 서비스 활성화" \
    "kubectl get svc blacklist-nodeport -n blacklist -o jsonpath='{.spec.ports[0].nodePort}'" \
    "32542"

# API 응답
run_test "Health API 응답" \
    "curl -s http://192.168.50.110:32542/health | jq -r '.status'" \
    "healthy"

# 현재 버전
CURRENT_VERSION=$(curl -s http://192.168.50.110:32542/health | jq -r '.details.version')
echo -e "${BLUE}현재 배포된 버전: $CURRENT_VERSION${NC}"

echo -e "${YELLOW}7. 배포 스크립트 검증${NC}"
echo "-----------------------------------"

run_test "deploy.sh 스크립트 존재" \
    "test -x deploy.sh && echo 'executable'" \
    "executable"

run_test "monitor-auto-deploy.sh 스크립트 존재" \
    "test -x monitor-auto-deploy.sh && echo 'executable'" \
    "executable"

run_test "setup-registry-auth.sh 스크립트 존재" \
    "test -x scripts/setup-registry-auth.sh && echo 'executable'" \
    "executable"

echo ""
echo "===== 검증 결과 요약 ====="
echo -e "총 테스트: $TOTAL_TESTS"
echo -e "${GREEN}성공: $PASS_COUNT${NC}"
echo -e "${RED}실패: $FAIL_COUNT${NC}"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}✅ CI/CD 파이프라인이 완벽하게 구성되었습니다!${NC}"
    echo ""
    echo "다음 단계:"
    echo "1. Docker Registry 인증 설정: ./scripts/setup-registry-auth.sh"
    echo "2. GitHub Secrets 추가"
    echo "3. 코드 변경 후 git push로 자동 배포 테스트"
else
    echo -e "${RED}⚠️  일부 구성이 누락되었습니다. 위의 실패 항목을 확인하세요.${NC}"
fi

echo ""
echo "===== 상세 정보 ====="
echo ""
echo "ArgoCD 애플리케이션 상태:"
kubectl get application blacklist -n argocd | grep blacklist
echo ""
echo "최근 Image Updater 로그:"
kubectl logs -n argocd deployment/argocd-image-updater --tail=5
echo ""
echo "현재 실행 중인 Pod:"
kubectl get pods -n blacklist | grep blacklist-