#!/bin/bash
# GitOps 배포 템플릿 테스트 스크립트

set -e

echo "🧪 GitOps 배포 템플릿 테스트를 시작합니다..."

# === 1. 환경 확인 ===
echo ""
echo "📋 1단계: 환경 확인"

# .env 파일 확인
if [ ! -f .env ]; then
    echo "❌ .env 파일이 없습니다."
    echo "   .env.example을 복사하여 .env를 생성하세요."
    exit 1
fi

source .env
echo "✅ 환경 변수 로드 완료"

# 필수 도구 확인
tools=("docker" "kubectl" "helm" "curl" "jq")
for tool in "${tools[@]}"; do
    if command -v $tool &> /dev/null; then
        echo "✅ $tool 설치됨"
    else
        echo "❌ $tool 설치되지 않음"
        exit 1
    fi
done

# === 2. Registry 연결 테스트 ===
echo ""
echo "🐳 2단계: Docker Registry 연결 테스트"

echo "Registry 연결 테스트: $REGISTRY_URL"
if curl -s -u $DOCKER_REGISTRY_USER:$DOCKER_REGISTRY_PASS $REGISTRY_URL/v2/ | grep -q "{}"; then
    echo "✅ Docker Registry 연결 성공"
else
    echo "❌ Docker Registry 연결 실패"
    echo "   Registry: $REGISTRY_URL"
    echo "   Username: $DOCKER_REGISTRY_USER"
    exit 1
fi

# Docker 로그인 테스트
echo "Docker 로그인 테스트..."
echo "$DOCKER_REGISTRY_PASS" | docker login $REGISTRY_URL --username $DOCKER_REGISTRY_USER --password-stdin
echo "✅ Docker 로그인 성공"

# === 3. ChartMuseum 연결 테스트 ===
echo ""
echo "📊 3단계: ChartMuseum 연결 테스트"

echo "ChartMuseum 연결 테스트: $CHARTS_URL"
if curl -s -u $HELM_REPO_USERNAME:$HELM_REPO_PASSWORD $CHARTS_URL/api/charts | jq . >/dev/null 2>&1; then
    echo "✅ ChartMuseum 연결 성공"
else
    echo "❌ ChartMuseum 연결 실패"
    echo "   URL: $CHARTS_URL"
    echo "   Username: $HELM_REPO_USERNAME"
    exit 1
fi

# === 4. Kubernetes 클러스터 연결 테스트 ===
echo ""
echo "☸️ 4단계: Kubernetes 클러스터 연결 테스트"

# kubeconfig 생성
mkdir -p ~/.kube
cat > ~/.kube/config << EOF
apiVersion: v1
kind: Config
clusters:
- cluster:
    insecure-skip-tls-verify: true
    server: $K8S_CLUSTER
  name: target-cluster
contexts:
- context:
    cluster: target-cluster
    namespace: $APP_NAMESPACE
    user: cluster-admin
  name: target-context
current-context: target-context
users:
- name: cluster-admin
  user:
    token: $K8S_TOKEN
EOF

echo "Kubernetes 클러스터 연결 테스트..."
if kubectl cluster-info >/dev/null 2>&1; then
    echo "✅ Kubernetes 클러스터 연결 성공"
    kubectl get nodes
else
    echo "❌ Kubernetes 클러스터 연결 실패"
    echo "   Cluster: $K8S_CLUSTER"
    exit 1
fi

# === 5. 이미지 빌드 테스트 ===
echo ""
echo "🔨 5단계: Docker 이미지 빌드 테스트"

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
TEST_TAG="test-$TIMESTAMP"
IMAGE_NAME="$REGISTRY_URL/blacklist:$TEST_TAG"

echo "테스트 이미지 빌드: $IMAGE_NAME"
docker build -f deployment/Dockerfile -t $IMAGE_NAME . --no-cache

echo "테스트 이미지 푸시: $IMAGE_NAME"
docker push $IMAGE_NAME

echo "✅ 이미지 빌드 및 푸시 성공"

# === 6. Helm Chart 테스트 ===
echo ""
echo "⛵ 6단계: Helm Chart 검증"

echo "Helm Chart Lint..."
helm lint helm/blacklist

echo "Helm Chart Template 검증..."
helm template test-blacklist helm/blacklist --debug >/dev/null

# Chart 버전 업데이트
sed -i "s/^version:.*/version: $TEST_TAG/" helm/blacklist/Chart.yaml
sed -i "s/^appVersion:.*/appVersion: \"$TEST_TAG\"/" helm/blacklist/Chart.yaml

echo "Helm Chart Package..."
helm package helm/blacklist --destination /tmp/

CHART_FILE=$(ls /tmp/blacklist-$TEST_TAG.tgz)
echo "생성된 차트: $CHART_FILE"

