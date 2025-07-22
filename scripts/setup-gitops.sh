#!/bin/bash

# GitOps Setup Script for Blacklist Application
# This script sets up ArgoCD and configures GitOps for the blacklist application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ARGOCD_NAMESPACE="argocd"
APP_NAMESPACE="blacklist"
REPO_URL="git@github.com:JCLEE94/blacklist.git"
REGISTRY="registry.jclee.me"

echo -e "${BLUE}=== GitOps Setup for Blacklist Application ===${NC}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

if ! command_exists kubectl; then
    echo -e "${RED}Error: kubectl is not installed${NC}"
    exit 1
fi

if ! command_exists argocd; then
    echo -e "${YELLOW}Warning: ArgoCD CLI not found. Installing...${NC}"
    curl -sSL -o /tmp/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
    chmod +x /tmp/argocd
    sudo mv /tmp/argocd /usr/local/bin/argocd
    echo -e "${GREEN}ArgoCD CLI installed${NC}"
fi

# 1. Install ArgoCD if not exists
echo -e "\n${YELLOW}1. Checking ArgoCD installation...${NC}"
if ! kubectl get namespace $ARGOCD_NAMESPACE >/dev/null 2>&1; then
    echo "Installing ArgoCD..."
    kubectl create namespace $ARGOCD_NAMESPACE
    kubectl apply -n $ARGOCD_NAMESPACE -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
    
    echo "Waiting for ArgoCD to be ready..."
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=argocd-server -n $ARGOCD_NAMESPACE --timeout=300s
else
    echo -e "${GREEN}ArgoCD is already installed${NC}"
fi

# 2. Get ArgoCD admin password
echo -e "\n${YELLOW}2. Getting ArgoCD admin credentials...${NC}"
ARGOCD_PASSWORD=$(kubectl -n $ARGOCD_NAMESPACE get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
echo -e "ArgoCD Admin Password: ${GREEN}$ARGOCD_PASSWORD${NC}"

# 3. Port forward to ArgoCD server
echo -e "\n${YELLOW}3. Setting up ArgoCD access...${NC}"
echo "Port forwarding ArgoCD server..."
kubectl port-forward svc/argocd-server -n $ARGOCD_NAMESPACE 8080:443 >/dev/null 2>&1 &
PF_PID=$!
sleep 5

# 4. Login to ArgoCD
echo -e "\n${YELLOW}4. Logging in to ArgoCD...${NC}"
argocd login localhost:8080 --username admin --password "$ARGOCD_PASSWORD" --insecure

# 5. Create application namespace if not exists
echo -e "\n${YELLOW}5. Creating application namespace...${NC}"
kubectl create namespace $APP_NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# 6. Create registry secret (if needed)
echo -e "\n${YELLOW}6. Creating registry secret...${NC}"
# registry.jclee.me doesn't require authentication, but create placeholder
kubectl create secret docker-registry regcred \
    --docker-server=$REGISTRY \
    --docker-username=dummy \
    --docker-password=dummy \
    --docker-email=dummy@example.com \
    -n $APP_NAMESPACE \
    --dry-run=client -o yaml | kubectl apply -f -

# 7. Add Git repository to ArgoCD
echo -e "\n${YELLOW}7. Adding Git repository to ArgoCD...${NC}"
if argocd repo list | grep -q "$REPO_URL"; then
    echo -e "${GREEN}Repository already added${NC}"
else
    # Check if SSH key exists
    if [ ! -f ~/.ssh/id_rsa ]; then
        echo -e "${RED}Error: SSH key not found. Please setup GitHub SSH key first${NC}"
        kill $PF_PID 2>/dev/null
        exit 1
    fi
    
    argocd repo add $REPO_URL --ssh-private-key-path ~/.ssh/id_rsa
fi

# 8. Create ArgoCD application
echo -e "\n${YELLOW}8. Creating ArgoCD application...${NC}"
kubectl apply -f k8s-gitops/argocd/blacklist-app.yaml

# 9. Sync application
echo -e "\n${YELLOW}9. Syncing application...${NC}"
argocd app sync blacklist

# 10. Check application status
echo -e "\n${YELLOW}10. Checking application status...${NC}"
argocd app get blacklist

# Clean up port forward
kill $PF_PID 2>/dev/null

echo -e "\n${GREEN}=== GitOps Setup Complete ===${NC}"
echo -e "${BLUE}You can access ArgoCD UI by running:${NC}"
echo -e "  kubectl port-forward svc/argocd-server -n argocd 8080:443"
echo -e "  Then open: https://localhost:8080"
echo -e "  Username: admin"
echo -e "  Password: $ARGOCD_PASSWORD"
echo -e "\n${BLUE}To check application status:${NC}"
echo -e "  argocd app get blacklist"
echo -e "  kubectl get pods -n blacklist"