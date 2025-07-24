#!/bin/bash
# CI/CD 파이프라인 테스트 스크립트

set -e

echo "=== CI/CD 파이프라인 테스트 ==="
echo ""

# 1. 사전 확인
echo "1. 사전 확인"
echo "------------"

# Git 상태
echo "Git 상태:"
git status --short || echo "Git 상태 확인 실패"
echo ""

# ArgoCD 애플리케이션 상태
echo "ArgoCD 애플리케이션:"
kubectl get application blacklist -n argocd 2>/dev/null || echo "ArgoCD 앱 없음"
echo ""

# 2. 테스트 변경사항 생성
echo "2. 테스트 변경사항 생성"
echo "----------------------"

# 버전 변경
VERSION="2.1.4-cicd-test-$(date +%Y%m%d%H%M%S)"
echo "새 버전: $VERSION"

# __init__.py 버전 업데이트
if [ -f "src/core/__init__.py" ]; then
    sed -i "s/__version__ = .*/__version__ = '$VERSION'/" src/core/__init__.py
    echo "✅ 버전 업데이트됨"
else
    echo "❌ __init__.py 파일 없음"
fi

# README에 테스트 마커 추가
echo "" >> README.md
echo "<!-- CI/CD Test: $VERSION -->" >> README.md
echo "✅ README 업데이트됨"

# 3. Git 커밋 및 푸시
echo ""
echo "3. Git 커밋 및 푸시"
echo "------------------"

git add -A
git commit -m "test: CI/CD pipeline validation - $VERSION

- Version bump to $VERSION
- Testing simple-cicd.yml workflow
- Validating ArgoCD integration" || echo "변경사항 없음"

echo ""
echo "푸시 중..."
git push origin main || {
    echo "❌ 푸시 실패!"
    echo "수동으로 실행: git push origin main"
    exit 1
}

echo ""
echo "4. CI/CD 파이프라인 모니터링"
echo "---------------------------"
echo ""
echo "다음 위치에서 확인:"
echo ""
echo "1. GitHub Actions (즉시 확인):"
echo "   https://github.com/JCLEE94/blacklist/actions"
echo ""
echo "2. 워크플로우 실행 확인 (10초 후):"
sleep 10

# GitHub CLI가 있으면 상태 확인
if command -v gh &>/dev/null; then
    echo "최근 워크플로우 실행:"
    gh run list --limit 3 || echo "GitHub CLI 실행 실패"
else
    echo "GitHub CLI 없음 - 웹에서 확인 필요"
fi

echo ""
echo "3. Docker 이미지 확인 (수동):"
echo "   docker images | grep blacklist"
echo ""
echo "4. ArgoCD 동기화 상태 (2-5분 후):"
echo "   kubectl get application blacklist -n argocd"
echo "   argocd app get blacklist --grpc-web"
echo ""
echo "5. Pod 배포 상태:"
echo "   kubectl get pods -n blacklist -w"
echo ""

# 5. 검증 체크리스트
echo "5. 검증 체크리스트"
echo "-----------------"
echo ""
echo "[ ] GitHub Actions 워크플로우 시작됨"
echo "[ ] Docker 빌드 성공"
echo "[ ] Registry에 이미지 푸시됨"
echo "[ ] ArgoCD가 새 이미지 감지"
echo "[ ] K8s Pod 재시작됨"
echo "[ ] 애플리케이션 정상 작동"
echo ""

echo "=== 테스트 시작됨 ==="
echo ""
echo "팁: 실시간 모니터링을 위해 다음 명령 실행:"
echo "watch -n 5 'kubectl get pods -n blacklist; echo; kubectl get application blacklist -n argocd'"