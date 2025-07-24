#!/bin/bash

# GitOps Setup Validation Script
# Validates all components required for GitOps deployment

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REGISTRY="${REGISTRY_URL:-registry.jclee.me}"
CHARTS_URL="${CHARTS_URL:-https://charts.jclee.me}"
ARGOCD_SERVER="${ARGOCD_SERVER:-argo.jclee.me}"
NAMESPACE="${APP_NAMESPACE:-blacklist}"
APP_NAME="${APP_NAME:-blacklist}"

echo "==================================="
echo "GitOps Setup Validation"
echo "==================================="
echo ""

# Function to check command existence
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 is installed"
        return 0
    else
        echo -e "${RED}✗${NC} $1 is not installed"
        return 1
    fi
}

# Function to check connectivity
check_connectivity() {
    local url=$1
    local name=$2
    
    if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$url" | grep -q "200\|401\|403"; then
        echo -e "${GREEN}✓${NC} $name is accessible at $url"
        return 0
    else
        echo -e "${RED}✗${NC} $name is not accessible at $url"
        return 1
    fi
}

# Function to check Kubernetes resources
check_k8s_resource() {
    local resource=$1
    local name=$2
    local namespace=$3
    
    if kubectl get $resource $name -n $namespace &> /dev/null; then
        echo -e "${GREEN}✓${NC} $resource/$name exists in namespace $namespace"
        return 0
    else
        echo -e "${RED}✗${NC} $resource/$name not found in namespace $namespace"
        return 1
    fi
}

# 1. Check Required Tools
echo "1. Checking required tools..."
echo "----------------------------"
TOOLS_OK=true
check_command "docker" || TOOLS_OK=false
check_command "kubectl" || TOOLS_OK=false
check_command "helm" || TOOLS_OK=false
check_command "argocd" || TOOLS_OK=false
check_command "curl" || TOOLS_OK=false
check_command "jq" || TOOLS_OK=false

if [ "$TOOLS_OK" = false ]; then
    echo -e "\n${YELLOW}⚠ Some tools are missing. Run setup scripts to install them.${NC}"
fi
echo ""

# 2. Check Docker Registry
echo "2. Checking Docker Registry..."
echo "-----------------------------"
check_connectivity "https://$REGISTRY/v2/" "Docker Registry"

# Test registry authentication
if [ -n "$DOCKER_REGISTRY_USER" ] && [ -n "$DOCKER_REGISTRY_PASS" ]; then
    if echo "$DOCKER_REGISTRY_PASS" | docker login $REGISTRY -u $DOCKER_REGISTRY_USER --password-stdin &> /dev/null; then
        echo -e "${GREEN}✓${NC} Registry authentication successful"
    else
        echo -e "${RED}✗${NC} Registry authentication failed"
    fi
else
    echo -e "${YELLOW}⚠${NC} Registry credentials not set in environment"
fi
echo ""

# 3. Check Helm Repository
echo "3. Checking Helm Repository..."
echo "-----------------------------"
check_connectivity "$CHARTS_URL" "ChartMuseum"

# Check if Helm repo is added
if helm repo list | grep -q "charts"; then
    echo -e "${GREEN}✓${NC} Helm repository 'charts' is configured"
    helm repo update charts &> /dev/null && echo -e "${GREEN}✓${NC} Helm repository updated"
else
    echo -e "${YELLOW}⚠${NC} Helm repository not added. Add with:"
    echo "    helm repo add charts $CHARTS_URL"
fi
echo ""

# 4. Check Kubernetes Cluster
echo "4. Checking Kubernetes Cluster..."
echo "--------------------------------"
if kubectl cluster-info &> /dev/null; then
    echo -e "${GREEN}✓${NC} Kubernetes cluster is accessible"
    CURRENT_CONTEXT=$(kubectl config current-context)
    echo -e "${GREEN}✓${NC} Current context: $CURRENT_CONTEXT"
else
    echo -e "${RED}✗${NC} Cannot connect to Kubernetes cluster"
fi

# Check namespace
check_k8s_resource "namespace" "$NAMESPACE" ""
echo ""

# 5. Check ArgoCD
echo "5. Checking ArgoCD..."
echo "--------------------"
check_connectivity "https://$ARGOCD_SERVER" "ArgoCD Server"

# Check ArgoCD login
if [ -n "$ARGOCD_AUTH_TOKEN" ]; then
    if argocd account get-user-info --grpc-web --auth-token $ARGOCD_AUTH_TOKEN --server $ARGOCD_SERVER &> /dev/null; then
        echo -e "${GREEN}✓${NC} ArgoCD authentication successful"
    else
        echo -e "${RED}✗${NC} ArgoCD authentication failed"
    fi
