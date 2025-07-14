#!/bin/bash

# ArgoCD 완전 설정 스크립트
# GitHub + Private Registry 연동

set -e

echo "🚀 ArgoCD 완전 설정 시작..."

# ArgoCD 서버 정보
ARGOCD_SERVER="argo.jclee.me"
ARGOCD_USER="admin"
ARGOCD_PASS="bingogo1"

# 프로젝트 정보
GITHUB_REPO="https://github.com/JCLEE94/blacklist.git"
REGISTRY="registry.jclee.me"
IMAGE_NAME="blacklist"
NAMESPACE="blacklist"

# ArgoCD CLI 로그인
echo "📌 ArgoCD 로그인..."
argocd login $ARGOCD_SERVER \
  --username $ARGOCD_USER \
  --password $ARGOCD_PASS \
  --grpc-web \
  --insecure

# GitHub Repository 연결 (Public repo라 인증 불필요)
echo "📌 GitHub Repository 연결..."
argocd repo add $GITHUB_REPO --name blacklist-repo || echo "Repository already exists"

# Namespace 생성
echo "📌 Namespace 생성..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Registry Secret 생성 (인증 불필요하지만 필요한 경우)
echo "📌 Registry Secret 생성..."
kubectl apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: regcred
  namespace: $NAMESPACE
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: eyJhdXRocyI6eyJyZWdpc3RyeS5qY2xlZS5tZSI6eyJhdXRoIjoiIn19fQ==
EOF

# ArgoCD Application 생성
echo "📌 ArgoCD Application 생성..."
argocd app create $IMAGE_NAME \
  --repo $GITHUB_REPO \
  --path k8s \
  --revision main \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace $NAMESPACE \
  --sync-policy automated \
  --self-heal \
  --auto-prune \
  --sync-option CreateNamespace=true \
  --sync-option PrunePropagationPolicy=foreground \
  --sync-option PruneLast=true \
  --kustomize-image $REGISTRY/$IMAGE_NAME:latest \
  --upsert

# Image Updater Annotations 설정
echo "📌 Image Updater 설정..."
argocd app set $IMAGE_NAME --annotation argocd-image-updater.argoproj.io/image-list=$IMAGE_NAME=$REGISTRY/$IMAGE_NAME:latest
argocd app set $IMAGE_NAME --annotation argocd-image-updater.argoproj.io/$IMAGE_NAME.update-strategy=latest
argocd app set $IMAGE_NAME --annotation argocd-image-updater.argoproj.io/write-back-method=git
argocd app set $IMAGE_NAME --annotation argocd-image-updater.argoproj.io/git-branch=main

# ArgoCD Image Updater에 Registry 설정 추가
echo "📌 Image Updater Registry 설정..."
kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-image-updater-config
  namespace: argocd
data:
  registries.conf: |
    registries:
    - name: registry.jclee.me
      prefix: registry.jclee.me
      api_url: http://registry.jclee.me
      insecure: yes
      defaultns: library
      credentials: secret:argocd/argocd-image-updater-secret#registry.jclee.me
EOF

# 빈 시크릿 생성 (인증 불필요)
kubectl create secret generic argocd-image-updater-secret \
  --from-literal=registry.jclee.me= \
  -n argocd \
  --dry-run=client -o yaml | kubectl apply -f -

# Image Updater 재시작
echo "📌 Image Updater 재시작..."
kubectl rollout restart deployment argocd-image-updater -n argocd

# Application 동기화
echo "📌 Application 동기화..."
argocd app sync $IMAGE_NAME

# 상태 확인
echo "📌 최종 상태 확인..."
argocd app get $IMAGE_NAME

echo "✅ ArgoCD 설정 완료!"
echo ""
echo "📊 확인 사항:"
echo "1. ArgoCD UI: https://$ARGOCD_SERVER"
echo "2. Application 상태: argocd app get $IMAGE_NAME"
echo "3. Image Updater 로그: kubectl logs -n argocd deployment/argocd-image-updater"
echo "4. 애플리케이션 접속: https://blacklist.jclee.me"