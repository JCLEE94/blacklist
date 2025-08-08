#!/bin/bash

# ArgoCD Helm Repository Configuration Script
# Configure ArgoCD to use charts.jclee.me as Helm repository

set -e

echo "🚀 Configuring ArgoCD to use charts.jclee.me Helm repository"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if kubectl is available
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}❌ kubectl is not installed${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ kubectl found${NC}"
}

# Function to check ArgoCD namespace
check_argocd_namespace() {
    if kubectl get namespace argocd &> /dev/null; then
        echo -e "${GREEN}✅ ArgoCD namespace exists${NC}"
    else
        echo -e "${YELLOW}⚠️  ArgoCD namespace not found. Creating...${NC}"
        kubectl create namespace argocd
    fi
}

# Function to add Helm repository to ArgoCD
add_helm_repo_to_argocd() {
    echo "📦 Adding charts.jclee.me to ArgoCD repositories..."
    
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: helm-charts-jclee
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: helm
  url: https://charts.jclee.me
  name: jclee-charts
EOF
    
    echo -e "${GREEN}✅ Helm repository added to ArgoCD${NC}"
}

# Function to apply ArgoCD applications
apply_argocd_applications() {
    echo "📋 Applying ArgoCD application configurations..."
    
    # Apply main blacklist app
    if [[ -f "k8s/blacklist-app.yaml" ]]; then
        kubectl apply -f k8s/blacklist-app.yaml
        echo -e "${GREEN}✅ Applied main blacklist application${NC}"
    fi
    
    # Apply auto-deploy configuration
    if [[ -f "k8s/argocd/argocd-auto-deploy.yaml" ]]; then
        kubectl apply -f k8s/argocd/argocd-auto-deploy.yaml
        echo -e "${GREEN}✅ Applied auto-deploy configuration${NC}"
    fi
    
    # Apply MSA configuration if exists
    if [[ -f "k8s/msa/argocd-application.yaml" ]]; then
        kubectl apply -f k8s/msa/argocd-application.yaml
        echo -e "${GREEN}✅ Applied MSA configuration${NC}"
    fi
}

# Function to verify ArgoCD applications
verify_applications() {
    echo "🔍 Verifying ArgoCD applications..."
    
    # Check if argocd CLI is available
    if command -v argocd &> /dev/null; then
        echo "📊 ArgoCD Applications Status:"
        argocd app list --grpc-web 2>/dev/null || kubectl get applications -n argocd
    else
        echo "📊 ArgoCD Applications (via kubectl):"
        kubectl get applications -n argocd
    fi
}

# Function to sync applications
sync_applications() {
    echo "🔄 Syncing ArgoCD applications..."
    
    if command -v argocd &> /dev/null; then
        # Try to sync using argocd CLI
        argocd app sync blacklist --grpc-web 2>/dev/null || true
        echo -e "${GREEN}✅ Sync initiated${NC}"
    else
        echo -e "${YELLOW}⚠️  ArgoCD CLI not found. Manual sync required via UI${NC}"
        echo "   Access ArgoCD at: https://argo.jclee.me"
    fi
}

# Main execution
main() {
    echo "Starting ArgoCD Helm configuration..."
    echo ""
    
    check_kubectl
    check_argocd_namespace
    add_helm_repo_to_argocd
    apply_argocd_applications
    verify_applications
    sync_applications
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}✅ ArgoCD configuration complete!${NC}"
    echo ""
    echo "📝 Summary:"
    echo "  • Helm repository: https://charts.jclee.me"
    echo "  • ArgoCD UI: https://argo.jclee.me"
    echo "  • Applications configured to use Helm charts"
    echo ""
    echo "🎯 Next steps:"
    echo "  1. Check ArgoCD UI for application status"
    echo "  2. Ensure Helm charts are published to charts.jclee.me"
    echo "  3. Monitor automatic sync status"
}

# Run main function
main "$@"