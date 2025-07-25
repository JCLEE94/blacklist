#!/bin/bash

echo "🔧 Registry 인증 문제 해결 스크립트"
echo "================================="

# 네임스페이스 확인/생성
echo "📁 네임스페이스 확인..."
kubectl create namespace blacklist --dry-run=client -o yaml | kubectl apply -f -

# Registry Secret 생성
echo "🔐 Registry Secret 생성..."
kubectl create secret docker-registry regcred \
  --docker-server=registry.jclee.me \
  --docker-username=admin \
  --docker-password=bingogo1 \
  --namespace=blacklist \
  --dry-run=client -o yaml | kubectl apply -f -

# Deployment에 imagePullSecrets 추가 (있는 경우)
echo "🔄 기존 Deployment 업데이트..."
if kubectl get deployment blacklist -n blacklist &> /dev/null; then
    kubectl patch deployment blacklist -n blacklist -p '{"spec":{"template":{"spec":{"imagePullSecrets":[{"name":"regcred"}]}}}}'
else
    echo "⚠️  blacklist deployment가 없습니다. ArgoCD로 배포될 예정입니다."
fi

# 기존 Pod 재시작 (이미지 풀 재시도)
echo "🔄 기존 Pod 재시작..."
kubectl delete pods -l app=blacklist -n blacklist 2>/dev/null || echo "삭제할 Pod가 없습니다."

echo ""
echo "✅ Registry 인증 설정 완료!"
echo ""
echo "📊 상태 확인:"
kubectl get secret regcred -n blacklist
kubectl get pods -n blacklist

echo ""
echo "🔍 다음 명령어로 상태를 모니터링하세요:"
echo "kubectl get pods -n blacklist -w"
echo "kubectl logs -f deployment/blacklist -n blacklist"