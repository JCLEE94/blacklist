#!/bin/bash

set -e

echo "🔍 Git 상태 확인..."
git status --porcelain

echo "📝 변경사항 스테이징..."
git add .

echo "💾 커밋 생성..."
git commit -F commit_message.txt

echo "🚀 origin/main으로 푸시..."
git push origin main

echo "✅ Git 작업 완료!"
echo "🔄 GitHub Actions 파이프라인이 자동으로 트리거됩니다:"
echo "   1. Docker 빌드"
echo "   2. registry.jclee.me로 이미지 푸시"
echo "   3. Helm 차트 업데이트"  
echo "   4. ArgoCD 자동 싱크"

# 임시 파일 정리
rm -f commit_message.txt git_commit_and_push.sh