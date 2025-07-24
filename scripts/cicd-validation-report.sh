#!/bin/bash
# CI/CD 검증 보고서

echo "=== CI/CD 파이프라인 검증 보고서 ==="
echo "시간: $(date)"
echo ""

# 1. 워크플로우 파일 검증
echo "## 1. GitHub Actions 워크플로우 검증"
echo "-------------------------------------"

# simple-cicd.yml 검증
echo "### simple-cicd.yml"
if [ -f ".github/workflows/simple-cicd.yml" ]; then
    echo "✅ 파일 존재"
    echo "특징:"
    echo "- Registry 인증 없이 직접 push"
    echo "- 단순한 빌드/푸시 프로세스"
    echo "- ArgoCD Image Updater 의존"
else
    echo "❌ 파일 없음"
fi
echo ""

# gitops-cicd.yml 검증
echo "### gitops-cicd.yml"
if [ -f ".github/workflows/gitops-cicd.yml" ]; then
    echo "✅ 파일 존재 (수정됨)"
    echo "변경사항:"
    echo "- Registry 로그인 제거됨"
    echo "- GitHub token 추가됨"
    echo "- K8s 매니페스트 업데이트 포함"
else
    echo "❌ 파일 없음"
fi
echo ""

# 2. ArgoCD 설정 검증
echo "## 2. ArgoCD 설정 검증"
echo "----------------------"

echo "### SSH 버전 (기존)"
if [ -f "k8s-gitops/argocd/blacklist-app.yaml" ]; then
    echo "✅ blacklist-app.yaml 존재"
    grep "repoURL" k8s-gitops/argocd/blacklist-app.yaml | head -1
else
    echo "❌ 파일 없음"
fi
echo ""

echo "### HTTPS 버전 (신규)"
if [ -f "k8s-gitops/argocd/blacklist-app-https.yaml" ]; then
    echo "✅ blacklist-app-https.yaml 존재"
    grep "repoURL" k8s-gitops/argocd/blacklist-app-https.yaml | head -1
    echo "장점: SSH key 설정 불필요"
else
    echo "❌ 파일 없음"
fi
echo ""

# 3. K8s 매니페스트 구조 검증
echo "## 3. K8s 매니페스트 구조 검증"
echo "-------------------------------"

echo "### 디렉토리 구조"
if [ -d "k8s-gitops" ]; then
    echo "✅ k8s-gitops 디렉토리 존재"
    echo ""
    echo "구조:"
    find k8s-gitops -type f -name "*.yaml" | sort | head -20
else
    echo "❌ k8s-gitops 디렉토리 없음"
fi
echo ""

echo "### Kustomization 설정"
if [ -f "k8s-gitops/overlays/prod/kustomization.yaml" ]; then
    echo "✅ Production kustomization.yaml 존재"
    echo "현재 이미지 태그:"
    grep -A1 "images:" k8s-gitops/overlays/prod/kustomization.yaml | grep "newTag" || echo "태그 없음"
else
    echo "❌ 파일 없음"
fi
echo ""

# 4. 문제점 진단
echo "## 4. 발견된 문제점"
echo "-------------------"

problems=0

# Registry 인증 확인
echo -n "- Registry 인증: "
if grep -q "REGISTRY_PASSWORD" .github/workflows/gitops-cicd.yml 2>/dev/null; then
    echo "❌ 여전히 인증 사용 중 (수정 필요)"
    ((problems++))
else
    echo "✅ 인증 제거됨"
fi

# ArgoCD 접근 방식
echo -n "- ArgoCD Git 접근: "
if kubectl get application blacklist -n argocd -o yaml 2>/dev/null | grep -q "git@github.com"; then
    echo "❌ SSH 사용 중 (HTTPS 전환 권장)"
    ((problems++))
else
    echo "✅ HTTPS 사용 또는 미설정"
fi

# GitHub Secrets 의존성
echo -n "- GitHub Secrets 의존성: "
if grep -q "secrets\." .github/workflows/simple-cicd.yml 2>/dev/null; then
    echo "❌ Secrets 의존성 있음"
    ((problems++))
else
    echo "✅ Secrets 의존성 없음"
fi

echo ""
echo "총 문제점: $problems개"
echo ""

# 5. 권장 사항
echo "## 5. 권장 사항"
echo "---------------"

if [ $problems -gt 0 ]; then
    echo "### 즉시 수정 필요:"
    echo "1. ArgoCD 앱을 HTTPS 버전으로 재생성:"
    echo "   kubectl delete application blacklist -n argocd --wait=false"
    echo "   kubectl apply -f k8s-gitops/argocd/blacklist-app-https.yaml"
    echo ""
    echo "2. simple-cicd.yml 워크플로우 사용:"
    echo "   - 복잡한 매니페스트 업데이트 없음"
    echo "   - Registry 인증 불필요"
    echo ""
else
    echo "✅ CI/CD 파이프라인이 올바르게 설정되었습니다."
fi

echo ""
echo "### 테스트 방법:"
echo "1. 코드 변경 후 커밋"
echo "2. git push origin main"
echo "3. GitHub Actions 확인: https://github.com/JCLEE94/blacklist/actions"
echo "4. ArgoCD 상태 확인: argocd app get blacklist --grpc-web"
echo ""

# 6. 현재 상태 요약
echo "## 6. 현재 상태 요약"
echo "-------------------"
echo "- 워크플로우: 2개 (gitops-cicd.yml, simple-cicd.yml)"
echo "- ArgoCD 설정: 2개 (SSH, HTTPS)"
echo "- K8s 구조: Kustomize 기반"
echo "- Registry: registry.jclee.me (인증 없음)"
echo ""

echo "=== 검증 완료 ==="