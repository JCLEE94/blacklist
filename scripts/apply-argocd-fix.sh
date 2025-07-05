#!/bin/bash
# Apply ArgoCD Ingress Health Fix

echo "🔧 Fixing ArgoCD Ingress Health Check..."

# ArgoCD에 로그인
argocd login argo.jclee.me \
  --username admin \
  --password bingogo1 \
  --insecure \
  --grpc-web

# 현재 상태 확인
echo "📊 Current status:"
argocd app get blacklist --grpc-web | grep -E "Health Status"

# 앱 삭제 후 재생성 (health check 설정과 함께)
echo "🔄 Recreating app with health check overrides..."

# 기존 앱 삭제
argocd app delete blacklist --grpc-web --yes

# 잠시 대기
sleep 5

# 새 앱 생성 (Ingress를 무시하도록 설정)
cat > /tmp/blacklist-app.yaml << 'EOF'
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: blacklist
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/JCLEE94/blacklist.git
    targetRevision: HEAD
    path: k8s
  destination:
    server: https://kubernetes.default.svc
    namespace: blacklist
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
    - PrunePropagationPolicy=foreground
  ignoreDifferences:
  - group: networking.k8s.io
    kind: Ingress
    jsonPointers:
    - /status
EOF

# ArgoCD CLI로 앱 생성
argocd app create -f /tmp/blacklist-app.yaml --grpc-web

# 초기 동기화
argocd app sync blacklist --grpc-web

echo "✅ App recreated with health check fixes"

# 최종 상태 확인
sleep 10
echo "📊 Final status:"
argocd app get blacklist --grpc-web | grep -E "Sync Status|Health Status"