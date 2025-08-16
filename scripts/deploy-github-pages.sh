#!/bin/bash
# GitHub Pages 포트폴리오 배포 스크립트

set -e

echo "📄 GitHub Pages 포트폴리오 배포"

# docs/ 디렉토리 확인
if [[ ! -d "docs" ]]; then
    echo "❌ docs/ 디렉토리가 없습니다."
    exit 1
fi

# GitHub Pages 설정 확인
PAGES_URL="https://jclee94.github.io/blacklist/"
echo "🌐 배포 대상: $PAGES_URL"

# 문서 업데이트
if [[ -f "docs/index.html" ]]; then
    # 현재 시간으로 업데이트
    CURRENT_TIME=$(date "+%Y-%m-%d %H:%M:%S")
    sed -i "s/Last updated: .*/Last updated: $CURRENT_TIME/g" docs/index.html 2>/dev/null || true
fi

# Git에 추가 및 커밋
git add docs/
if git diff --staged --quiet; then
    echo "ℹ️ 변경사항이 없습니다."
else
    git commit -m "docs: Update GitHub Pages portfolio

📄 Portfolio documentation updated
🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
fi

# GitHub에 푸시 (Pages 자동 배포 트리거)
echo "📤 GitHub Pages 배포 트리거..."
git push origin main

echo "✅ GitHub Pages 배포 완료!"
echo "🌐 포트폴리오: $PAGES_URL"
echo "⏳ 배포 완료까지 1-2분 소요됩니다."