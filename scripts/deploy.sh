#!/bin/bash
# 간편 배포 스크립트

echo "🚀 배포 시작..."

# Git 상태 확인
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  커밋되지 않은 변경사항이 있습니다."
    read -p "계속하시겠습니까? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 변경사항 커밋 및 푸시
git add -A
git commit -m "chore: auto deployment $(date +'%Y-%m-%d %H:%M:%S')"
git push origin main

echo "✅ GitHub에 푸시 완료"
echo "⏳ CI/CD 파이프라인이 자동으로 실행됩니다..."
echo ""
echo "진행 상황 확인:"
echo "- GitHub Actions: https://github.com/JCLEE94/blacklist/actions"
echo "- ArgoCD: kubectl get app blacklist -n argocd"
echo "- Pod 상태: kubectl get pods -n blacklist -w"
