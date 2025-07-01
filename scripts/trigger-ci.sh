#!/bin/bash
# CI/CD 파이프라인 테스트 트리거 스크립트

echo "🚀 CI/CD 파이프라인 테스트를 위한 더미 커밋 생성..."

# 현재 시간으로 더미 파일 생성
echo "# CI/CD 테스트 - $(date '+%Y-%m-%d %H:%M:%S')" > .ci-test

# Git에 추가 및 커밋
git add .ci-test
git commit -m "test: CI/CD 파이프라인 테스트 트리거 - $(date '+%Y%m%d-%H%M%S')"

echo "✅ 커밋 생성 완료. GitHub에 푸시 중..."
git push origin main

echo "🔄 GitHub Actions 실행 상태 확인..."
echo "   - GitHub Actions: https://github.com/JCLEE94/blacklist/actions"
echo "   - 자동 이미지 업데이터 로그 확인: kubectl logs -f job/auto-image-updater-\$(date +%Y%m%d%H%M) -n blacklist"
echo ""
echo "⏳ 약 5-10분 후 다음 명령어로 배포 상태를 확인할 수 있습니다:"
echo "   kubectl get pods -n blacklist"
echo "   kubectl logs deployment/blacklist -n blacklist --tail=20"