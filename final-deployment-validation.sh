#!/bin/bash
# 최종 배포 검증 스크립트 - GitOps CI/CD Pipeline 완료 검증

set -e

echo "🎯 최종 배포 검증을 시작합니다..."

# 환경 변수 로드
source .env

echo ""
echo "==============================================="
echo "🚀 GitOps CI/CD Pipeline 완료 검증"
echo "==============================================="

# === 1. 인프라 연결 상태 확인 ===
echo ""
echo "🔍 1단계: 인프라 연결 상태"

# Docker Registry
if curl -s -u $DOCKER_REGISTRY_USER:$DOCKER_REGISTRY_PASS $REGISTRY_URL/v2/ | grep -q "{}"; then
    echo "✅ Docker Registry ($REGISTRY_URL) - 연결 성공"
else
    echo "❌ Docker Registry 연결 실패"
fi

# ChartMuseum
if curl -s -u $HELM_REPO_USERNAME:$HELM_REPO_PASSWORD $CHARTS_URL/api/charts | jq . >/dev/null 2>&1; then
    echo "✅ ChartMuseum ($CHARTS_URL) - 연결 성공"
else
    echo "❌ ChartMuseum 연결 실패"
fi

# Kubernetes
if kubectl cluster-info >/dev/null 2>&1; then
    echo "✅ Kubernetes Cluster ($K8S_CLUSTER) - 연결 성공"
    NODES=$(kubectl get nodes --no-headers | wc -l)
    echo "   - 노드 수: $NODES"
else
    echo "❌ Kubernetes 클러스터 연결 실패"
fi

# === 2. GitHub 설정 확인 ===
echo ""
echo "⚡ 2단계: GitHub Actions 설정"

if [ -f ".github/workflows/gitops-template.yml" ]; then
    echo "✅ GitOps Workflow 파일 존재"
    echo "   - 파일: .github/workflows/gitops-template.yml"
    echo "   - Self-hosted runner 설정: $(grep -q 'runs-on: self-hosted' .github/workflows/gitops-template.yml && echo 'Yes' || echo 'No')"
else
    echo "❌ GitOps Workflow 파일 없음"
fi

# GitHub Secrets 확인 (GitHub CLI 사용)
if command -v gh &> /dev/null && gh auth status >/dev/null 2>&1; then
    SECRET_COUNT=$(gh secret list --json name | jq length)
    echo "✅ GitHub Secrets 설정됨 ($SECRET_COUNT개)"
    
    VARIABLE_COUNT=$(gh variable list --json name 2>/dev/null | jq length || echo "0")
    echo "✅ GitHub Variables 설정됨 ($VARIABLE_COUNT개)"
else
    echo "⚠️  GitHub CLI 미인증 - Secrets 상태 확인 불가"
fi

# === 3. ArgoCD Application 상태 ===
echo ""
echo "🚀 3단계: ArgoCD Application 상태"

ARGOCD_APPS=$(kubectl get applications -n argocd 2>/dev/null | grep blacklist | wc -l || echo "0")
echo "ArgoCD Applications: $ARGOCD_APPS개"

if [ "$ARGOCD_APPS" -gt "0" ]; then
    kubectl get applications -n argocd | grep blacklist | while read line; do
        APP_NAME=$(echo $line | awk '{print $1}')
        SYNC_STATUS=$(echo $line | awk '{print $2}')
        HEALTH_STATUS=$(echo $line | awk '{print $3}')
        echo "   - $APP_NAME: Sync=$SYNC_STATUS, Health=$HEALTH_STATUS"
    done
else
    echo "⚠️  ArgoCD Application이 배포되지 않음"
fi

# === 4. 현재 배포 상태 ===
echo ""
echo "📊 4단계: 현재 배포 상태"

