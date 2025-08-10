#!/bin/bash

# 🔄 Kustomize 기반 GitOps 파이프라인 실행 스크립트

echo "🚀 Kustomize 기반 CI/CD 파이프라인 시작..."
echo ""

# Git 사용자 정보 설정
git config --local user.name "JCLEE94"
git config --local user.email "jclee@example.com"

# 현재 버전 확인
CURRENT_VERSION=$(cat VERSION)
echo "📦 현재 버전: $CURRENT_VERSION"

# 변경사항 스테이징
echo "📝 변경사항 스테이징 중..."
git add .
git add -A

# 변경사항 확인
echo ""
echo "📋 커밋할 변경사항:"
git diff --staged --name-only

echo ""
echo "🔍 변경사항 요약:"
git diff --staged --stat

# Conventional commit 생성 (Claude co-author 포함)
echo ""
echo "💾 Conventional commit 생성 중..."

COMMIT_MESSAGE="feat: migrate to Kustomize-based GitOps deployment v${CURRENT_VERSION}

✨ 주요 변경사항:
- GitHub Actions 워크플로우를 Helm에서 Kustomize로 마이그레이션
- 다중 환경 오버레이 지원 (dev/staging/production) 
- Docker 레이어 캐싱으로 빌드 성능 최적화
- ArgoCD Image Updater와 자동 동기화 연동
- registry.jclee.me 프라이빗 레지스트리 통합
- Self-hosted runner 호환성 유지 (v3 actions)

🏗️ 기술적 개선:
- Kustomize 4.5.7 기반 매니페스트 관리
- 환경별 ConfigMap 자동 생성
- 이미지 태깅 전략 개선 (version/sha/date)
- GitOps 워크플로우 완전 자동화

🎯 배포 대상:
- Development: k8s/overlays/dev/
- Staging: k8s/overlays/staging/  
- Production: k8s/overlays/production/

Co-authored-by: Claude <claude@anthropic.com>"

git commit -m "$COMMIT_MESSAGE"

if [ $? -eq 0 ]; then
    echo "✅ Conventional commit 생성 완료"
else
    echo "❌ Commit 생성 실패"
    exit 1
fi

echo ""
echo "🔄 Git push 실행 중..."
git push origin main

if [ $? -eq 0 ]; then
    echo "✅ Git push 성공 - GitHub Actions 트리거됨"
else
    echo "❌ Git push 실패"
    exit 1
fi

echo ""
echo "📊 파이프라인 상태 모니터링:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔗 GitHub Actions: https://github.com/JCLEE94/blacklist/actions"
echo "🔗 ArgoCD Dashboard: https://argo.jclee.me"
echo "🔗 Docker Registry: registry.jclee.me/blacklist"
echo ""
echo "⏱️ 예상 배포 시간:"
echo "  • Docker 빌드 & 푸시: 2-3분"
echo "  • Kustomize 매니페스트 업데이트: 30초"
echo "  • ArgoCD 자동 동기화: 1-2분"
echo "  • 전체 배포 완료: 5-7분"
echo ""
echo "🎯 다음 단계:"
echo "  1. ✅ Conventional commit with Claude co-author 생성 완료"
echo "  2. ✅ Git push를 통한 GitHub Actions 트리거 완료"
echo "  3. 🔄 Docker 이미지 빌드 & registry.jclee.me 푸시 진행 중"
echo "  4. 🔄 Kustomize 매니페스트 자동 업데이트 진행 중"
echo "  5. ⏳ ArgoCD Image Updater 감지 대기 중 (최대 2분)"
echo "  6. ⏳ Kubernetes 클러스터 자동 배포 대기 중"
echo ""
echo "🚀 Kustomize 기반 GitOps 파이프라인이 성공적으로 시작되었습니다!"