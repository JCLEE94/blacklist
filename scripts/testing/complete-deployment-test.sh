#!/bin/bash

echo "🚀 완전한 GitOps 배포 검증 스크립트"
echo "=================================="

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 결과 추적
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 테스트 함수
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "\n${BLUE}🔍 Test $TOTAL_TESTS: $test_name${NC}"
    
    if eval "$test_command"; then
        echo -e "${GREEN}✅ PASS: $test_name${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}❌ FAIL: $test_name${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

echo -e "${YELLOW}Phase 1: 인프라 준비${NC}"
echo "========================"

# 1. Registry Secret 생성
run_test "네임스페이스 생성" "kubectl create namespace blacklist --dry-run=client -o yaml | kubectl apply -f -"

run_test "Registry Secret 생성" "kubectl create secret docker-registry regcred \
  --docker-server=registry.jclee.me \
  --docker-username=admin \
  --docker-password=bingogo1 \
  --namespace=blacklist \
  --dry-run=client -o yaml | kubectl apply -f -"

# 2. Registry 연결 테스트
run_test "Registry 접속 테스트" "curl -s -u admin:bingogo1 https://registry.jclee.me/v2/_catalog | jq . > /dev/null"

# 3. ChartMuseum 연결 테스트
run_test "ChartMuseum 접속 테스트" "curl -s -u admin:bingogo1 https://charts.jclee.me/api/charts | jq . > /dev/null"

echo -e "\n${YELLOW}Phase 2: ArgoCD 배포${NC}"
echo "====================="

# 4. ArgoCD Application 생성
run_test "ArgoCD Application 생성" "kubectl apply -f k8s-gitops/argocd/blacklist-app-chartrepo.yaml"

# 5. Application 상태 확인
sleep 10
run_test "ArgoCD Application 존재 확인" "kubectl get application blacklist -n argocd"

echo -e "\n${YELLOW}Phase 3: 배포 상태 검증${NC}"
echo "========================"

# Pod 준비 대기 (최대 5분)
echo -e "${BLUE}⏳ Pod 준비 대기 중 (최대 5분)...${NC}"
for i in {1..30}; do
    if kubectl get pods -n blacklist | grep -q "Running"; then
        echo -e "${GREEN}✅ Pod가 Running 상태입니다!${NC}"
        break
    elif kubectl get pods -n blacklist | grep -q "ImagePullBackOff\|ErrImagePull"; then
        echo -e "${RED}❌ 이미지 풀 오류 발생${NC}"
        kubectl describe pods -n blacklist | grep -A 5 "Events:"
        break
    fi
    echo "대기 중... ($i/30)"
    sleep 10
done

# 6. Pod 상태 확인
run_test "Pod Running 상태 확인" "kubectl get pods -n blacklist | grep -q Running"

# 7. Service 확인
run_test "Service 존재 확인" "kubectl get service blacklist -n blacklist"

# 8. NodePort 접근 테스트
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[0].address}')
SERVICE_URL="http://$NODE_IP:32452"

echo -e "\n${YELLOW}Phase 4: 애플리케이션 테스트${NC}"
echo "==========================="

# 서비스 준비 대기
echo -e "${BLUE}⏳ 서비스 준비 대기 중...${NC}"
sleep 30

# 9. Health Check
run_test "Health Check 테스트" "curl -f $SERVICE_URL/health"

# 10. API 엔드포인트 테스트
run_test "API Stats 테스트" "curl -f $SERVICE_URL/api/stats"

run_test "Test 엔드포인트 테스트" "curl -f $SERVICE_URL/test"

run_test "Blacklist API 테스트" "curl -f $SERVICE_URL/api/blacklist/active"

echo -e "\n${YELLOW}Phase 5: 성능 및 부하 테스트${NC}"
echo "============================"

# 11. 기본 성능 테스트
echo -e "${BLUE}⚡ 기본 성능 테스트 (10회 요청)${NC}"
total_time=0
for i in {1..10}; do
    start_time=$(date +%s.%N)
    curl -s "$SERVICE_URL/health" > /dev/null
    end_time=$(date +%s.%N)
    request_time=$(echo "$end_time - $start_time" | bc -l)
    total_time=$(echo "$total_time + $request_time" | bc -l)
    echo "Request $i: ${request_time}s"
done

avg_time=$(echo "scale=3; $total_time / 10" | bc -l)
echo -e "${GREEN}평균 응답 시간: ${avg_time}s${NC}"

# 성능 기준 확인 (1초 이내)
run_test "성능 테스트 (< 1초)" "[ $(echo \"$avg_time < 1.0\" | bc -l) -eq 1 ]"

echo -e "\n${YELLOW}Phase 6: GitOps 검증${NC}"
echo "==================="

# 12. ArgoCD Application 상태
run_test "ArgoCD Sync 상태 확인" "kubectl get application blacklist -n argocd -o jsonpath='{.status.sync.status}' | grep -q Synced"

run_test "ArgoCD Health 상태 확인" "kubectl get application blacklist -n argocd -o jsonpath='{.status.health.status}' | grep -q Healthy"

echo -e "\n${YELLOW}Phase 7: 리소스 상태 확인${NC}"
echo "======================="

# 13. 전체 리소스 상태
echo -e "${BLUE}📊 전체 리소스 상태:${NC}"
kubectl get all -n blacklist

echo -e "\n${BLUE}📊 ArgoCD Application 상태:${NC}"
kubectl get application blacklist -n argocd -o yaml | grep -A 10 "status:"

echo -e "\n${BLUE}📊 최근 이벤트:${NC}"
kubectl get events -n blacklist --sort-by='.lastTimestamp' | tail -5

echo -e "\n${YELLOW}=== 최종 결과 ===${NC}"
echo "총 테스트: $TOTAL_TESTS"
echo -e "${GREEN}성공: $PASSED_TESTS${NC}"
echo -e "${RED}실패: $FAILED_TESTS${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${GREEN}🎉 모든 테스트 통과! GitOps 배포가 성공적으로 완료되었습니다!${NC}"
    echo -e "\n${BLUE}🔗 접속 정보:${NC}"
    echo "애플리케이션 URL: $SERVICE_URL"
    echo "Health Check: $SERVICE_URL/health"
    echo "API Stats: $SERVICE_URL/api/stats"
    echo "ArgoCD Dashboard: https://argo.jclee.me"
    
    echo -e "\n${BLUE}📈 모니터링 명령어:${NC}"
    echo "kubectl logs -f deployment/blacklist -n blacklist"
    echo "kubectl get application blacklist -n argocd -w"
    echo "kubectl top pods -n blacklist"
    
    exit 0
else
    echo -e "\n${RED}❌ 일부 테스트가 실패했습니다. 로그를 확인하세요.${NC}"
    echo -e "\n${BLUE}🔍 디버깅 명령어:${NC}"
    echo "kubectl describe pods -n blacklist"
    echo "kubectl logs -l app=blacklist -n blacklist"
    echo "kubectl get events -n blacklist --sort-by='.lastTimestamp'"
    
    exit 1
fi