#!/bin/bash
# GitOps CI/CD 테스트 스크립트

set -e

echo "=== GitOps CI/CD 테스트 ==="
echo ""

# 1. Git 상태 확인
echo "1. Git 상태 확인"
cd /home/jclee/app/blacklist
git status --short

# 2. 변경사항 커밋
echo -e "\n2. 변경사항 커밋"
git add -A
git commit -m "test: GitOps 단일 저장소 CI/CD 테스트 v2.1.2" || echo "No changes to commit"

# 3. Push
echo -e "\n3. GitHub에 Push"
git push origin main

# 4. CI/CD 파이프라인 상태 확인
echo -e "\n4. CI/CD 파이프라인 시작 대기 (10초)"
sleep 10

# 5. GitHub Actions 상태 확인
echo -e "\n5. GitHub Actions 실행 상태"
if command -v gh &> /dev/null; then
    gh run list --workflow=gitops-cicd.yml --limit 1
else
    echo "GitHub CLI not available"
fi

# 6. ArgoCD 애플리케이션 상태
echo -e "\n6. ArgoCD 애플리케이션 상태"
kubectl get application blacklist -n argocd 2>/dev/null || echo "ArgoCD app not found"

# 7. Kubernetes 배포 상태
echo -e "\n7. Kubernetes 배포 상태"
kubectl get pods -n blacklist | head -5

echo -e "\n✅ 테스트 완료 - CI/CD 파이프라인이 시작되었습니다"