#!/bin/bash
# 배포 검증 체크리스트 스크립트 - Blacklist Management System
set -e

echo "🔍 Blacklist Management System - 배포 검증 체크리스트"
echo "====================================================="

# 설정값
APP_NAME="blacklist"
NAMESPACE="${NAMESPACE:-blacklist}"
GITHUB_ORG="${GITHUB_ORG:-JCLEE94}"
REGISTRY_URL="${REGISTRY_URL:-registry.jclee.me}"
ARGOCD_URL="${ARGOCD_URL:-argo.jclee.me}"
CHARTMUSEUM_URL="${CHARTMUSEUM_URL:-https://charts.jclee.me}"
NODEPORT="${NODEPORT:-32542}"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 결과 추적
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# 체크 함수
check_status() {
    local description="$1"
    local command="$2"
    local expected_result="$3"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    echo -e "${BLUE}[$TOTAL_CHECKS] 확인 중: $description${NC}"
    
    if eval "$command" > /tmp/check_output.txt 2>&1; then
        if [ -n "$expected_result" ]; then
            if grep -q "$expected_result" /tmp/check_output.txt; then
                echo -e "${GREEN}✅ PASS: $description${NC}"
                PASSED_CHECKS=$((PASSED_CHECKS + 1))
                return 0
            else
                echo -e "${RED}❌ FAIL: $description (결과 불일치)${NC}"
                echo "Expected: $expected_result"
                echo "Got: $(cat /tmp/check_output.txt)"
                FAILED_CHECKS=$((FAILED_CHECKS + 1))
                return 1
            fi
        else
            echo -e "${GREEN}✅ PASS: $description${NC}"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            return 0
        fi
    else
        echo -e "${RED}❌ FAIL: $description${NC}"
        echo "Error: $(cat /tmp/check_output.txt)"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

# 체크 함수 (URL 전용)
check_url() {
    local description="$1"
    local url="$2"
    local expected_status="${3:-200}"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    echo -e "${BLUE}[$TOTAL_CHECKS] URL 확인: $description${NC}"
    echo "   URL: $url"
    
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" "$url" 2>/dev/null || echo "HTTPSTATUS:000")
    http_status=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    
    if [ "$http_status" = "$expected_status" ]; then
        echo -e "${GREEN}✅ PASS: $description (HTTP $http_status)${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo -e "${RED}❌ FAIL: $description (HTTP $http_status, expected $expected_status)${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

echo ""
echo "🏁 배포 검증 시작..."

# 1. GitHub Actions 워크플로우 상태 확인
echo -e "\n${YELLOW}=== 1. GitHub Actions 워크플로우 상태 ===${NC}"
if command -v gh >/dev/null 2>&1; then
    check_status "GitHub CLI 설치됨" "gh --version" "gh version"
    check_status "GitHub 인증 상태" "gh auth status" "Logged in to github.com"
    
    echo -e "${BLUE}최근 워크플로우 실행 내역:${NC}"
    gh run list --limit 3 2>/dev/null || echo "워크플로우 실행 내역을 가져올 수 없습니다."
else
    echo -e "${YELLOW}⚠ GitHub CLI가 설치되지 않음 - 수동 확인 필요${NC}"
fi

# 2. Docker 이미지 푸시 확인
echo -e "\n${YELLOW}=== 2. Docker 이미지 Registry 확인 ===${NC}"
if command -v curl >/dev/null 2>&1; then
    # Registry 접근성 확인
    check_url "Registry 접근성" "http://${REGISTRY_URL}/v2/" "200"
    
    # 이미지 태그 목록 확인
    REGISTRY_AUTH=""
    if [ -n "$REGISTRY_USERNAME" ] && [ -n "$REGISTRY_PASSWORD" ]; then
        REGISTRY_AUTH="-u ${REGISTRY_USERNAME}:${REGISTRY_PASSWORD}"
    fi
    
    echo -e "${BLUE}최근 이미지 태그 확인:${NC}"
    curl -s $REGISTRY_AUTH "http://${REGISTRY_URL}/v2/${GITHUB_ORG}/${APP_NAME}/tags/list" 2>/dev/null | \
        python3 -m json.tool 2>/dev/null || echo "이미지 태그 목록을 가져올 수 없습니다."
else
    echo -e "${YELLOW}⚠ curl이 설치되지 않음 - Registry 확인 불가${NC}"
fi

# 3. Helm 차트 업로드 확인
echo -e "\n${YELLOW}=== 3. Helm 차트 ChartMuseum 확인 ===${NC}"
if command -v curl >/dev/null 2>&1; then
    # ChartMuseum 접근성 확인
    check_url "ChartMuseum 접근성" "${CHARTMUSEUM_URL}/health" "200"
    
    # 차트 목록 확인
    CHART_AUTH=""
    if [ -n "$CHARTMUSEUM_USERNAME" ] && [ -n "$CHARTMUSEUM_PASSWORD" ]; then
        CHART_AUTH="-u ${CHARTMUSEUM_USERNAME}:${CHARTMUSEUM_PASSWORD}"
    fi
    
    echo -e "${BLUE}차트 버전 확인:${NC}"
    curl -s $CHART_AUTH "${CHARTMUSEUM_URL}/api/charts/${APP_NAME}" 2>/dev/null | \
        python3 -m json.tool 2>/dev/null || echo "차트 목록을 가져올 수 없습니다."
else
    echo -e "${YELLOW}⚠ curl이 설치되지 않음 - ChartMuseum 확인 불가${NC}"
fi

# 4. ArgoCD 애플리케이션 동기화 상태 확인
echo -e "\n${YELLOW}=== 4. ArgoCD 애플리케이션 상태 ===${NC}"
if command -v argocd >/dev/null 2>&1; then
    # ArgoCD 로그인 (환경변수 기반)
    if [ -n "$ARGOCD_URL" ] && [ -n "$ARGOCD_USERNAME" ] && [ -n "$ARGOCD_PASSWORD" ]; then
        echo -e "${BLUE}ArgoCD 로그인 중...${NC}"
        argocd login $ARGOCD_URL --username $ARGOCD_USERNAME --password $ARGOCD_PASSWORD --insecure --grpc-web > /dev/null 2>&1 || \
            echo -e "${YELLOW}⚠ ArgoCD 로그인 실패 - 수동 로그인 필요${NC}"
        
        APP_FULL_NAME="${APP_NAME}-${NAMESPACE}"
        check_status "ArgoCD 애플리케이션 존재" "argocd app get $APP_FULL_NAME --grpc-web" "Name:"
        
        echo -e "${BLUE}ArgoCD 애플리케이션 상태:${NC}"
        argocd app get $APP_FULL_NAME --grpc-web 2>/dev/null || echo "애플리케이션 상태를 가져올 수 없습니다."
    else
        echo -e "${YELLOW}⚠ ArgoCD 인증 정보 없음 - 수동 확인 필요${NC}"
    fi
else
    echo -e "${YELLOW}⚠ ArgoCD CLI가 설치되지 않음 - 수동 확인 필요${NC}"
fi

# 5. Kubernetes 리소스 확인
echo -e "\n${YELLOW}=== 5. Kubernetes 리소스 상태 ===${NC}"
if command -v kubectl >/dev/null 2>&1; then
    check_status "kubectl 연결 확인" "kubectl cluster-info" "is running"
    check_status "네임스페이스 존재" "kubectl get namespace $NAMESPACE" "$NAMESPACE"
    check_status "Deployment 상태" "kubectl get deployment $APP_NAME -n $NAMESPACE" "blacklist"
    check_status "Pod 실행 상태" "kubectl get pods -n $NAMESPACE -l app=$APP_NAME" "Running"
    check_status "Service 존재" "kubectl get service $APP_NAME -n $NAMESPACE" "$APP_NAME"
    
    echo -e "${BLUE}Pod 상세 상태:${NC}"
    kubectl get pods -n $NAMESPACE -l app=$APP_NAME -o wide 2>/dev/null || echo "Pod 정보를 가져올 수 없습니다."
    
    echo -e "${BLUE}Service 상세 정보:${NC}"
    kubectl get svc -n $NAMESPACE -l app=$APP_NAME -o wide 2>/dev/null || echo "Service 정보를 가져올 수 없습니다."
else
    echo -e "${YELLOW}⚠ kubectl이 설치되지 않음 - Kubernetes 확인 불가${NC}"
fi

# 6. 애플리케이션 헬스체크
echo -e "\n${YELLOW}=== 6. 애플리케이션 헬스체크 ===${NC}"

# NodePort로 접근 (Kubernetes 클러스터 내부)
if command -v kubectl >/dev/null 2>&1; then
    NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}' 2>/dev/null || echo "localhost")
    HEALTH_URL="http://${NODE_IP}:${NODEPORT}/health"
    
    check_url "헬스체크 엔드포인트" "$HEALTH_URL" "200"
    
    # 추가 API 엔드포인트 테스트
    api_endpoints=(
        "/api/stats"
        "/api/collection/status"
        "/api/blacklist/active"
        "/api/fortigate"
    )
    
    echo -e "${BLUE}API 엔드포인트 테스트:${NC}"
    for endpoint in "${api_endpoints[@]}"; do
        check_url "API $endpoint" "http://${NODE_IP}:${NODEPORT}${endpoint}" "200"
    done
else
    echo -e "${YELLOW}⚠ kubectl이 없어 NodePort 확인 불가${NC}"
    
    # 외부 접근 시도
    if [ -n "$EXTERNAL_URL" ]; then
        check_url "외부 헬스체크" "${EXTERNAL_URL}/health" "200"
    else
        echo -e "${YELLOW}⚠ EXTERNAL_URL 환경변수 없음${NC}"
    fi
fi

# 7. 성능 및 로그 확인
echo -e "\n${YELLOW}=== 7. 성능 및 로그 확인 ===${NC}"
if command -v kubectl >/dev/null 2>&1; then
    echo -e "${BLUE}최근 애플리케이션 로그 (마지막 20줄):${NC}"
    kubectl logs -l app=$APP_NAME -n $NAMESPACE --tail=20 2>/dev/null || echo "로그를 가져올 수 없습니다."
    
    echo -e "\n${BLUE}리소스 사용량:${NC}"
    kubectl top pods -n $NAMESPACE -l app=$APP_NAME 2>/dev/null || echo "리소스 사용량을 가져올 수 없습니다 (metrics-server 필요)."
fi

# 8. 보안 및 설정 확인
echo -e "\n${YELLOW}=== 8. 보안 및 설정 확인 ===${NC}"
if command -v kubectl >/dev/null 2>&1; then
    check_status "Registry Secret 존재" "kubectl get secret regcred -n $NAMESPACE" "regcred"
    check_status "App Secrets 존재" "kubectl get secret ${APP_NAME}-secrets -n $NAMESPACE" "${APP_NAME}-secrets"
    check_status "ConfigMap 존재" "kubectl get configmap ${APP_NAME}-config -n $NAMESPACE" "${APP_NAME}-config"
    
    echo -e "${BLUE}Security Context 확인:${NC}"
    kubectl get pods -n $NAMESPACE -l app=$APP_NAME -o jsonpath='{.items[0].spec.securityContext}' 2>/dev/null | \
        python3 -m json.tool 2>/dev/null || echo "Security Context 정보를 가져올 수 없습니다."
fi

# 결과 요약
echo -e "\n${YELLOW}========================================${NC}"
echo -e "${YELLOW}           검증 결과 요약               ${NC}"
echo -e "${YELLOW}========================================${NC}"

echo -e "총 검사 항목: ${BLUE}$TOTAL_CHECKS${NC}"
echo -e "통과: ${GREEN}$PASSED_CHECKS${NC}"
echo -e "실패: ${RED}$FAILED_CHECKS${NC}"

if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "\n${GREEN}🎉 모든 검증 항목이 통과했습니다!${NC}"
    echo -e "${GREEN}✅ 배포가 성공적으로 완료되었습니다.${NC}"
    
    echo -e "\n${BLUE}🔗 접속 정보:${NC}"
    echo -e "   Health Check: http://blacklist.jclee.me:${NODEPORT}/health"
    echo -e "   Dashboard: http://blacklist.jclee.me:${NODEPORT}/"
    echo -e "   API Docs: http://blacklist.jclee.me:${NODEPORT}/api/stats"
    echo -e "   ArgoCD: https://${ARGOCD_URL}/applications/${APP_NAME}-${NAMESPACE}"
    
    exit 0
else
    echo -e "\n${RED}❌ $FAILED_CHECKS개 항목에서 문제가 발견되었습니다.${NC}"
    echo -e "${YELLOW}🔧 문제 해결 후 다시 검증해주세요.${NC}"
    
    echo -e "\n${BLUE}💡 일반적인 해결 방법:${NC}"
    echo -e "   1. GitHub Actions 워크플로우 로그 확인"
    echo -e "   2. ArgoCD 애플리케이션 Sync 상태 확인"
    echo -e "   3. Kubernetes Pod 로그 확인: kubectl logs -f -l app=${APP_NAME} -n ${NAMESPACE}"
    echo -e "   4. Registry 및 ChartMuseum 접근 권한 확인"
    echo -e "   5. Secrets 및 ConfigMap 설정 확인"
    
    exit 1
fi

# 임시 파일 정리
rm -f /tmp/check_output.txt