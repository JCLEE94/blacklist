#!/bin/bash
# 배포 상태 확인 스크립트

echo "=== Blacklist 배포 상태 확인 ==="
echo "시간: $(date)"
echo ""

# 1. Kubernetes 상태
echo "1. Kubernetes 배포 상태"
echo "------------------------"
kubectl get pods -n blacklist 2>/dev/null || echo "Error: Cannot get pods"
echo ""
kubectl get deployment -n blacklist 2>/dev/null || echo "Error: Cannot get deployment"
echo ""

# 2. Service 상태
echo "2. Service 상태"
echo "---------------"
kubectl get svc -n blacklist 2>/dev/null || echo "Error: Cannot get services"
echo ""

# 3. 애플리케이션 헬스 체크
echo "3. 애플리케이션 헬스 체크"
echo "------------------------"
curl -s http://localhost:8541/health 2>/dev/null | python3 -m json.tool || echo "Error: Health check failed"
echo ""

# 4. ArgoCD 애플리케이션 상태
echo "4. ArgoCD 애플리케이션 상태"
echo "--------------------------"
kubectl get application blacklist -n argocd -o wide 2>/dev/null || echo "Error: Cannot get ArgoCD app"
echo ""

# 5. 최근 이벤트
echo "5. 최근 배포 이벤트"
echo "-------------------"
kubectl get events -n blacklist --sort-by='.lastTimestamp' | tail -10 2>/dev/null || echo "Error: Cannot get events"
echo ""

# 6. 리소스 사용량
echo "6. 리소스 사용량"
echo "----------------"
kubectl top pods -n blacklist 2>/dev/null || echo "Metrics not available"
echo ""

# 7. 로그 미리보기
echo "7. 최근 애플리케이션 로그"
echo "------------------------"
kubectl logs -n blacklist deployment/blacklist --tail=20 2>/dev/null || echo "Error: Cannot get logs"

echo ""
echo "=== 배포 상태 확인 완료 ===