else
    echo -e "${YELLOW}⚠${NC} ARGOCD_AUTH_TOKEN not set"
fi

# Check ArgoCD application
if argocd app get $APP_NAME --grpc-web &> /dev/null; then
    echo -e "${GREEN}✓${NC} ArgoCD application '$APP_NAME' exists"
    
    # Get sync status
    SYNC_STATUS=$(argocd app get $APP_NAME --grpc-web -o json | jq -r '.status.sync.status')
    HEALTH_STATUS=$(argocd app get $APP_NAME --grpc-web -o json | jq -r '.status.health.status')
    
    echo "   Sync Status: $SYNC_STATUS"
    echo "   Health Status: $HEALTH_STATUS"
else
    echo -e "${YELLOW}⚠${NC} ArgoCD application '$APP_NAME' not found"
fi
echo ""

# 6. Check Kubernetes Resources
echo "6. Checking Kubernetes Resources..."
echo "----------------------------------"
check_k8s_resource "deployment" "$APP_NAME" "$NAMESPACE"
check_k8s_resource "service" "$APP_NAME" "$NAMESPACE"
check_k8s_resource "secret" "regcred" "$NAMESPACE"

# Check pods
POD_COUNT=$(kubectl get pods -n $NAMESPACE -l app=$APP_NAME --no-headers 2>/dev/null | wc -l)
if [ "$POD_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} Found $POD_COUNT pod(s) for $APP_NAME"
    
    # Check pod status
    NOT_READY=$(kubectl get pods -n $NAMESPACE -l app=$APP_NAME --no-headers 2>/dev/null | grep -v "Running\|Completed" | wc -l)
    if [ "$NOT_READY" -eq 0 ]; then
        echo -e "${GREEN}✓${NC} All pods are running"
    else
        echo -e "${YELLOW}⚠${NC} $NOT_READY pod(s) are not ready"
    fi
else
    echo -e "${YELLOW}⚠${NC} No pods found for $APP_NAME"
fi
echo ""

# 7. Check Application Health
echo "7. Checking Application Health..."
echo "--------------------------------"
# Try NodePort first
if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "http://192.168.50.110:32452/health" | grep -q "200"; then
    echo -e "${GREEN}✓${NC} Application health check passed (NodePort)"
    HEALTH_DATA=$(curl -s "http://192.168.50.110:32452/health")
    echo "   Status: $(echo $HEALTH_DATA | jq -r '.status' 2>/dev/null || echo 'unknown')"
elif curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "https://blacklist.jclee.me/health" | grep -q "200"; then
    echo -e "${GREEN}✓${NC} Application health check passed (Ingress)"
else
    echo -e "${YELLOW}⚠${NC} Application health check failed or not accessible"
fi
echo ""

# 8. Check GitHub Configuration
echo "8. Checking GitHub Configuration..."
echo "----------------------------------"
if [ -f ".github/workflows/gitops-template.yml" ]; then
    echo -e "${GREEN}✓${NC} GitOps workflow template exists"
else
    echo -e "${RED}✗${NC} GitOps workflow template not found"
fi

# Check for required secrets in workflow
REQUIRED_SECRETS=("REGISTRY_USERNAME" "REGISTRY_PASSWORD" "ARGOCD_AUTH_TOKEN")
echo "Required GitHub Secrets:"
for secret in "${REQUIRED_SECRETS[@]}"; do
    echo "   - $secret"
done
echo -e "${YELLOW}⚠${NC} Verify these are set in GitHub Settings → Secrets"
echo ""

# 9. Summary
echo "==================================="
echo "Summary"
echo "==================================="
echo ""

# Overall status
ALL_GOOD=true
[ "$TOOLS_OK" = false ] && ALL_GOOD=false

if [ "$ALL_GOOD" = true ]; then
    echo -e "${GREEN}✅ GitOps setup is valid and ready for deployment!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Push code to trigger pipeline: git push origin main"
    echo "2. Monitor pipeline: GitHub Actions tab"
    echo "3. Check deployment: argocd app get $APP_NAME --grpc-web"
else
    echo -e "${YELLOW}⚠ Some issues detected. Please review and fix them.${NC}"
    echo ""
    echo "For detailed setup instructions, see:"
    echo "- docs/GITOPS_DEPLOYMENT_GUIDE.md"
    echo "- scripts/setup/argocd-complete-setup.sh"
fi

echo ""
echo "Validation complete!"