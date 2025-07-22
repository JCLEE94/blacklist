#!/bin/bash
# 즉시 배포 스크립트

echo "🚀 GitOps 자동 배포 시작..."

# Git 상태 확인
echo "📋 Git 상태 확인..."
git status --short

# 모든 변경사항 추가
echo "📦 변경사항 추가..."
git add -A

# 커밋
echo "💾 커밋 생성..."
git commit -m "feat: GitOps 완전 자동화 설정

- CI/CD 파이프라인 개선: 테스트 실패 시 빌드 중단
- ArgoCD 자동 동기화 및 Self-healing 활성화  
- Image Updater 자동 배포 설정
- 멀티 태그 전략 (timestamp, sha, latest)
- GitHub Actions 워크플로우 최적화"

# Push
echo "📤 GitHub에 Push..."
git push origin main

echo ""
echo "✅ Push 완료!"
echo ""
echo "🔄 자동 배포 프로세스:"
echo "1. GitHub Actions 빌드 시작 (바로)"
echo "2. Docker 이미지 빌드 및 푸시 (~2분)"
echo "3. ArgoCD Image Updater 감지 (2분 이내)"
echo "4. Kubernetes 자동 배포 (~1분)"
echo ""
echo "📊 모니터링:"
echo "- GitHub Actions: https://github.com/JCLEE94/blacklist/actions"
echo "- ArgoCD 상태: argocd app get blacklist --grpc-web"
echo "- Pod 상태: kubectl get pods -n blacklist -w"