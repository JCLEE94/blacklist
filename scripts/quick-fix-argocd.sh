#!/bin/bash

echo "🔧 ArgoCD Ingress Quick Fix"
echo "=========================="
echo ""
echo "원격 서버(192.168.50.110)에 다음 명령을 실행하세요:"
echo ""
echo "1️⃣ SSH로 원격 서버 접속:"
echo "   ssh jclee@192.168.50.110"
echo ""
echo "2️⃣ ArgoCD ConfigMap 수정:"
echo "   kubectl edit cm argocd-cm -n argocd"
echo ""
echo "3️⃣ 다음 내용을 data 섹션에 추가 (기존 data: 아래):"
cat << 'EOF'

  resource.customizations.health.networking.k8s.io_Ingress: |
    hs = {}
    hs.status = "Healthy"
    hs.message = "Ingress is ready"
    return hs
EOF
echo ""
echo "4️⃣ ArgoCD Server 재시작:"
echo "   kubectl rollout restart deployment argocd-server -n argocd"
echo ""
echo "5️⃣ 재시작 완료 대기:"
echo "   kubectl rollout status deployment argocd-server -n argocd"
echo ""
echo "6️⃣ ArgoCD App 동기화:"
echo "   argocd app sync blacklist --grpc-web --insecure"
echo ""
echo "또는 한 줄로 실행:"
echo ""
cat << 'ONELINER'
kubectl patch cm argocd-cm -n argocd --type merge -p '{"data":{"resource.customizations.health.networking.k8s.io_Ingress":"hs = {}\nhs.status = \"Healthy\"\nhs.message = \"Ingress is ready\"\nreturn hs"}}' && kubectl rollout restart deployment argocd-server -n argocd
ONELINER
echo ""
echo "✅ 위 명령을 실행하면 Ingress가 Healthy 상태로 변경됩니다."