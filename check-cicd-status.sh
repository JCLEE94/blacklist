#!/bin/bash

# CI/CD Pipeline Status Check Script
# This script verifies the complete CI/CD pipeline status for the Blacklist Management System

echo "=========================================="
echo "CI/CD Pipeline Status Check"
echo "=========================================="
echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Status tracking
OVERALL_STATUS="PASS"

# Function to check status
check_status() {
    local name="$1"
    local condition="$2"
    
    if eval "$condition"; then
        echo -e "${GREEN}✓${NC} $name"
    else
        echo -e "${RED}✗${NC} $name"
        OVERALL_STATUS="FAIL"
    fi
}

# 1. GitHub Actions Runner Status
echo -e "${YELLOW}1. GitHub Actions Runner Status${NC}"
echo "-----------------------------------"
if systemctl is-active --quiet actions-runner 2>/dev/null; then
    echo -e "${GREEN}✓ Self-hosted runner active${NC}"
else
    echo -e "${YELLOW}⚠ Self-hosted runner not detected${NC}"
    echo "  Start command: sudo systemctl start actions-runner"
fi

# Check latest workflow runs
if command -v gh &> /dev/null; then
    echo ""
    echo "Recent Workflow Runs:"
    gh run list --repo JCLEE94/blacklist --limit 3 | head -4
fi
echo ""

# 2. ArgoCD Status
echo -e "${YELLOW}2. ArgoCD Status${NC}"
echo "-----------------------------------"
SYNC_STATUS=$(kubectl get application blacklist -n argocd -o jsonpath='{.status.sync.status}' 2>/dev/null)
HEALTH_STATUS=$(kubectl get application blacklist -n argocd -o jsonpath='{.status.health.status}' 2>/dev/null)

if [ -n "$SYNC_STATUS" ]; then
    echo "Sync Status: $SYNC_STATUS"
    echo "Health Status: $HEALTH_STATUS"
    check_status "ArgoCD sync status" "[ '$SYNC_STATUS' = 'Synced' ]"
    check_status "ArgoCD health status" "[ '$HEALTH_STATUS' = 'Healthy' ]"
else
    echo -e "${RED}✗ ArgoCD application not found${NC}"
    OVERALL_STATUS="FAIL"
fi
echo ""