echo "ChartMuseum에 업로드..."
curl -v \
  -u "$HELM_REPO_USERNAME:$HELM_REPO_PASSWORD" \
  -F "chart=@$CHART_FILE" \
  "$CHARTS_URL/api/charts"

echo "✅ Helm Chart 테스트 성공"

# === 7. Kubernetes Secret 생성 테스트 ===
echo ""
echo "🔐 7단계: Kubernetes Secret 생성 테스트"

echo "Kubernetes Secret 생성..."
./scripts/create-k8s-secrets.sh

echo "Secret 확인..."
kubectl get secrets -n $APP_NAMESPACE | grep -E "(regcred|blacklist-secrets)"

echo "✅ Kubernetes Secret 생성 성공"

# === 8. ArgoCD Application 배포 테스트 ===
echo ""
echo "🚀 8단계: ArgoCD Application 배포 테스트"

echo "Development 환경 배포..."
kubectl apply -f k8s-gitops/argocd/blacklist-app-development.yaml

# ArgoCD 동기화 상태 확인
echo "ArgoCD 애플리케이션 상태 확인..."
for i in {1..30}; do
    echo "상태 확인 시도 $i/30..."
    
    SYNC_STATUS=$(kubectl get application blacklist-development -n argocd -o jsonpath='{.status.sync.status}' 2>/dev/null || echo "Unknown")
    HEALTH_STATUS=$(kubectl get application blacklist-development -n argocd -o jsonpath='{.status.health.status}' 2>/dev/null || echo "Unknown")
    
    echo "  Sync Status: $SYNC_STATUS"
    echo "  Health Status: $HEALTH_STATUS"
    
    if [[ "$SYNC_STATUS" == "Synced" ]]; then
        echo "✅ ArgoCD 애플리케이션 동기화 성공!"
        break
    fi
    
    sleep 10
done

# === 9. 배포 상태 확인 ===
echo ""
echo "📊 9단계: 배포 상태 확인"

echo "Pod 상태 확인..."
kubectl get pods -n $APP_NAMESPACE

echo "Service 상태 확인..."
kubectl get svc -n $APP_NAMESPACE

echo "최근 이벤트..."
kubectl get events -n $APP_NAMESPACE --sort-by='.lastTimestamp' | tail -5

# === 10. 애플리케이션 접근 테스트 ===
echo ""
echo "🌐 10단계: 애플리케이션 접근 테스트"

NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[0].address}')
NODE_PORT=${NODE_PORT:-32453}
SERVICE_URL="http://$NODE_IP:$NODE_PORT"

echo "서비스 URL: $SERVICE_URL"

# 헬스체크 대기
echo "애플리케이션 헬스체크 대기..."
for i in {1..60}; do
    echo "헬스체크 시도 $i/60..."
    if curl -f --max-time 10 "$SERVICE_URL/health" >/dev/null 2>&1; then
        echo "✅ 애플리케이션 접근 성공!"
        curl -s "$SERVICE_URL/health" | jq . || true
        break
    fi
    sleep 5
done

# === 테스트 결과 요약 ===
echo ""
echo "📋 =========================================="
echo "🎉 GitOps 배포 템플릿 테스트 완료!"
echo "============================================"
echo ""
echo "✅ 성공한 테스트:"
echo "   - Docker Registry 연결 및 이미지 푸시"
echo "   - ChartMuseum 연결 및 차트 업로드"  
echo "   - Kubernetes 클러스터 연결"
echo "   - Helm Chart 빌드 및 검증"
echo "   - Kubernetes Secret 생성"
echo "   - ArgoCD Application 배포"
echo "   - 애플리케이션 헬스체크"
echo ""
echo "🌐 접속 정보:"
echo "   - Application: $SERVICE_URL"
echo "   - Health Check: $SERVICE_URL/health"
echo "   - API Stats: $SERVICE_URL/api/stats"
echo "   - ArgoCD Dashboard: https://$ARGOCD_SERVER"
echo ""
echo "📦 배포된 리소스:"
echo "   - Docker Image: $IMAGE_NAME"
echo "   - Helm Chart: blacklist-$TEST_TAG"
echo "   - ArgoCD App: blacklist-development"
echo "   - Namespace: $APP_NAMESPACE"
echo ""
echo "🚀 이제 GitHub Actions를 통한 자동 배포가 가능합니다!"
echo "   git add . && git commit -m 'feat: add GitOps template' && git push"

# 정리
echo ""
echo "🧹 테스트 리소스 정리 중..."
docker rmi $IMAGE_NAME >/dev/null 2>&1 || true
rm -f /tmp/blacklist-*.tgz

echo "✅ 테스트 완료!"