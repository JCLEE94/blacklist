#!/bin/bash
# Kubernetes Secrets 생성 스크립트
# GitOps 템플릿용 필수 시크릿 구성

set -e

echo "🔐 Kubernetes Secrets 생성을 시작합니다..."

# 환경 변수 로드
if [ -f .env ]; then
    source .env
    echo "✅ .env 파일에서 환경 변수를 로드했습니다."
else
    echo "❌ .env 파일이 없습니다. .env.example을 복사하여 .env를 생성하세요."
    echo "   cp .env.example .env"
    exit 1
fi

# 기본값 설정
NAMESPACE=${APP_NAMESPACE:-blacklist}
REGISTRY_URL=${REGISTRY_URL:-registry.jclee.me}

# kubectl 확인
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl이 설치되어 있지 않습니다."
    exit 1
fi

# 클러스터 연결 확인
if ! kubectl cluster-info >/dev/null 2>&1; then
    echo "❌ Kubernetes 클러스터에 연결할 수 없습니다."
    echo "   kubeconfig를 확인하세요."
    exit 1
fi

echo "✅ Kubernetes 클러스터 연결 확인 완료"

# 네임스페이스 생성
echo "📦 네임스페이스 '$NAMESPACE' 생성 중..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# === 1. Docker Registry Secret ===
echo "🐳 Docker Registry Secret 생성 중..."
kubectl create secret docker-registry regcred \
  --docker-server=$REGISTRY_URL \
  --docker-username=$DOCKER_REGISTRY_USER \
  --docker-password=$DOCKER_REGISTRY_PASS \
  --namespace=$NAMESPACE \
  --dry-run=client -o yaml | kubectl apply -f -

# === 2. Application Secrets ===
echo "🔑 Application Secrets 생성 중..."
kubectl create secret generic blacklist-secrets \
  --from-literal=REGTECH_USERNAME="$REGTECH_USERNAME" \
  --from-literal=REGTECH_PASSWORD="$REGTECH_PASSWORD" \
  --from-literal=SECUDIUM_USERNAME="$SECUDIUM_USERNAME" \
  --from-literal=SECUDIUM_PASSWORD="$SECUDIUM_PASSWORD" \
  --from-literal=SECRET_KEY="$SECRET_KEY" \
  --from-literal=JWT_SECRET_KEY="$JWT_SECRET_KEY" \
  --from-literal=API_SECRET_KEY="$API_SECRET_KEY" \
  --from-literal=DATABASE_URL="$DATABASE_URL" \
  --from-literal=REDIS_URL="$REDIS_URL" \
  --namespace=$NAMESPACE \
  --dry-run=client -o yaml | kubectl apply -f -

# === 3. ArgoCD Repository Secret (ArgoCD 네임스페이스에 생성) ===
echo "📊 ArgoCD Repository Secret 생성 중..."
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f - >/dev/null 2>&1 || true

kubectl create secret generic chartmuseum-helm-repo \
  --from-literal=type=helm \
  --from-literal=url=$CHARTS_URL \
  --from-literal=name=chartmuseum \
  --from-literal=username=$HELM_REPO_USERNAME \
  --from-literal=password=$HELM_REPO_PASSWORD \
  --namespace=argocd \
  --dry-run=client -o yaml > /tmp/argocd-repo-secret.yaml

# ArgoCD 라벨 추가
cat >> /tmp/argocd-repo-secret.yaml << EOF
metadata:
  labels:
    argocd.argoproj.io/secret-type: repository
EOF

kubectl apply -f /tmp/argocd-repo-secret.yaml

# === 4. Registry Secret for ArgoCD Image Updater ===
echo "🔄 ArgoCD Image Updater Registry Secret 생성 중..."
kubectl create secret docker-registry harbor-registry-updater \
  --docker-server=$REGISTRY_URL \
  --docker-username=$DOCKER_REGISTRY_USER \
  --docker-password=$DOCKER_REGISTRY_PASS \
  --namespace=argocd \
  --dry-run=client -o yaml | kubectl apply -f -

# === 5. ConfigMap for ArgoCD Image Updater ===
echo "⚙️ ArgoCD Image Updater ConfigMap 생성 중..."
cat > /tmp/argocd-image-updater-config.yaml << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-image-updater-config
  namespace: argocd
  labels:
    app.kubernetes.io/name: argocd-image-updater
    app.kubernetes.io/part-of: argocd
data:
  registries.conf: |
    registries:
    - name: registry.jclee.me
      api_url: http://registry.jclee.me
      ping: yes
      insecure: yes
      credentials: pullsecret:argocd/harbor-registry-updater
  log.level: info
  kube.events: true
EOF

kubectl apply -f /tmp/argocd-image-updater-config.yaml

# === 6. 검증 ===
echo ""
echo "🔍 생성된 Secrets 검증 중..."

echo "  📦 네임스페이스 '$NAMESPACE' secrets:"
kubectl get secrets -n $NAMESPACE

echo ""
echo "  📦 네임스페이스 'argocd' secrets:"
kubectl get secrets -n argocd | grep -E "(chartmuseum|harbor-registry)"

echo ""
echo "  📦 네임스페이스 'argocd' configmaps:"
kubectl get configmaps -n argocd | grep image-updater

# === 7. Secret 내용 확인 (디버깅용) ===
if [[ "${DEBUG:-false}" == "true" ]]; then
    echo ""
    echo "🔍 Secret 내용 확인 (DEBUG 모드):"
    
    echo "  Registry Secret:"
    kubectl get secret regcred -n $NAMESPACE -o yaml | grep -A5 -B5 "\.dockerconfigjson"
    
    echo "  Application Secret keys:"
    kubectl get secret blacklist-secrets -n $NAMESPACE -o jsonpath='{.data}' | jq -r 'keys[]'
    
    echo "  ArgoCD Repository Secret:"
    kubectl get secret chartmuseum-helm-repo -n argocd -o yaml | grep -A10 -B5 "stringData"
fi

echo ""
echo "✅ Kubernetes Secrets 생성이 완료되었습니다!"
echo ""
echo "📋 생성된 Secrets:"
echo "   - $NAMESPACE/regcred (Docker Registry)"
echo "   - $NAMESPACE/blacklist-secrets (Application)"
echo "   - argocd/chartmuseum-helm-repo (Helm Repository)"
echo "   - argocd/harbor-registry-updater (Image Updater)"
echo ""
echo "📋 생성된 ConfigMaps:"
echo "   - argocd/argocd-image-updater-config"
echo ""
echo "🚀 이제 ArgoCD 애플리케이션을 배포할 수 있습니다!"
echo "   kubectl apply -f k8s-gitops/argocd/blacklist-app-production.yaml"
echo "   kubectl apply -f k8s-gitops/argocd/blacklist-app-development.yaml"

# Cleanup temporary files
rm -f /tmp/argocd-repo-secret.yaml /tmp/argocd-image-updater-config.yaml