# 3. ArgoCD Image Updater
echo -e "${YELLOW}3. ArgoCD Image Updater${NC}"
echo "-----------------------------------"
UPDATER_POD=$(kubectl get pods -n argocd -l app.kubernetes.io/name=argocd-image-updater -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$UPDATER_POD" ]; then
    echo -e "${GREEN}✓ Image Updater running: $UPDATER_POD${NC}"
    echo "Recent logs:"
    kubectl logs -n argocd $UPDATER_POD --tail=3 2>/dev/null | grep -E "(Processing results|error|updated)" || echo "  No recent update logs"
else
    echo -e "${RED}✗ Image Updater not running${NC}"
    OVERALL_STATUS="FAIL"
fi
echo ""

# 4. Docker Registry Access
echo -e "${YELLOW}4. Docker Registry Access${NC}"
echo "-----------------------------------"
REGISTRY_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://registry.jclee.me/v2/ 2>/dev/null)
check_status "Registry accessible (HTTP $REGISTRY_CHECK)" "[ '$REGISTRY_CHECK' = '200' -o '$REGISTRY_CHECK' = '401' ]"

# Check registry authentication
if kubectl get secret regcred -n blacklist &>/dev/null; then
    check_status "Docker registry secret exists" "true"
else
    check_status "Docker registry secret exists" "false"
    echo -e "  ${YELLOW}Create with: kubectl create secret docker-registry regcred --docker-server=registry.jclee.me --docker-username=<user> --docker-password=<pass> -n blacklist${NC}"
fi
echo ""

# 5. Current Deployment Info
echo -e "${YELLOW}5. Current Deployment Info${NC}"
echo "-----------------------------------"
# Try multiple endpoints
HEALTH_ENDPOINTS=(
    "http://localhost:8541/health"
    "http://localhost:32542/health"
    "http://192.168.50.110:32542/health"
)

HEALTH_FOUND=false
for endpoint in "${HEALTH_ENDPOINTS[@]}"; do
    HEALTH_RESPONSE=$(curl -s "$endpoint" 2>/dev/null)
    if [ -n "$HEALTH_RESPONSE" ]; then
        CURRENT_VERSION=$(echo "$HEALTH_RESPONSE" | jq -r '.details.version' 2>/dev/null)
        ACTIVE_IPS=$(echo "$HEALTH_RESPONSE" | jq -r '.details.active_ips' 2>/dev/null)
        if [ "$CURRENT_VERSION" != "null" ]; then
            echo "Version: $CURRENT_VERSION"
            echo "Active IPs: $ACTIVE_IPS"
            echo "Health Endpoint: $endpoint"
            HEALTH_FOUND=true
            break
        fi
    fi
done

if [ "$HEALTH_FOUND" = false ]; then
    echo -e "${RED}✗ Unable to reach health endpoint${NC}"
fi

CURRENT_IMAGE=$(kubectl get deployment blacklist -n blacklist -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null)
if [ -n "$CURRENT_IMAGE" ]; then
    echo "Current Image: $CURRENT_IMAGE"
fi
echo ""

# 6. CI/CD Configuration Files
echo -e "${YELLOW}6. CI/CD Configuration Files${NC}"
echo "-----------------------------------"
check_status "GitHub Actions workflow exists" "[ -f '.github/workflows/auto-deploy.yaml' -o -f '.github/workflows/simple-deploy.yaml' ]"
check_status "Kubernetes manifests exist" "[ -d 'k8s' ]"
check_status "Dockerfile exists" "[ -f 'deployment/Dockerfile' ]"
echo ""

# 7. Kubernetes Resources
echo -e "${YELLOW}7. Kubernetes Resources${NC}"
echo "-----------------------------------"
echo "Pods in blacklist namespace:"
kubectl get pods -n blacklist --no-headers 2>/dev/null | while read line; do
    if [ -n "$line" ]; then
        POD_NAME=$(echo "$line" | awk '{print $1}')
        READY=$(echo "$line" | awk '{print $2}')
        STATUS=$(echo "$line" | awk '{print $3}')
        if [ "$STATUS" = "Running" ]; then
            echo -e "  ${GREEN}✓${NC} $POD_NAME ($READY)"
        else
            echo -e "  ${RED}✗${NC} $POD_NAME ($STATUS)"
        fi
    fi
done
echo ""

# 8. Current Issues & Recommendations
echo -e "${YELLOW}8. Current Issues & Recommendations${NC}"
echo "-----------------------------------"

# Check if workflows are failing
LATEST_CONCLUSION=$(gh run list --repo JCLEE94/blacklist --limit 1 --json conclusion -q '.[0].conclusion' 2>/dev/null)
if [ "$LATEST_CONCLUSION" = "failure" ]; then
    echo -e "${RED}Issue: GitHub Actions workflows are failing${NC}"
    echo "  Cause: Missing Docker registry authentication"
    echo ""
    echo -e "${BLUE}Fix Steps:${NC}"
    echo "  1. Add GitHub Secrets:"
    echo "     - Go to: https://github.com/JCLEE94/blacklist/settings/secrets/actions"
    echo "     - Add: DOCKER_REGISTRY_USER and DOCKER_REGISTRY_PASS"
    echo ""
    echo "  2. Update workflow to include docker login:"
    echo "     - Add login step before docker push"
    echo ""
fi

# Check ArgoCD connectivity
if [ -z "$SYNC_STATUS" ]; then
    echo -e "${YELLOW}Issue: ArgoCD application not configured${NC}"
    echo "  Run: ./scripts/k8s-management.sh init"
    echo ""
fi

# Manual deployment workaround
echo -e "${BLUE}Manual Deployment (if CI/CD fails):${NC}"
echo "  docker build -f deployment/Dockerfile -t registry.jclee.me/jclee94/blacklist:latest ."
echo "  docker push registry.jclee.me/jclee94/blacklist:latest"
echo "  kubectl rollout restart deployment blacklist -n blacklist"
echo ""

# 9. Summary
echo "=========================================="
echo -e "${BLUE}Summary${NC}"
echo "=========================================="

if [ "$OVERALL_STATUS" = "PASS" ]; then
    echo -e "${GREEN}✓ Overall Status: OPERATIONAL${NC}"
    echo ""
    echo "The application is running successfully!"
    echo "However, CI/CD pipeline needs registry authentication fix."
else
    echo -e "${RED}✗ Overall Status: ISSUES DETECTED${NC}"
    echo ""
    echo "Please review the issues above and follow the recommendations."
fi

echo ""
echo "Quick Commands:"
echo "  Check logs: kubectl logs -f deployment/blacklist -n blacklist"
echo "  Check workflows: gh run list --repo JCLEE94/blacklist"
echo "  Force sync: argocd app sync blacklist --grpc-web"
echo "=========================================="

# Exit with appropriate code
if [ "$OVERALL_STATUS" = "PASS" ]; then
    exit 0
else
    exit 1
fi