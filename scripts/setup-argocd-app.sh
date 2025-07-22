#!/bin/bash
# ArgoCD 애플리케이션 설정 스크립트

set -e

echo "=== ArgoCD 애플리케이션 설정 ==="
echo ""

# 1. ArgoCD 네임스페이스 확인
echo "1. ArgoCD 네임스페이스 확인"
if kubectl get namespace argocd &>/dev/null; then
    echo "✅ ArgoCD 네임스페이스 존재"
else
    echo "❌ ArgoCD 네임스페이스 없음"
    echo "ArgoCD 설치가 필요합니다."
    exit 1
fi
echo ""

# 2. 기존 애플리케이션 삭제 (있는 경우)
echo "2. 기존 애플리케이션 확인"
if kubectl get application blacklist -n argocd &>/dev/null; then
    echo "기존 애플리케이션 발견, 삭제 중..."
    kubectl delete application blacklist -n argocd --wait=false
    sleep 5
fi
echo ""

# 3. HTTPS 버전 애플리케이션 생성
echo "3. ArgoCD 애플리케이션 생성 (HTTPS)"
kubectl apply -f k8s-gitops/argocd/blacklist-app-https.yaml

echo ""
echo "4. 애플리케이션 상태 확인"
sleep 3
kubectl get application blacklist -n argocd

echo ""
echo "5. 수동 동기화 (초기 설정)"
if command -v argocd &>/dev/null; then
    argocd app sync blacklist --grpc-web || echo "ArgoCD CLI 없음"
else
    echo "ArgoCD CLI가 없습니다. 웹 UI에서 수동 동기화 필요"
fi

echo ""
echo "=== 설정 완료 ==="
echo ""
echo "다음 단계:"
echo "1. GitHub Actions 확인: https://github.com/JCLEE94/blacklist/actions"
echo "2. ArgoCD 웹 UI에서 애플리케이션 상태 확인"
echo "3. 테스트: ./scripts/test-simple-cicd.sh"