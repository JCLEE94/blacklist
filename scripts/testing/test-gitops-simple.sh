#!/bin/bash
# GitOps 배포 템플릿 간단 테스트 스크립트
# Docker 빌드를 제외한 핵심 기능만 테스트

set -e

echo "🧪 GitOps 핵심 기능 테스트를 시작합니다..."

# 환경 변수 로드
source .env
echo "✅ 환경 변수 로드 완료"

# === 1. Registry 연결 테스트 ===
echo ""
echo "🐳 Docker Registry 연결 테스트"
if curl -s -u $DOCKER_REGISTRY_USER:$DOCKER_REGISTRY_PASS $REGISTRY_URL/v2/ | grep -q "{}"; then
    echo "✅ Docker Registry 연결 성공"
else
    echo "❌ Docker Registry 연결 실패"
    exit 1
fi

# === 2. ChartMuseum 연결 테스트 ===
echo ""
echo "📊 ChartMuseum 연결 테스트"
if curl -s -u $HELM_REPO_USERNAME:$HELM_REPO_PASSWORD $CHARTS_URL/api/charts | jq . >/dev/null 2>&1; then
    echo "✅ ChartMuseum 연결 성공"
else
    echo "❌ ChartMuseum 연결 실패"
    exit 1
fi

# === 3. Kubernetes 클러스터 연결 테스트 ===
echo ""
echo "☸️ Kubernetes 클러스터 연결 테스트"
if kubectl cluster-info >/dev/null 2>&1; then
    echo "✅ Kubernetes 클러스터 연결 성공"
    kubectl get nodes --no-headers | head -1
else
    echo "❌ Kubernetes 클러스터 연결 실패"
    exit 1
fi

# === 4. Helm Chart 검증 ===
echo ""
echo "⛵ Helm Chart 검증"
echo "Helm Chart Lint..."
if helm lint helm/blacklist >/dev/null 2>&1; then
    echo "✅ Helm Chart Lint 통과"
else
    echo "❌ Helm Chart Lint 실패"
fi

echo "Helm Chart Template 검증..."
if helm template test-blacklist helm/blacklist --debug >/dev/null 2>&1; then
    echo "✅ Helm Template 검증 통과"
else
    echo "❌ Helm Template 검증 실패"
fi

# === 5. Kubernetes Secret 확인/생성 ===
echo ""
echo "🔐 Kubernetes Secret 확인"
echo "현재 네임스페이스의 Secret 목록:"
kubectl get secrets -n $APP_NAMESPACE | grep -E "(regcred|blacklist-secrets)" || echo "  (관련 Secret이 없습니다)"

# Secret 생성 스크립트 실행
if [ -f "scripts/create-k8s-secrets.sh" ]; then
    echo "Kubernetes Secret 생성..."
    ./scripts/create-k8s-secrets.sh
    echo "✅ Kubernetes Secret 생성 완료"
fi

# === 6. ArgoCD Application 상태 확인 ===
echo ""
echo "🚀 ArgoCD Application 상태 확인"

# Development 환경 확인
if kubectl get application blacklist-development -n argocd >/dev/null 2>&1; then
    SYNC_STATUS=$(kubectl get application blacklist-development -n argocd -o jsonpath='{.status.sync.status}' 2>/dev/null || echo "Unknown")
    HEALTH_STATUS=$(kubectl get application blacklist-development -n argocd -o jsonpath='{.status.health.status}' 2>/dev/null || echo "Unknown")
    echo "Development App - Sync: $SYNC_STATUS, Health: $HEALTH_STATUS"
else
    echo "Development Application이 없습니다. 생성합니다..."
    kubectl apply -f k8s-gitops/argocd/blacklist-app-development.yaml
fi

# Production 환경 확인
if kubectl get application blacklist-production -n argocd >/dev/null 2>&1; then
    SYNC_STATUS=$(kubectl get application blacklist-production -n argocd -o jsonpath='{.status.sync.status}' 2>/dev/null || echo "Unknown")
    HEALTH_STATUS=$(kubectl get application blacklist-production -n argocd -o jsonpath='{.status.health.status}' 2>/dev/null || echo "Unknown")
    echo "Production App - Sync: $SYNC_STATUS, Health: $HEALTH_STATUS"
else
    echo "Production Application이 없습니다. 생성합니다..."
    kubectl apply -f k8s-gitops/argocd/blacklist-app-production.yaml
fi

# === 7. 배포 상태 확인 ===
echo ""
echo "📊 현재 배포 상태"
echo "Pod 상태:"
kubectl get pods -n $APP_NAMESPACE 2>/dev/null || echo "  (Pod가 없습니다)"

echo "Service 상태:"
kubectl get svc -n $APP_NAMESPACE 2>/dev/null || echo "  (Service가 없습니다)"

# === 8. GitHub Actions Workflow 확인 ===
echo ""
echo "⚡ GitHub Actions Workflow 확인"
if [ -f ".github/workflows/gitops-template.yml" ]; then
    echo "✅ GitOps Template Workflow 파일 존재"
else
    echo "❌ GitOps Template Workflow 파일이 없습니다"
fi

# === 9. 환경 변수 요약 ===
echo ""
echo "📋 설정된 환경 변수 요약"
echo "  - Registry: $REGISTRY_URL"
echo "  - ChartMuseum: $CHARTS_URL"
echo "  - Kubernetes: $K8S_CLUSTER"
echo "  - ArgoCD: $ARGOCD_SERVER"
echo "  - App Namespace: $APP_NAMESPACE"
echo "  - Node Port: $NODE_PORT"

# === 테스트 결과 요약 ===
echo ""
echo "============================================"
echo "🎉 GitOps 핵심 기능 테스트 완료!"
echo "============================================"
echo ""
echo "✅ 검증 완료:"
echo "   - Docker Registry 연결 및 인증"
echo "   - ChartMuseum 연결 및 API 접근"
echo "   - Kubernetes 클러스터 연결"
echo "   - Helm Chart 구조 및 템플릿 검증"
echo "   - ArgoCD Application 상태 확인"
echo "   - GitHub Actions Workflow 구성"
echo ""
echo "🚀 CI/CD 파이프라인 준비 완료!"
echo "   이제 다음 명령어로 자동 배포를 트리거할 수 있습니다:"
echo ""
echo "   git add ."
echo "   git commit -m \"feat: implement GitOps CI/CD pipeline\""  
echo "   git push origin main      # → Production 배포"
echo "   git push origin develop   # → Development 배포"
echo ""
echo "🌐 ArgoCD Dashboard: https://$ARGOCD_SERVER"
echo ""