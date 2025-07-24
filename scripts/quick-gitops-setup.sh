#!/bin/bash
# 빠른 GitOps 자동화 설정

echo "⚡ GitOps 빠른 자동화 설정..."

# ArgoCD Application 적용
echo "1. ArgoCD Application 생성..."
kubectl apply -f k8s-gitops/argocd/blacklist-app-auto.yaml

# Image Updater 재시작 (설정 반영)
echo "2. Image Updater 재시작..."
kubectl rollout restart deployment/argocd-image-updater -n argocd

# 초기 동기화
echo "3. 초기 동기화..."
argocd app sync blacklist --grpc-web || true

echo "✅ GitOps 자동화 설정 완료!"
echo ""
echo "이제 git push만 하면 자동 배포됩니다:"
echo "1. git add . && git commit -m 'feat: 새 기능'"
echo "2. git push origin main"
echo "3. 2분 내 자동 배포 완료"