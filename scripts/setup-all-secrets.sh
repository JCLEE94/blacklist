#!/bin/bash
# setup-all-secrets.sh - 모든 Secret 설정을 한번에 수행

set -e

# 환경 변수 확인
if [ -z "$REGISTRY_URL" ] || [ -z "$REGISTRY_USER" ] || [ -z "$REGISTRY_PASS" ]; then
    echo "❌ 필수 환경 변수가 설정되지 않았습니다:"
    echo "   REGISTRY_URL, REGISTRY_USER, REGISTRY_PASS"
    exit 1
fi

echo "🔧 Creating all secrets for blacklist project..."

# 네임스페이스 생성
echo "Creating namespaces..."
for ns in argocd blacklist monitoring; do
    kubectl create namespace $ns --dry-run=client -o yaml | kubectl apply -f -
    echo "✅ Namespace: $ns"
done

# Registry Secret 생성 (모든 네임스페이스)
echo "Creating registry secrets..."
for ns in argocd blacklist monitoring; do
    kubectl create secret docker-registry regcred \
        --docker-server=${REGISTRY_URL} \
        --docker-username=${REGISTRY_USER} \
        --docker-password=${REGISTRY_PASS} \
        --namespace=$ns \
        --dry-run=client -o yaml | kubectl apply -f -
    echo "✅ Registry secret in namespace: $ns"
done

# Application Secret 생성 (환경별)
echo "Creating application secrets..."

# Production secrets
kubectl create secret generic blacklist-secret \
    --from-literal=REGTECH_USERNAME="${REGTECH_USERNAME:-nextrade}" \
    --from-literal=REGTECH_PASSWORD="${REGTECH_PASSWORD:-Sprtmxm1@3}" \
    --from-literal=SECUDIUM_USERNAME="${SECUDIUM_USERNAME:-nextrade}" \
    --from-literal=SECUDIUM_PASSWORD="${SECUDIUM_PASSWORD:-Sprtmxm1@3}" \
    --from-literal=SECRET_KEY="${SECRET_KEY:-$(openssl rand -hex 32)}" \
    --from-literal=JWT_SECRET_KEY="${JWT_SECRET_KEY:-$(openssl rand -hex 32)}" \
    --from-literal=API_SECRET_KEY="${API_SECRET_KEY:-$(openssl rand -hex 32)}" \
    --namespace=blacklist \
    --dry-run=client -o yaml | kubectl apply -f -

echo "✅ Application secrets created"

# ArgoCD Repository Secret (필요한 경우)
if [ ! -z "$GITHUB_TOKEN" ]; then
    kubectl create secret generic charts-repo \
        --from-literal=type=git \
        --from-literal=url=https://github.com/jclee/charts.git \
        --from-literal=username=not-used \
        --from-literal=password=${GITHUB_TOKEN} \
        --namespace=argocd \
        --dry-run=client -o yaml | kubectl apply -f -
    echo "✅ ArgoCD repository secret created"
fi

echo ""
echo "🎉 All secrets have been created successfully!"
echo ""
echo "Next steps:"
echo "1. Apply ArgoCD application: kubectl apply -f argocd/application.yaml"
echo "2. Check ArgoCD UI: kubectl port-forward svc/argocd-server -n argocd 8080:443"
echo "3. Sync application: argocd app sync blacklist"