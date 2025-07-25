#!/bin/bash

echo "===== Blacklist Management System 종합 테스트 ====="
echo ""

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 결과 출력 함수
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

# 1. Kubernetes 리소스 확인
echo "1. Kubernetes 리소스 상태 확인"
echo "--------------------------------"

# Pod 상태
PODS_RUNNING=$(kubectl get pods -n blacklist -o json | jq '.items[] | select(.status.phase == "Running") | .metadata.name' | wc -l)
PODS_TOTAL=$(kubectl get pods -n blacklist -o json | jq '.items | length')
echo "Pod 상태: $PODS_RUNNING/$PODS_TOTAL Running"
[ "$PODS_RUNNING" -eq "$PODS_TOTAL" ]
print_result $? "모든 Pod 정상 실행 중"

# Service 상태
SERVICES=$(kubectl get svc -n blacklist --no-headers | wc -l)
echo "Service 개수: $SERVICES"
[ "$SERVICES" -gt 0 ]
print_result $? "Service 생성됨"

# Ingress 상태
INGRESS=$(kubectl get ingress -n blacklist --no-headers | wc -l)
echo "Ingress 개수: $INGRESS"
[ "$INGRESS" -gt 0 ]
print_result $? "Ingress 생성됨"

echo ""

# 2. ArgoCD 상태 확인
echo "2. ArgoCD GitOps 상태 확인"
echo "--------------------------------"

# ArgoCD Application 상태
ARGO_STATUS=$(kubectl get application blacklist -n argocd -o jsonpath='{.status.sync.status}' 2>/dev/null)
echo "ArgoCD 동기화 상태: $ARGO_STATUS"
[ "$ARGO_STATUS" = "Synced" ]
print_result $? "ArgoCD 동기화 완료"

# ArgoCD Health 상태
ARGO_HEALTH=$(kubectl get application blacklist -n argocd -o jsonpath='{.status.health.status}' 2>/dev/null)
echo "ArgoCD Health 상태: $ARGO_HEALTH"
[ "$ARGO_HEALTH" = "Healthy" ]
print_result $? "ArgoCD 애플리케이션 건강함"

echo ""

# 3. API 엔드포인트 테스트
echo "3. API 엔드포인트 테스트"
echo "--------------------------------"

# 기본 URL 설정
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
NODEPORT_URL="http://$NODE_IP:32542"
HTTPS_URL="https://blacklist.jclee.me"

# Health 체크
echo "Health 체크 테스트:"
curl -s "$NODEPORT_URL/health" > /tmp/health.json
HEALTH_STATUS=$(jq -r '.status' /tmp/health.json 2>/dev/null)
[ "$HEALTH_STATUS" = "healthy" ]
print_result $? "Health API 정상"

# 통계 API
echo "통계 API 테스트:"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$NODEPORT_URL/api/stats")
[ "$HTTP_CODE" = "200" ]
print_result $? "Stats API 응답 (HTTP $HTTP_CODE)"

# Collection 상태
echo "Collection 상태 테스트:"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$NODEPORT_URL/api/collection/status")
[ "$HTTP_CODE" = "200" ]
print_result $? "Collection Status API 응답 (HTTP $HTTP_CODE)"

# FortiGate API
echo "FortiGate External Connector 테스트:"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$NODEPORT_URL/api/fortigate")
[ "$HTTP_CODE" = "200" ]
print_result $? "FortiGate API 응답 (HTTP $HTTP_CODE)"

# 웹 대시보드
echo "웹 대시보드 테스트:"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$NODEPORT_URL/")
[ "$HTTP_CODE" = "200" ]
print_result $? "웹 대시보드 응답 (HTTP $HTTP_CODE)"

echo ""

# 4. HTTPS 접속 테스트
echo "4. HTTPS Ingress 테스트"
echo "--------------------------------"

# HTTPS Health 체크
echo "HTTPS Health 체크:"
HTTP_CODE=$(curl -k -s -o /dev/null -w "%{http_code}" "$HTTPS_URL/health")
[ "$HTTP_CODE" = "200" ]
print_result $? "HTTPS Health 응답 (HTTP $HTTP_CODE)"

# HTTPS 웹 대시보드
echo "HTTPS 웹 대시보드:"
HTTP_CODE=$(curl -k -s -o /dev/null -w "%{http_code}" "$HTTPS_URL/")
[ "$HTTP_CODE" = "200" ]
print_result $? "HTTPS 대시보드 응답 (HTTP $HTTP_CODE)"

echo ""

# 5. 데이터 수집 테스트
echo "5. 데이터 수집 기능 테스트"
echo "--------------------------------"

# Collection 활성화
echo "Collection 활성화 테스트:"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$NODEPORT_URL/api/collection/enable")
[ "$HTTP_CODE" = "200" ]
print_result $? "Collection 활성화 API 응답 (HTTP $HTTP_CODE)"

# 활성 IP 조회
echo "활성 IP 목록 조회:"
ACTIVE_IPS=$(curl -s "$NODEPORT_URL/api/blacklist/active" | wc -l)
echo "활성 IP 개수: $ACTIVE_IPS"
[ $? -eq 0 ]
print_result $? "활성 IP 조회 성공"

echo ""

# 6. 성능 테스트
echo "6. 성능 테스트"
echo "--------------------------------"

# 응답 시간 측정
echo "API 응답 시간 측정:"
TOTAL_TIME=0
for i in {1..10}; do
    TIME=$(curl -s -o /dev/null -w "%{time_total}" "$NODEPORT_URL/health")
    TOTAL_TIME=$(echo "$TOTAL_TIME + $TIME" | bc)
done
AVG_TIME=$(echo "scale=3; $TOTAL_TIME / 10" | bc)
echo "평균 응답 시간: ${AVG_TIME}초"
RESULT=$(echo "$AVG_TIME < 0.5" | bc)
[ "$RESULT" -eq 1 ]
print_result $? "응답 시간 양호 (<500ms)"

echo ""

# 7. 로그 확인
echo "7. 로그 상태 확인"
echo "--------------------------------"

# 최근 에러 로그
ERROR_COUNT=$(kubectl logs -n blacklist -l app.kubernetes.io/name=blacklist --tail=100 | grep -i error | wc -l)
echo "최근 100줄 중 에러 로그: $ERROR_COUNT개"
[ "$ERROR_COUNT" -lt 5 ]
print_result $? "에러 로그 정상 범위"

echo ""

# 8. 최종 결과
echo "===== 테스트 결과 요약 ====="
echo ""
echo "접속 가능 URL:"
echo "- NodePort: http://$NODE_IP:32542/"
echo "- HTTPS: https://blacklist.jclee.me/"
echo ""
echo "주요 API 엔드포인트:"
echo "- Health: /health"
echo "- Stats: /api/stats"
echo "- Collection: /api/collection/status"
echo "- FortiGate: /api/fortigate"
echo "- Active IPs: /api/blacklist/active"
echo ""

# 테스트 완료 시간
echo "테스트 완료: $(date '+%Y-%m-%d %H:%M:%S')"