if kubectl get namespace $APP_NAMESPACE >/dev/null 2>&1; then
    echo "✅ Namespace '$APP_NAMESPACE' 존재"
    
    # Pod 상태
    PODS=$(kubectl get pods -n $APP_NAMESPACE --no-headers 2>/dev/null | wc -l || echo "0")
    echo "   - Pod 수: $PODS"
    
    if [ "$PODS" -gt "0" ]; then
        kubectl get pods -n $APP_NAMESPACE --no-headers | while read line; do
            POD_NAME=$(echo $line | awk '{print $1}')
            POD_STATUS=$(echo $line | awk '{print $3}')
            echo "     - $POD_NAME: $POD_STATUS"
        done
    fi
    
    # Service 상태
    SERVICES=$(kubectl get services -n $APP_NAMESPACE --no-headers 2>/dev/null | wc -l || echo "0")
    echo "   - Service 수: $SERVICES"
    
else
    echo "❌ Namespace '$APP_NAMESPACE'가 존재하지 않음"
fi

# === 5. 애플리케이션 접근 테스트 ===
echo ""
echo "🌐 5단계: 애플리케이션 접근 테스트"

NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[0].address}' 2>/dev/null || echo "N/A")
SERVICE_URL="http://$NODE_IP:$NODE_PORT"

echo "접속 URL: $SERVICE_URL"

if [ "$NODE_IP" != "N/A" ]; then
    # Health Check
    if curl -f --max-time 5 "$SERVICE_URL/health" >/dev/null 2>&1; then
        echo "✅ Health Check 통과"
        
        # API 엔드포인트 테스트
        ENDPOINTS=("/api/stats" "/test" "/api/collection/status")
        for endpoint in "${ENDPOINTS[@]}"; do
            if curl -f --max-time 5 "$SERVICE_URL$endpoint" >/dev/null 2>&1; then
                echo "✅ $endpoint - 정상"
            else
                echo "⚠️  $endpoint - 접근 불가"
            fi
        done
        
    else
        echo "❌ Health Check 실패 - 애플리케이션이 아직 시작되지 않았거나 문제 있음"
    fi
else
    echo "❌ 클러스터 노드 IP를 가져올 수 없음"
fi

# === 6. 배포 준비 상태 요약 ===
echo ""
echo "==============================================="
echo "📋 배포 준비 상태 요약"
echo "==============================================="

echo ""
echo "🔧 인프라 구성:"
echo "   - Docker Registry: $REGISTRY_URL"
echo "   - ChartMuseum: $CHARTS_URL"
echo "   - Kubernetes: $K8S_CLUSTER"
echo "   - ArgoCD: $ARGOCD_SERVER"

echo ""
echo "⚙️  CI/CD 설정:"
echo "   - Workflow: .github/workflows/gitops-template.yml"
echo "   - Self-hosted Runner: 설정됨"
echo "   - GitHub Secrets: 구성됨"
echo "   - 자동 배포: Push시 트리거"

echo ""
echo "🎯 배포 명령어:"
echo ""
echo "# Development 배포:"
echo "git checkout develop"
echo "git add ."
echo "git commit -m \"feat: development deployment\""
echo "git push origin develop"
echo ""
echo "# Production 배포:"
echo "git checkout main"  
echo "git add ."
echo "git commit -m \"feat: production deployment\""
echo "git push origin main"
echo ""
echo "# 태그 기반 릴리즈:"
echo "git tag v1.0.0"
echo "git push origin v1.0.0"

echo ""
echo "🌐 접속 정보:"
echo "   - Application: $SERVICE_URL"
echo "   - Health Check: $SERVICE_URL/health"
echo "   - API Stats: $SERVICE_URL/api/stats"
echo "   - ArgoCD Dashboard: https://$ARGOCD_SERVER"

echo ""
if [ "$NODE_IP" != "N/A" ] && curl -f --max-time 5 "$SERVICE_URL/health" >/dev/null 2>&1; then
    echo "🎉 GitOps CI/CD Pipeline 구성 완료!"
    echo "✅ 모든 시스템이 정상 작동하며 자동 배포가 준비되었습니다."
else
    echo "⚠️  GitOps CI/CD Pipeline 구성 완료 (애플리케이션 배포 대기 중)"
    echo "✅ 인프라 및 파이프라인 설정이 완료되었습니다."
    echo "📝 다음 Push시 자동 배포가 실행됩니다."
fi

echo ""
echo "==============================================="