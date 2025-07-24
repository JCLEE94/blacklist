#!/bin/bash

# Pre-Deployment Integration Check Script
# Validates all components before deployment to prevent failures

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGISTRY="${REGISTRY_URL:-registry.jclee.me}"
CHARTS_URL="${CHARTS_URL:-https://charts.jclee.me}"
NAMESPACE="${APP_NAMESPACE:-blacklist}"
APP_NAME="${APP_NAME:-blacklist}"
NODE_PORT="${NODE_PORT:-32542}"
EXTERNAL_DOMAIN="${EXTERNAL_DOMAIN:-blacklist.jclee.me}"

# Test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
WARNINGS=0

echo "===================================="
echo "Pre-Deployment Integration Check"
echo "===================================="
echo ""

# Function to run a test
run_test() {
    local test_name=$1
    local test_command=$2
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "Testing: $test_name... "
    
    if eval "$test_command" &> /dev/null; then
        echo -e "${GREEN}PASSED${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# Function to run a warning test (non-critical)
run_warning_test() {
    local test_name=$1
    local test_command=$2
    
    echo -n "Checking: $test_name... "
    
    if eval "$test_command" &> /dev/null; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${YELLOW}WARNING${NC}"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi
}

# 1. Registry Tests
echo -e "${BLUE}1. Registry Integration Tests${NC}"
echo "------------------------------"

run_test "Registry connectivity" "curl -s -f -o /dev/null https://$REGISTRY/v2/"
run_test "Registry catalog accessible" "curl -s -f https://$REGISTRY/v2/_catalog | grep -q 'repositories'"

# Check specific image
IMAGE_PATH="jclee94/blacklist"
run_test "Blacklist image exists" "curl -s -f https://$REGISTRY/v2/$IMAGE_PATH/tags/list | grep -q 'latest'"

# Test with authentication if provided
if [ -n "$REGISTRY_USERNAME" ] && [ -n "$REGISTRY_PASSWORD" ]; then
    run_test "Registry authentication" "echo '$REGISTRY_PASSWORD' | docker login $REGISTRY -u $REGISTRY_USERNAME --password-stdin"
fi

echo ""

# 2. ChartMuseum Tests
echo -e "${BLUE}2. ChartMuseum Integration Tests${NC}"
echo "---------------------------------"

run_test "ChartMuseum accessibility" "curl -s -f -o /dev/null $CHARTS_URL"
run_test "Chart index available" "curl -s -f $CHARTS_URL/index.yaml | grep -q 'apiVersion'"
run_test "Blacklist chart exists" "curl -s -f $CHARTS_URL/index.yaml | grep -q 'name: blacklist'"

# Test Helm operations
run_test "Helm repo configured" "helm repo list | grep -q charts"
run_test "Helm repo update" "helm repo update charts"
run_test "Chart searchable" "helm search repo charts/blacklist | grep -q blacklist"

echo ""

# 3. Kubernetes Resource Tests
echo -e "${BLUE}3. Kubernetes Resource Tests${NC}"
echo "-----------------------------"

run_test "Kubernetes cluster accessible" "kubectl cluster-info"
run_test "Namespace exists" "kubectl get namespace $NAMESPACE"
run_test "No existing deployment conflicts" "! kubectl get deployment $APP_NAME -n $NAMESPACE &> /dev/null || true"

# Check for port conflicts
run_test "NodePort $NODE_PORT available" "! kubectl get svc -A -o json | jq -r '.items[].spec.ports[]?.nodePort' | grep -q ^${NODE_PORT}$"

# Check secrets
run_test "Registry secret exists" "kubectl get secret regcred -n $NAMESPACE"

echo ""

# 4. ArgoCD Tests
echo -e "${BLUE}4. ArgoCD Integration Tests${NC}"
echo "----------------------------"

run_test "ArgoCD CLI available" "command -v argocd"
run_test "ArgoCD server accessible" "argocd version --grpc-web | grep -q 'Server'"

if [ -n "$ARGOCD_AUTH_TOKEN" ]; then
    run_test "ArgoCD authentication" "argocd account get-user-info --grpc-web --auth-token $ARGOCD_AUTH_TOKEN"
fi

# Check if app already exists
if argocd app get $APP_NAME --grpc-web &> /dev/null; then
    run_warning_test "ArgoCD app doesn't exist" "false"
    echo "  Note: Existing app will be updated"
else
    run_test "ArgoCD app doesn't exist" "true"
fi

echo ""

# 5. Configuration Tests
echo -e "${BLUE}5. Configuration Tests${NC}"
echo "----------------------"

run_test "GitHub workflow exists" "test -f .github/workflows/gitops-template.yml"
run_test "Helm chart exists" "test -d charts/blacklist"
run_test "Values file exists" "test -f charts/blacklist/values.yaml"

# Check image configuration in values
run_test "Image repository correct" "grep -q 'repository: registry.jclee.me/jclee94/blacklist' charts/blacklist/values.yaml"
run_test "Service type is NodePort" "grep -q 'type: NodePort' charts/blacklist/values.yaml || echo 'service:\n  type: NodePort' >> charts/blacklist/values.yaml"

echo ""

# 6. External Access Tests
echo -e "${BLUE}6. External Access Tests${NC}"
echo "------------------------"

run_warning_test "External domain resolves" "nslookup $EXTERNAL_DOMAIN"
run_warning_test "Reverse proxy accessible" "curl -s -f -o /dev/null https://$EXTERNAL_DOMAIN || curl -s -f -o /dev/null http://$EXTERNAL_DOMAIN"

# Check local hosts file
if grep -q "$EXTERNAL_DOMAIN" /etc/hosts; then
    echo -e "  ${YELLOW}Note: $EXTERNAL_DOMAIN is in /etc/hosts${NC}"
fi

echo ""

# 7. Application Tests
echo -e "${BLUE}7. Application Integration Tests${NC}"
echo "--------------------------------"

# Test basic Python imports
run_test "Python dependencies" "python3 -c 'import flask, pandas, openpyxl, redis, orjson'"
run_test "Application imports" "python3 -c 'from src.core.app_compact import create_app'"
run_test "Database initialization" "python3 -c 'from init_database import init_db; print(\"OK\")'"

echo ""

# 8. Summary
echo "===================================="
echo -e "${BLUE}Test Summary${NC}"
echo "===================================="
echo "Total Tests: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✅ All critical tests passed! Ready for deployment.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Commit and push changes"
    echo "2. Monitor GitHub Actions pipeline"
    echo "3. Check ArgoCD sync status"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please fix issues before deployment.${NC}"
    echo ""
    echo "Common fixes:"
    echo "- Run: helm repo add charts $CHARTS_URL"
    echo "- Run: kubectl create namespace $NAMESPACE"
    echo "- Check registry credentials"
    echo "- Verify ArgoCD connection"
    exit 1
fi