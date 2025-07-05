#!/bin/bash
# Fix ArgoCD Health Check for Ingress

echo "🔧 Fixing ArgoCD Ingress Health Check..."

# ArgoCD 로그인
argocd login argo.jclee.me \
  --username admin \
  --password bingogo1 \
  --insecure \
  --grpc-web

# Ingress 리소스에 대한 health check 비활성화
argocd app set blacklist \
  --resource-override-health Ingress:networking.k8s.io:* \
  --grpc-web

# 또는 특정 Ingress만 건너뛰기
argocd app set blacklist \
  --resource-override-ignoreDifferences '
- group: networking.k8s.io
  kind: Ingress
  name: blacklist
  namespace: blacklist
  jsonPointers:
  - /status
' --grpc-web

echo "✅ Health check override applied"

# 앱 새로고침
argocd app get blacklist --refresh --grpc-web

echo "📊 Current status:"
argocd app get blacklist --grpc-web | grep -E "Sync Status|Health Status"